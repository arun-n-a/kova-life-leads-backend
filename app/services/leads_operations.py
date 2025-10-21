import queue
import base64
from typing import Dict, List, Tuple, Optional
from math import ceil
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import boto3
from flask import g, render_template
from sqlalchemy import (func,  and_, not_, desc)
from werkzeug.datastructures import FileStorage
from sqlalchemy.orm import Query

from app.models import (
    MailingLead as ML, 
    MailingAssignee as MA, 
    MailingResponse as MR, 
    MailingLeadMemberStatusLog as MLMSL,
    Agent, User)
from app.services.utils import (
    convert_datetime_to_timezone_date, 
    date_time_obj_to_str, 
    date_object_to_string,
    convert_utc_to_timezone
)
from app.services.file_operations import thread_download_mortgage_file
from app.services.custom_errors import *
from app.services.crud import CRUD
from app.services.sendgrid_email import SendgridEmailSending
from app.services.aws_services import AmazonServices
from app import app, db, logging
from config import Config_is
from constants import (
    EXCLUDED_STATUS_FILTER_FROM_SALE,
    EXCLUDED_STATUS_OCCUR_TWO_TIME,
    LEAD_STATUS 
    )


def view_lead_filters(db_query, query_filters: Dict):
    if g.user['role_id'] == 1 and query_filters.get('agent_id'):
        db_query = db_query.filter(MA.agent_id == query_filters.pop('agent_id'))  
    else:
        db_query = db_query.filter(MA.agent_id.in_(g.user['mailing_agent_ids']))
    if query_filters.get('lead_status'):
        db_query = db_query.filter(MA.lead_status == query_filters.pop('lead_status'))
    else:
        db_query = db_query.filter(MA.lead_status != 12)
    if query_filters.get('campaign'):
        db_query = db_query.filter(MA.campaign_name.ilike(f"%{query_filters.pop('campaign', '')}%"))
    if query_filters.get('name'):
        if query_filters.get('name').strip().isdigit():
            db_query = db_query.filter(MA.mortgage_id == query_filters.pop('name').strip())
        else:
            db_query = db_query.filter(ML.full_name.ilike(f"%{query_filters.pop('name').strip()}%"))
    if query_filters.get('purchased_user_id'):
        db_query = db_query.filter(MA.purchased_user_id == query_filters.pop('purchased_user_id'))
    else:
        db_query = db_query.filter(MA.purchased_user_id == None)
    for k, v in query_filters.items():
        db_query = db_query.filter(getattr(ML, k) == v)
    return db_query


def get_agents_mailing_leads(query_filters: Dict, page: int, per_page: int) -> Tuple:
    print(query_filters, page, per_page)
    result = []
    if not query_filters.pop('is_mailed', None):
        db_query = ML.query.join(
            MR, MR.mortgage_id == ML.mortgage_id).join(MA, MA.mortgage_id==ML.mortgage_id).with_entities(
                ML.mortgage_id, ML.source_id, ML.full_name, ML.state, ML.city, MA.agent_id, MA.notes, 
                MA.lead_status, MA.suppression_rejection_msg, MA.campaign_name, MR.call_in_date_time, MR.completed, 
                MR.ivr_response, MR.ivr_logs, ML.zip, ML.address, ML.city, ML.first_name, ML.last_name, 
                ML.lender_name, ML.loan_amount, ML.loan_date, MA.id.label('assignee_id'))
        if query_filters.get('lead_status', '') != 12:
            db_query =  db_query.order_by(MR.call_in_date_time.desc())
        else:
            db_query =  db_query.order_by(MA.modified_at.desc())
        if 'completed' in query_filters:
            # To view completed leads
            db_query = db_query.filter(MR.completed == query_filters.pop('completed'))
    else:
        db_query = (
            ML.query
            .outerjoin(MR, MR.mortgage_id == ML.mortgage_id)
            .join(MA, MA.mortgage_id==ML.mortgage_id)
            .with_entities(
                ML.mortgage_id, ML.source_id, ML.full_name, ML.state, MA.id.label('assignee_id'), 
                MA.agent_id, MA.notes, MA.lead_status, MA.suppression_rejection_msg, ML.city, 
                MA.campaign_name, ML.address, ML.zip, ML.first_name, ML.last_name, ML.lender_name,
                ML.loan_amount, ML.loan_date
                )
            .filter(MR.mortgage_id == None)
            .order_by(MA.modified_at.desc())
            )
    db_query = view_lead_filters(db_query, query_filters)
    try:
        leads = db_query.paginate(page=page, per_page=per_page, error_out=False)    
        for data in leads.items:
            data = data._asdict()
            data['loan_date'] = date_object_to_string(data['loan_date'])
            data['call_in_date_time'] = date_time_obj_to_str(data.get('call_in_date_time'))
            result.append(data)
    except Exception as e:
        db.session.rollback()
        print(f"get_agents_mailing_value_leads --> {e}")
        raise InternalError('Server is overloaded please try again later')
    if result:
        return result, {'total': leads.total, 'current_page': leads.page, 'per_page': leads.per_page,
                        'length': len(result)}
    raise NoContent()


def download_all_mailing_leads_thread(db_query, page, per_page, thread_response):
    try:
        with app.app_context():
            response = []
            with db.session.begin():
                try:
                    leads = db_query.order_by(ML.mortgage_id.desc()).paginate(
                        page=page, per_page=per_page, error_out=False)
                    for data in leads.items:
                        data = data._asdict()
                        data['loan_date'] = date_object_to_string(data['loan_date'])
                        data['call_in_date_time'] = date_time_obj_to_str(data.get('call_in_date_time', None))
                        response.append(data)
                    thread_response.put(response)
                except Exception as e:
                    db.session.rollback()
                    print(f'download_all_mailing_of_agent_by_admin_thread Exception {page} {e}')
                    logging.error(f'download_all_mailing_of_agent_by_admin_thread Exception {page} {e}')
                    thread_response.put(str(e))
    except Exception as e:
        print(f'download_all_mailing_of_agent_by_admin_thread main exception as {e}')
        logging.exception(f'download_all_mailing_of_agent_by_admin_thread main exception as {e}')
    return True


def all_download_agent_mailing_leads(query_filters: Dict, total: int) -> List:
    result, page, per_page, thread_response = [], 0, 15000, queue.Queue()
    if not query_filters.pop('is_mailed', None):
        db_query = ML.query.join(MR, MR.mortgage_id == ML.mortgage_id).join(
            MA, MA.mortgage_id==ML.mortgage_id).with_entities(
                ML.mortgage_id, ML.source_id, ML.full_name, ML.state, ML.city, MA.id.label('assignee_id'), MA.agent_id, 
                MA.lead_status, MA.campaign_name, MR.call_in_date_time, MR.completed, 
                MR.ivr_response, ML.city, ML.address, ML.zip, ML.first_name, ML.last_name, ML.lender_name,
                ML.loan_date, ML.loan_amount).order_by(MR.call_in_date_time.desc())
        if 'completed' in query_filters:
            # To view completed leads
            db_query = db_query.filter(MR.completed== query_filters.pop('completed'))
    else:
        db_query = ML.query.outerjoin(MR, MR.mortgage_id == ML.mortgage_id).join(
            MA, MA.mortgage_id==ML.mortgage_id).with_entities(
            ML.mortgage_id, ML.source_id, ML.full_name, ML.state, MA.id.label('assignee_id'), MA.agent_id, MA.lead_status, 
            MA.campaign_name, ML.zip, ML.city, ML.address, ML.first_name, 
            ML.last_name, ML.loan_amount, ML.loan_date).filter(MR.mortgage_id == None).order_by(MA.modified_at.desc())
    db_query = view_lead_filters(db_query, query_filters)
    with ThreadPoolExecutor(max_workers=5) as executor:
        for page in range(1, ceil(total / per_page) + 1):
            executor.submit(download_all_mailing_leads_thread, db_query, page, per_page, thread_response)
    for _ in range(1, ceil(total / per_page) + 1):
        val = thread_response.get(timeout=120)
        print(f'Length of cal {len(val)}')
        if isinstance(val, list):
            result.extend(val)
        else:
            raise InternalError()
    if result:
        return result
    raise NoContent()


def mailer_single_lead_serializer(lead_obj: ML) -> Dict:
    data = dict(
        mortgage_id=lead_obj.mortgage_id, full_name=lead_obj.full_name, address=lead_obj.address,
        lender_name=lead_obj.lender_name, city=lead_obj.city, loan_amount=lead_obj.loan_amount,
        state=lead_obj.state, zip=lead_obj.zip, first_name=lead_obj.first_name, 
        last_name=lead_obj.last_name, loan_date=ML.loan_date)
    try:
        data['loan_date'] = date_object_to_string(data['loan_date'])
        data['ivr_response'] = lead_obj.mailing_response.ivr_response
        data['call_in_date_time'] = date_time_obj_to_str(lead_obj.mailing_response.call_in_date_time)
    except:
        pass
    return data


def get_mailing_single_mortgage_details(mortgage_id: str, agent_id: int) -> Dict:
    lead_obj = ML.query.join(MA, ML.mortgage_id == MA.mortgage_id).with_entities(ML, MA.notes, MA.created_at).filter(
        MA.mortgage_id == mortgage_id, MA.agent_id == agent_id).first()
    if not lead_obj:
        raise NoContent()
    ml_obj, notes, created_at = lead_obj
    data = mailer_single_lead_serializer(ml_obj)
    data.update({'notes': notes, 'agent_id': agent_id, 'created_at': convert_utc_to_timezone(created_at)})
    return data


def single_mortgage_public(mortgage_id: str, uuid: str) -> Dict:
    lead_obj = ML.query.filter_by(mortgage_id=mortgage_id, uuid=uuid).first()
    if not lead_obj:
        raise NoContent()
    data = mailer_single_lead_serializer(lead_obj)
    return data


# def mailing_bird_view(week: int, ) -> Dict:
#     now = datetime.utcnow().date() - timedelta(days=28 * week)
#     monday = now - timedelta(days=now.weekday())
#     last_week = monday + timedelta(days=28)
#     agents, created_date = {}, set()
#     try:
#         for i in MA.query.join(ML, ML.mortgage_id == MA.mortgage_id).join(Agent, MA.agent_id == Agent.id).join(
#             User, User.id == Agent.user_id).outerjoin(MR, MR.mortgage_id == ML.mortgage_id).filter(
#                 ML.created_date >= monday, ML.created_date < last_week).with_entities(
#                     MA.agent_id, ML.created_date, User.name, func.count(MR.id).label('call_attempt'), 
#                     func.count(ML.agent_id).label('total')).group_by(ML.created_date, MA.agent_id, User.name).all():
#             created_date.add(str(i.created_date))
#             if not agents.get(i.agent_id):
#                 agents[i.agent_id] = {'name': i.name, 'agent_id': i.agent_id, 'files': {}}
#             agents[i.agent_id]['files'][str(i.created_date)] = dict(
#                 total=i.total, 
#                 call_received_count=i.call_attempt,
#                 created_date=str(i.created_date))
#     except Exception as e:
#         print(e)
#         db.session.rollback()
#         db.session.close()
#         raise InternalError()
#     if created_date:
#         return {'agents': list(agents.values()), 'created_date': list(created_date)}
#     raise NoContent()


def mailing_campaign_status_change(mortgage_ids: List, agent_ids: List, lead_status: int) -> bool:
    MA.query.filter(MA.mortgage_id.in_(mortgage_ids), MA.agent_id.in_(agent_ids)).update({'lead_status': lead_status, 'lead_status_changed_at': datetime.utcnow()})
    CRUD.db_commit()
    status_logs = []
    agent_mortgage_status = defaultdict(int)
    can_sale = set()
    cannot_sale = set()
    for ld in MA.query.filter(
        MA.mortgage_id.in_(mortgage_ids)
        ).with_entities(MA.mortgage_id, MA.lead_status, MA.id.label('assignee_id')).all():
        status_logs.append(
            MLMSL(
                mailing_assignee_id=ld.assignee_id,
                lead_status=lead_status,
                user_id=g.user['id']
            )
        )
        if ld.mortgage_id in cannot_sale:
            continue
        if ld.lead_status in EXCLUDED_STATUS_FILTER_FROM_SALE:
            cannot_sale.add(ld.mortgage_id)
        else:
            can_sale.add(ld.mortgage_id)
    if status_logs:
        db.session.bulk_save_objects(status_logs)
    for mortgage_id in (set(agent_mortgage_status.keys()) - cannot_sale):
        if agent_mortgage_status[mortgage_id] >= 2:
            cannot_sale.add(mortgage_id)
        else:
            can_sale.add(mortgage_id)
    if cannot_sale:
        ML.query.filter(ML.mortgage_id.in_(list(cannot_sale)), ML.can_sale == True).update({'can_sale': False})
    if can_sale - cannot_sale:
        ML.query.filter(ML.mortgage_id.in_(list(can_sale - cannot_sale)), ML.can_sale == False).update({'can_sale': True})
    CRUD.db_commit()
    return True


def change_lead_status(category:int, data: Dict) -> bool:
    if g.user['role_id'] == 1 and (data.get('agent_id', 0) not in  g.user['agents']):
        agent_ids = [data['agent_id']]
    else:
        agent_ids = g.user['mailing_agent_ids'] if category == 1 else g.user['digital_agent_ids']
    if category == 1:
        mailing_campaign_status_change(data.pop('mortgage_ids'), agent_ids, data['lead_status'])
    # elif category == 2:
    #     digital_campaign_status_change(data, agent_ids)
    CRUD.db_commit()
    return True


def admin_mailing_suppression_decide(agent_mortgage: List, data: Dict) -> bool:
    # Admin can approve or reject the suppression requests
    # mortgage_id_list = set()
    status_logs = []
    for lead in agent_mortgage:
        MA.query.filter(MA.id == lead['id'], MA.agent_id == lead['agent_id']).update(
            {'suppression_approved_by': g.user['id'], **data})
        status_logs.append(
            MLMSL(
                mailing_assignee_id=lead['id'],
                lead_status=data.get('lead_status'),
                user_id=g.user['id']
            )
        )
    if status_logs:
        db.session.bulk_save_objects(status_logs)
        # bulk insert new status in MailingLeadMemberStatusLog
        # mortgage_id_list.add(lead['id'])
    # if data.get('lead_status') == 12:
        # ML.query.filter(ML.mortgage_id.in_(list(mortgage_id_list)), ML.disabled_in_marketplace == False).update(
        #     {'disabled_in_marketplace': True})
    CRUD.db_commit()
    return True


def notes_add_update(category: int, data: Dict) -> bool:
    if g.user['role_id'] != 1 and (data.get('agent_id') not in g.user['agents']):
        raise Forbidden()
    if category == 1:
        CRUD.update(MA, {'mortgage_id': data.pop('mortgage_id'), 'agent_id': data.pop('agent_id')}, 
                    {'notes': data.get('notes', '')})
    # else:
    #     CRUD.update(LeadMember, {'digital_lead_id': data.pop('id'), 'agent_id': data.pop('agent_id')}, {'notes': data.get('notes', '')})
    return True


class CopyMoveMailingLead:    
    def __init__(self, data: Dict):
        print(data)
        self.mortgage_ids = data['mortgage_ids']
        self.to_user_id = data['to_user_id']
        self.to_agent_id = data['to_agent_id']
        self.from_agent_ids = list(set(data['mortgage_ids'].values()))
        self.new_owner_agent_ids = [agent_id.id for agent_id in Agent.query.filter_by(
            user_id=data['to_user_id']).with_entities(Agent.id).all()]
        existing_ids = [i.mortgage_id for i in MA.query.with_entities(MA.mortgage_id).filter(
            MA.mortgage_id.in_(list(self.mortgage_ids.keys())), 
            MA.agent_id.in_(self.new_owner_agent_ids)).all()]
        if existing_ids:
            raise Conflict(f'The mortgage {", ".join(str(mi) for mi in existing_ids)} is already assigned so please remove and try again.')

    def copy_leads(self) -> bool:
        ids = []
        print(self.mortgage_ids)
        for mortgage_id, from_agent, campaign_name in MA.query.with_entities(
            MA.mortgage_id, MA.agent_id, MA.campaign_name).filter(
                MA.mortgage_id.in_(list(self.mortgage_ids.keys())), 
                MA.agent_id.in_(self.from_agent_ids)).all():
            if mortgage_id in ids or self.mortgage_ids.get(str(mortgage_id)) != from_agent:
                continue
            ids.append(mortgage_id)
            data = dict(
                mortgage_id=mortgage_id, 
                agent_id=self.to_agent_id,
                copied_by_user=g.user['id'],
                copied_from_agent_id=from_agent,
                copied=True,
                campaign_name=campaign_name,
                copied_at=datetime.utcnow()
                )
            # if purchased_user_id:
            #     data['purchased_user_id'] = self.to_user_id
            lm = MA(**data)
            db.session.add(lm)
        CRUD.db_commit()
        return True
    
    def move_leads(self) -> bool:
        ids = []
        print(self.mortgage_ids)
        for lm in MA.query.filter(
            MA.mortgage_id.in_(list(self.mortgage_ids.keys())),
            MA.agent_id.in_(self.from_agent_ids)).all():
            print(lm)
            if lm.mortgage_id in ids or self.mortgage_ids.get(str(lm.mortgage_id)) != lm.agent_id:
                continue
            ids.append(lm.mortgage_id)
            lm.moved_at = datetime.utcnow()
            moved_history = lm.moved_history if lm.moved_history else []
            moved_history.append({'moved_from_agent_id': lm.agent_id, 'moved_by_user': lm.g.user['id'], 'moved_at': str(lm.moved_at), 'moved_to': self.to_agent_id})
            lm.moved_history = moved_history
            lm.moved_from_agent_id = lm.agent_id
            lm.agent_id = self.to_agent_id
            lm.lead_status = 1
            lm.moved = True
            lm.moved_by_user = g.user['id']
        CRUD.db_commit()
        return True


# TODO: delete this stats
# def get_multiple_agents_stats_campaign_view(file_id: int) -> List:
#     data = {}
#     try:
#         for i in MA.query.join(ML, MA.mortgage_id == ML.mortgage_id).join(Agent, Agent.id == MA.agent_id).join(
#             User, User.id == Agent.user_id).outerjoin(MR, MR.mortgage_id == ML.mortgage_id).with_entities(
#                 MA.agent_id, func.count(MA.agent_id).label('total'), MR.completed, User.name).filter(
#                     ML.file_id == file_id).group_by(MA.agent_id, MR.completed, User.name, ML.state).all():
#             if not data.get(i.agent_id):
#                 data[i.agent_id] = {'agent_id': i.agent_id, 'name': i.name, 'True': 0 if i.completedis None else i.total, 
#                                     'total': i.total}
#             else:
#                 data[i.agent_id] |= {
#                     'total': i.total+data[i.agent_id]['total'], 
#                     'True': data[i.agent_id]['True'] if i.completedis None else (data[i.agent_id]['True'] + i.total)}
#         if data:
#             return list(data.values())
#     except Exception as e:
#         db.session.rollback()
#         print(f"get_multiple_agents_stats_campaign_view -> {e}")
#     raise NoContent()

# TODO: delete this stats
# def get_multiple_agents_stats_campaign_state_view(file_id: int) -> List:
#     data = {}
#     try:
#         for i in MA.query.join(ML, MA.mortgage_id == ML.mortgage_id).join(Agent, Agent.id == MA.agent_id).join(
#             User, User.id == Agent.user_id).outerjoin(MR, MR.mortgage_id == ML.mortgage_id).with_entities(
#                 MA.agent_id, func.count(MA.agent_id).label('total'), ML.state, MR.completed, User.name).filter(
#                     ML.file_id == file_id).group_by(MA.agent_id, MR.completed, User.name, ML.state).all():
#             if not data.get(i.agent_id):
#                 data[i.agent_id] = {'agent_id': i.agent_id, 'name': i.name, 
#                                     'state': {i.state: {'state': i.state, str(i.completed): i.total, 'total': i.total}}}
#                 continue
#             if not data[i.agent_id]['state'].get(i.state):
#                 data[i.agent_id]['state'][i.state] = {'state': i.state, str(i.completed): i.total, 'total': i.total}
#             else:
#                 print(data[i.agent_id]['state'][i.state])
#                 data[i.agent_id]['state'][i.state].update({'total': i.total+data[i.agent_id]['state'][i.state]['total'], 
#                                                             str(i.completed): i.total})
#         if data:
#             result = [{"agent_id": info['agent_id'], 'name': info['name'], 'state': list(info.pop('state', {}).values())} for info in data.values()]
#             return result
#     except Exception as e:
#         db.session.rollback()
#         print(f"else: -> {e}")
#     raise NoContent()


def upload_sales_docs(category: int, mortgage_id: str, agent_id: int, files:  Optional[List[FileStorage]] = None) -> bool:
    attachments = []
    if category == 1:
        query_response = MA.query.join(
            ML, ML.mortgage_id == MA.mortgage_id
            ).with_entities(ML, MA).filter(
                MA.mortgage_id == mortgage_id, MA.agent_id.in_(g.user['mailing_agent_ids'])).first()
    # elif category == 2:
    #     query_response = LeadMember.query.join(DigitalLeads, DigitalLeads.id == LeadMember.digital_lead_id).with_entities(
    #         DigitalLeads, LeadMember).filter(LeadMember.digital_lead_id == id_, 
    #                                          LeadMember.agent_id.in_(g.user['digital_agent_ids'])).first()
    if not query_response:
        raise Forbidden()
    for file_is in files:
        file_object = files.get(file_is)
        file_name = file_object.filename
        new_file_name = f"{g.user['id']}_{round(datetime.utcnow().timestamp())}_{file_name}"
        file_type = file_object.content_type
        file_contents = file_object.read()
        AmazonServices().put_object(
            file_is=file_contents,
            path=f"{Config_is.ENVIRONMENT}/suppression-docs/{category}/{mortgage_id}/{agent_id}/{new_file_name}",
            content_type=file_type
            )

        encoded_file = base64.b64encode(file_contents).decode('ascii')
        attachments.append({'encoded_file': encoded_file, 'name': file_name, 'type': file_type})
    query_response[1].lead_status = 7
    query_response[0].can_sale = False
    if not query_response[1].sold_date:
        query_response[1].sold_date = convert_datetime_to_timezone_date(datetime.utcnow())
    query_response[1].suppressed_by = g.user['id']
    CRUD.db_commit()
    html_data = render_template(
        "suppression_requests.html", mortgage_id=mortgage_id, full_name=query_response[0].full_name,
        agent_name=g.user['name'], sold_date=date_object_to_string(query_response[1].sold_date),
        link_is=f"{Config_is.FRONT_END_URL}/suppression-list")
    SendgridEmailSending(
        Config_is.SUPPRESSION_LIST_ALERT_TO, 
        f"Suppression Proof Uploaded: Mortgage {mortgage_id}",
        html_data, 10).send_email_with_attachments(attachments)
    return True

        
def delete_sales_docs(category: int, mortgage_id: str, agent_id: int, file_names: List) -> bool:
    s3_client = AmazonServices()
    if category == 1:
        if g.user['role_id'] != 1:
            if agent_id not in g.user['mailing_agent_ids'] or not MA.query.filter(MA.mortgage_id == mortgage_id, MA.agent_id == agent_id).count():
                raise Forbidden()
        # elif category == 2:
        #     if not LeadMember.query.filter(
        #         LeadMember.digital_lead_id == id_, LeadMember.agent_id.in_(g.user['digital_agent_ids'])).count():
        #         raise Forbidden()
    for file_is in file_names:
        s3_client.delete_object(f"{Config_is.ENVIRONMENT}/suppression-docs/{category}/{mortgage_id}/{agent_id}/{file_is}")
    return True


def list_sold_documents(category: int, mortgage_id: str, agent_id: int) -> List:
    if category == 1:
        if g.user['role_id'] != 1:
            if agent_id not in g.user['mailing_agent_ids'] or not MA.query.filter(MA.mortgage_id == mortgage_id, MA.agent_id.in_(g.user['mailing_agent_ids'])).count():
                raise Forbidden()
        # elif category == 2:
        #     if not LeadMember.query.filter(LeadMember.digital_lead_id == id_, LeadMember.agent_id.in_(g.user['digital_agent_ids'])).count():
        #         raise Forbidden()
        #     s3_path = s3_path + '/digital'
    result = AmazonServices().list_objects(f"{Config_is.ENVIRONMENT}/suppression-docs/{category}/{mortgage_id}/{agent_id}/")
    if result:
        return result
    raise NoContent()


def list_mailing_suppression_requests(page: int, per_page: int) -> Tuple:
    result = []
    try:
        lead_objs = ML.query.join(
            MR, MR.mortgage_id == ML.mortgage_id).join(MA, MA.mortgage_id==ML.mortgage_id).join(
                Agent, Agent.id == MA.agent_id).join(User, User.id == Agent.user_id).with_entities(
                    ML.mortgage_id, ML.source_id, ML.full_name, ML.state, ML.city, MA.id.label('assignee_id'), MA.agent_id, MA.notes, 
                    MA.lead_status, MA.suppression_rejection_msg, MA.campaign_name, MR.call_in_date_time, MR.completed, 
                    MR.ivr_response, MR.ivr_logs, MA.sold_date, User.name.label('agent_name'), ML.zip, 
                    ML.city, ML.address, ML.first_name, ML.last_name, ML.lender_name, ML.loan_amount, ML.loan_date).filter(
                        MA.lead_status == 7).order_by(MA.modified_at.desc()).paginate(
                            page=page, per_page=per_page, error_out=False)
        for data in lead_objs.items:
            data = data._asdict()
            data['call_in_date_time'] = date_time_obj_to_str(data['call_in_date_time'])
            for dt in ('sold_date', 'loan_date'):
                data[dt] = date_object_to_string(data[dt])
            result.append(data)
        if result:
            return result, {'total': lead_objs.total, 'current_page': lead_objs.page, 'length': len(result), 
                            'per_page': lead_objs.per_page}
    except Exception as e:
        print(f"list_mailing_suppression_requests {e}")
    raise NoContent()


def get_mailing_leads_search(search: str) -> Dict:
    lead_obj = MA.query.join(ML, ML.mortgage_id == MA.mortgage_id).outerjoin(
        MR, MR.mortgage_id == ML.mortgage_id).with_entities(
            ML.mortgage_id, ML.source_id, ML.full_name, ML.state, MA.id.label('assignee_id'), MA.agent_id, MA.notes, 
            MA.lead_status, MA.suppression_rejection_msg, MA.campaign_name, MR.call_in_date_time, MR.completed, 
            MR.ivr_response, MR.ivr_logs, ML.zip, ML.city, ML.address, ML.first_name, ML.last_name, 
            ML.lender_name, ML.loan_amount, ML.loan_date)
    if g.user['role_id'] != 1:
        lead_obj = lead_obj.filter(MA.agent_id.in_(g.user['mailing_agent_ids']))
    lead_obj = lead_obj.filter(MA.mortgage_id == search).first()
    if not lead_obj:
        raise NoContent()
    data = lead_obj._asdict()
    data['loan_date'] = date_object_to_string(data['loan_date'])
    data['call_in_date_time'] = date_time_obj_to_str(lead_obj.call_in_date_time)
    return data

            
# def get_leads_count_for_territory(category: int) -> List[Dict]:
#     if category == 1:
#         leads_data = (
#             ML.query
#             .outerjoin(MR, ML.mortgage_id == MR.mortgage_id)
#             .join(MA, ML.mortgage_id == MA.mortgage_id)
#             .filter(ML.agent_id.in_(g.user['mailing_agent_ids']))
#             .with_entities(
#                 func.count(func.distinct(MA.mortgage_id)).label("total_leads"),
#                 func.count(func.distinct(ML.state)).label("total_territory"),   
#                 func.count(func.distinct(MA.mortgage_id)).filter(
#                     and_(
#                         MR.completed == True,
#                         ~MA.lead_status.in_(EXCLUDED_STATUS_FILTER_FROM_SALE)
#                     )
#                 ).label("completed"),
#                 func.count(func.distinct(MA.mortgage_id)).filter(
#                     and_(
#                         MR.completed == False,
#                         ~MA.lead_status.in_(EXCLUDED_STATUS_FILTER_FROM_SALE)
#                     )
#                 ).label("incomplete"),
#                 func.count(func.distinct(MA.mortgage_id)).filter(
#                     and_(
#                         MR.completed == True,
#                         MA.lead_status == 7
#                     )
#                 ).label("completed_sold"),
#                 # func.count(func.distinct(MA.mortgage_id)).filter(
#                 #     and_(
#                 #         MR.completed== True,
#                 #         MA.lead_status == 12
#                 #     )
#                 # ).label("completed_suppressed"),
#                 func.count(func.distinct(MA.mortgage_id)).filter(
#                     and_(
#                         MR.completed == False,
#                         MA.lead_status == 7
#                     )
#                 ).label("incomplete_sold"),
#                 # func.count(func.distinct(MA.mortgage_id)).filter(
#                 #     and_(
#                 #         MR.completed == False,
#                 #         MA.lead_status == 12
#                 #     )
#                 # ).label("incomplete_suppressed"),
#             )
#             .first()
#         )

#         return leads_data._asdict()



# def get_statewise_territory_leads_count(category: int, page: int, per_page: int) -> Tuple:
#     if category == 1:
#         leads_data = (
#             ML.query
#             .outerjoin(MR, ML.mortgage_id == MR.mortgage_id)
#             .join(MA, ML.mortgage_id == MA.mortgage_id)
#             .filter(MA.agent_id.in_(g.user['mailing_agent_ids']))
#             .with_entities(
#                 ML.state,
#                 func.count(MA.mortgage_id).label("total_leads"),
#                 func.count(MA.mortgage_id).filter(
#                     and_(
#                         MR.completed== True,
#                         ~MA.lead_status.in_(EXCLUDED_STATUS_FILTER_FROM_SALE)
#                     )
#                 ).label("completed"),
#                 func.count(MA.mortgage_id).filter(
#                     and_(
#                         MR.completed== True,
#                         MA.lead_status == 7
#                     )
#                 ).label("completed_sold"),
#                 # func.count(func.distinct(MA.mortgage_id)).filter(
#                 #     and_(
#                 #         MR.completed== True,
#                 #         MA.lead_status == 12
#                 #     )
#                 # ).label("completed_suppressed"),
#                 func.count(MA.mortgage_id).filter(
#                     and_(
#                         MR.completed== False,
#                         ~MA.lead_status.in_(EXCLUDED_STATUS_FILTER_FROM_SALE)
#                     )
#                 ).label("incomplete"),
#                 func.count(MA.mortgage_id).filter(
#                     and_(
#                         MR.completed== False,
#                         MA.lead_status == 7
#                     )
#                 ).label("incomplete_sold"),
#                 # func.count(MA.mortgage_id).filter(
#                 #     and_(
#                 #         MR.completed== False,
#                 #         MA.lead_status == 12
#                 #     )
#                 # ).label("incomplete_suppressed"),
#             )
#             .group_by(ML.state)
#             .paginate(page=page, per_page=per_page, error_out=False)
#         )

#         result = [row._asdict() for row in leads_data.items]

#         return result, {
#             'current_page': leads_data.page,
#             'per_page': leads_data.per_page,
#             'total': leads_data.total,
#             'length': len(result)
#         }

def get_campaign_leads_view(page: int, per_page: int, marketplace: str) -> Tuple:
    result = []
    try:
        lead_query = MA.query.join(
            ML, ML.mortgage_id == MA.mortgage_id
        ).outerjoin(
            MR, MR.mortgage_id == MA.mortgage_id
        ).filter(
                MA.agent_id.in_(g.user['mailing_agent_ids'])
            ).with_entities(
            MA.campaign_name,
            func.count(func.distinct(ML.mortgage_id)).label("total_leads"),
            func.count(func.distinct(ML.mortgage_id)).filter(
                and_(
                    MR.completed== True,
                    ~MA.lead_status.in_(EXCLUDED_STATUS_FILTER_FROM_SALE)
                )
            ).label("completed"),
            func.count(func.distinct(ML.mortgage_id)).filter(
                and_(
                    MR.completed== False,
                    ~MA.lead_status.in_(EXCLUDED_STATUS_FILTER_FROM_SALE)
                )
            ).label("incomplete"),
            # func.count(func.distinct(ML.mortgage_id)).filter(
            #     MA.lead_status == 12
            # ).label("suppressed_leads"),
            func.count(func.distinct(ML.mortgage_id)).filter(
                MA.lead_status == 7
            ).label("sold"),
        ).group_by(
           MA.campaign_name, ML.source_id
        ).order_by(
           desc(MA.campaign_name)
        )

        if marketplace == "1":
            lead_query = lead_query.filter(MA.purchased_user_id == g.user["id"])
        else:
            lead_query = lead_query.filter(MA.purchased_user_id.is_(None))
        lead_query = lead_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        for leads in lead_query.items:
            result.append(leads._asdict())

        if result:
            return result, {
                "total": lead_query.total,
                "current_page": lead_query.page,
                "length": len(result),
                "per_page": lead_query.per_page
            }

    except Exception as e:
        print(f"get_campaign_leads error: {e}")

    raise NoContent()


def get_my_leads_status_count() -> Dict:
    leads_data = (
        MA.query
        .with_entities(
            func.count(MA.mortgage_id).filter(MA.lead_status == 2),
            func.count(MA.mortgage_id).filter(MA.lead_status == 3),
            func.count(MA.mortgage_id).filter(MA.lead_status == 4),
            func.count(MA.mortgage_id).filter(MA.lead_status == 6),
            func.count(MA.mortgage_id).filter(MA.lead_status == 7)

        )
        .first()
    )

    return {
        2: leads_data[0],
        3: leads_data[1],
        4: leads_data[2],
        6: leads_data[3],
        7: leads_data[4],
    }

def single_mailing_lead_status_log(mailing_assignee_id: int, agent_id: int) -> List:
    log_objs = MLMSL.query.join(MA, MA.id == MLMSL.mailing_assignee_id).filter(
        MLMSL.mailing_assignee_id == mailing_assignee_id, MA.agent_id.in_(g.user['mailing_agent_ids'])).with_entities(
        MLMSL.id, MLMSL.lead_status, MLMSL.created_at).order_by(
        MLMSL.id.desc()).all()

    return [{
            "id": log.id,
            "lead_status": log.lead_status,       
            "created_at": convert_utc_to_timezone(log.created_at)
        } for log in log_objs]


def get_multiple_agents_stats_campaign_view(campaign_name: str):
    data = {}
    try:
        for i in MA.query.join(ML, ML.mortgage_id == MA.mortgage_id).outerjoin(
            MR, MR.mortgage_id == ML.mortgage_id).filter(MA.campaign_name == campaign_name).with_entities(MA.agent_id, 
                    func.count(MA.agent_id), MR.completed).group_by(MR.completed, MA.agent_id).all():
            if not data.get((i[0], i[2])):
                data[(i[0], i[2])] = {"agent_id": i[0], "completed": i[2], "count": i[1]}
            else:
                data[(i[0], i[2])]["count"] += i[1]
        for u in Agent.query.join(User, User.id == Agent.user_id).filter(Agent.id.in_({k[0] for k in data.keys()})).with_entities(
                Agent.id, User.name).all():
            for key in data:
                if key[0] == u[0]:
                    data[key]["agent_name"] = u[1]
        return list(data.values())
    except Exception as e:
        db.session.rollback()
        print(f"thread_agents_stats_campaign -> {e}")
    raise NoContent()


def get_multiple_agents_stats_campaign_state_view(campaign_name: str) -> List:
    data = {}
    try:
        for i in MA.query.join(ML, ML.mortgage_id == MA.mortgage_id).outerjoin(
            MR, MR.mortgage_id == ML.mortgage_id).filter(MA.campaign_name == campaign_name).with_entities(MA.agent_id, 
                    func.count(MA.agent_id), MR.completed, ML.state).group_by(MA.agent_id, MR.completed, ML.state).all():
            if not data.get(i[0]):
                data[i[0]] = {'agent_id': i[0], 'state': {}}
            if not data[i[0]]['state'].get(i[3]):
                data[i[0]]['state'][i[3]] = {'state': i[3], 'completed': 0, 'total': 0, 'incomplete': 0}
            data[i[0]]['state'][i[3]]['total'] += i[1]
            if i[2] is True:
                data[i[0]]['state'][i[3]]['completed'] += i[1]
            elif i[2] is False:
                data[i[0]]['state'][i[3]]['incomplete'] += i[1]
        for u in Agent.query.join(User, User.id == Agent.user_id).filter(Agent.id.in_(list(data.keys()))).with_entities(
                Agent.id, User.name).all():
            data[u[0]]['agent_name'] = u[1]
            data[u[0]]['state'] = list(data[u[0]]['state'].values())
        return list(data.values())
    except Exception as e:
        db.session.rollback()
        print(f"thread_agents_stats_campaign -> {e}")
    raise NoContent()


