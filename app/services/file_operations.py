import csv
import io
import queue
import base64
from uuid import uuid4
from math import ceil
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

from flask import g, request
from sqlalchemy.orm import Query
from PIL import Image

from app.services.crud import CRUD
from app.models import (
    UploadedFile as UF,
    MailingLead as ML,
    MailingAssignee as MA,
    MailingResponse as MR,
    StripeCustomerSubscription as SCS,
    Agent, User
)
from app.services.aws_services import AmazonServices
from app.services.utils import (
    convert_datetime_to_timezone_date, 
    date_time_obj_to_str,
    date_object_to_string
    )
from app.services.custom_errors import *
from app import app, logging, db, redis_obj
from constants import LEAD_STATUS
from config import Config_is


def upload_purchase_agreement(id_: str, base64_img: str) -> bool:
    # Remove data URI scheme header
    header, encoded = base64_img.split(',', 1)
    image_data = base64.b64decode(encoded)
    # Open image using PIL
    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    # Convert image to PDF
    pdf_buffer = io.BytesIO()
    image.save(pdf_buffer, format="PDF")
    pdf_buffer.seek(0)
    # Upload to S3
    # a = AmazonServices().put_object(
    #     Bucket=Config_is.S3_BUCKET_NAME,
    #     Key=f"{Config_is.ENVIRONMENT}/purchase_agreement/{id_}.pdf",
    #     Body=pdf_buffer,
    #     ContentType='application/pdf'
    # )
    a = AmazonServices().put_object(pdf_buffer, f"{Config_is.ENVIRONMENT}/purchase_agreement/{id_}.pdf", 'application/pdf')
    print(a)
    return True


def mailing_campaign_bulk_save(
    thread_response, lead_data: List, lead_assignee: List[MA]
    ):
    with app.app_context():
        try:
            db.session.bulk_save_objects(lead_data)
            db.session.commit()
            db.session.bulk_save_objects(lead_assignee)
            thread_response.put(True)
            db.session.commit()
        except Exception as e:
            print(f"bulk_save Exception: {e}")
            logging.error(f"bulk_save Exception: {e}")
            thread_response.put(str(e))
            db.session.rollback()
        db.session.close()
    return True


# def iul_campaign_bulk_save(thread_response, file_id: int, db_data: List, db_agents: Dict, campaign: str):
#     print('iul_campaign_bulk_save')
#         with app.app_context():
#             try:
#                 db.session.bulk_save_objects(db_data)
#                 db.session.commit()
#                 leads = {ld[1]: ld[0] for ld in DigitalLeads.query.with_entities(DigitalLeads.id, DigitalLeads.uuid).filter_by(
#                     file_id=file_id).all()}
#                 print(leads)
#                 for u, a in db_agents.items():
#                     lm = LeadMember(agent_id=a, digital_lead_id=leads[u], campaign_name=campaign)
#                     db.session.add(lm)
#                 db.session.commit()
#                 thread_response.put(True)
#             except Exception as e:
#                 print(f"bulk_save Exception: {e}")
#                 logging.error(f"bulk_save Exception: {e}")
#                 thread_response.put(str(e))
#                 db.session.rollback()
#             db.session.close()
#     return True


def csv_header_modify(csv_row: Dict, csv_headings: Dict) -> Dict:
    for variable, column in csv_headings.items():
        try:
            csv_row[variable] = csv_row.pop(column)
        except KeyError:
            pass
    return csv_row


def csv_mailing_input_with_mortgage_id(
        campaign: str, file_is: object, source_id: int, 
        category: int, csv_headers: Dict):
    threads, delete_table, run, thread_response = [], None, True, queue.Queue()
    mortgage_ids = []
    uploaded = CRUD.create(
        UF, {
            "name": file_is.filename,
            "source_id": source_id,
            "category": category,
            "uploaded_by": g.user["id"],
            "campaign": campaign,
        },
    )
    created_date = convert_datetime_to_timezone_date(uploaded.created_at)
    with io.TextIOWrapper(file_is) as fp:
        reader = csv.DictReader(fp)
        # if (
        #     not csv_headers.get("AGENT_ID")
        #     or csv_headers.get("Agent Identifier") not in reader.fieldnames
        # ):
        if not csv_headers.get("AGENT_ID"):
            raise BadRequest("Agent Column name should be either 'AGENT_ID' or 'Agent Identifier'")
        counter = 0
        while run:
            lead_data, assignee_data = [], []
            for _ in range(10000):
                try:
                    row = next(reader)
                    if not row.get(csv_headers["AGENT_ID"]):
                        continue
                    counter += 1
                    csv_modified = csv_header_modify(row, csv_headers)
                    unique_id = uuid4().hex[:10]
                    # disabled_in_marketplace = False if row.get(STATE, '') not in DISABLED_STATES else True
                    mortgage_ids.append(int(row.get("MORTGAGE_ID")))
                    lead_data.append(
                        ML(
                            mortgage_id=row.get("MORTGAGE_ID"),
                            file_id=uploaded.id,
                            uuid=unique_id,
                            full_name=(
                                row.get("FULL_NAME", "")
                                or f"{row.get('FIRST', '')} {row.get('LAST', '')}"
                            ).strip(),
                            first_name=row.get('FIRST', ''),
                            last_name=row.get('LAST', ''),
                            state=row.get("STATE", "").upper(),
                            agent_id=row.get("AGENT_ID"),
                            city=row.pop('CITY'),
                            lender_name=row.get('LENDER_NAME'),
                            loan_amount=float(row.get('LOAN_AMOUNT', '0').lstrip('$').replace(',', '')),
                            loan_date=row.get('LOAN_DATE'),
                            loan_type=row.get('LOAN_TYPE'),
                            address=csv_modified.get("ADDRESS",''),
                            zip=csv_modified.get("ZIP"),
                            source_id=source_id,
                            csv_data=csv_modified,
                            created_date=created_date
                        )
                    )
                    assignee_data.append(MA(agent_id=row.get("AGENT_ID"), mortgage_id=row.get("MORTGAGE_ID"), campaign_name=campaign))
                    # disabled_in_marketplace=disabled_in_marketplace,
                    if counter % 2500 == 0:
                        t = Thread(
                            target=mailing_campaign_bulk_save,
                            args=(thread_response, lead_data, assignee_data),
                        )
                        lead_data, assignee_data = [], []
                        threads.append(t)
                        t.start()            
                except StopIteration:
                    run = False
                    break
            if counter and counter % 2500 != 0:
                t = Thread(
                    target=mailing_campaign_bulk_save,
                    args=(thread_response, lead_data, assignee_data),
                )
                threads.append(t)
                t.start()
    file_is.seek(0)
    AmazonServices().acl_file_upload_obj_s3(file_is, f"{Config_is.ENVIRONMENT}/weekly-files/{uploaded.id}.csv", "text/csv")
    for t in threads:
        t.join()
        try:
            response_is = thread_response.get_nowait()
            if response_is is True:
                continue
            if "duplicate key value violates unique constraint " in str(response_is):
                print(f"dupliocate {response_is}")
                logging.info(f"response_is {response_is} violates")
                delete_table = f"Duplicate mortgage Id"
                break
            else:
                delete_table = str(response_is)
                break
        except Exception as e:
            print(f"our exception {e}")
            logging.error(f"our exception {e}")
            delete_table = str(e)
            break
    else:
        mortgage_ids.sort()
        redis_obj.set("new_file_name", int(mortgage_ids[-1]) + 1)
        return {"file_id": uploaded.id, "total_records": counter, "threads": len(threads)}
    logging.info(f"finale if {delete_table} {uploaded.id}")
    print(f"finale if {delete_table} {uploaded.id}")
    try:
        UF.query.filter_by(id=uploaded.id).delete()
        db.session.commit()
        print("delete committed")
    except Exception as e:
        print(e)
        db.session.rollback()
        logging.info("Deletion committed")
    raise BadRequest(delete_table)


def thread_download_mortgage_file(
        leads_obj: Query, page: int, per_page: int, 
        campaign: str, thread_response
        ):
    try:
        with app.app_context():
            response = []
            with db.session.begin():
                try:
                    leads_obj = leads_obj.paginate(
                        page=page, per_page=per_page, error_out=False
                    )
                    for data in leads_obj.items:
                        data = data._asdict()
                        data |= dict(campaign=campaign, loan_date=date_object_to_string(data['loan_date']))
                        response.append(data)
                    thread_response.put(response)
                except Exception as e:
                    print(f"thread_download_mortgage_file Exception {e}")
                    logging.error(f"thread_download_mortgage_file Exception {e}")
                    db.session.rollback()
                    thread_response.put(str(e))
            db.session.close()
    except Exception as e:
        print(f"thread_download_mortgage_file main exception {e}")
        logging.exception(f"thread_download_mortgage_file main exception {e}")
    return True


def download_mortgage_file(file_id: str, campaign: str) -> List:
    leads_obj = ML.query.filter(ML.file_id == file_id)
    leads_obj = leads_obj.with_entities(
        ML.mortgage_id, ML.full_name, ML.agent_id, ML.state, ML.city, ML.address, ML.zip, 
        ML.lender_name, ML.first_name, ML.last_name, ML.loan_type, ML.loan_amount,
        ML.loan_date
    ).order_by(ML.mortgage_id)

    return threaded_file_download(
        query=leads_obj,
        campaign=campaign
    )


def uploaded_file_info_list(
    category_id: int, page: int, per_page: int, search: Optional[str] = None
    ) -> Tuple:
    file_obj = UF.query.filter(UF.category == category_id)
    if search:
        file_obj = file_obj.filter(UF.campaign.ilike(f"%{search}%"))
    file_obj = file_obj.order_by(UF.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    result = [f.to_dict() for f in file_obj.items]
    if result:
        return result, {
            "total": file_obj.total,
            "current_page": file_obj.page,
            "per_page": file_obj.per_page,
            "length": len(result),
        }
    raise NoContent()


def all_mailer_leads_except_mailed_thread(
    page: int, per_page: int, lead_query: Query, thread_response
    ):
    try:
        with app.app_context():
            response = []
            with db.session.begin():
                try:
                    leads = lead_query.paginate(
                        page=page, per_page=per_page, error_out=False
                    )
                    for data in leads.items:
                        data = data._asdict()
                        data['loan_date'] = date_object_to_string(data['loan_date'])
                        data["lead_status"] = LEAD_STATUS.get(data["lead_status"])
                        data['call_in_time'] = date_time_obj_to_str(data.pop('call_in_date_time'))
                        response.append(data)
                    thread_response.put(response)
                except Exception as e:
                    print(f"all_mailer_leads_except_mailed_thread Exception: {e}")
                    logging.error(
                        f"all_mailer_leads_except_mailed_thread Exception: {e}"
                    )
                    db.session.rollback()
                    thread_response.put(str(e))
            db.session.close()
    except Exception as e:
        print(f"all_mailer_leads_except_mailed_thread main exception {e}")
        logging.exception(f"all_mailer_leads_except_mailed_thread main exception {e}")
    return True


def download_all_mailer_leads_except_mailed(agent_id: int) -> List:
    if g.user["role_id"] == 1 and request.args.get("agent_id"):
        agent_id = [request.args.get("agent_id")]
    else:
        agent_id = g.user["mailing_agent_ids"]
    page, per_page, result, thread_response = 0, 10000, [], queue.Queue()
    query = (
        ML.query.join(MA, ML.mortgage_id == MA.mortgage_id)
        .join(MR, MR.mortgage_id == ML.mortgage_id)
        .with_entities(
            MA.mortgage_id,
            ML.full_name,
            ML.city,
            ML.address,
            ML.state,
            ML.city,
            MA.agent_id,
            MA.campaign_name,
            MA.lead_status,
            MR.ivr_response,
            MR.call_in_date_time,
            MR.completed,
            ML.zip,
            ML.lender_name,
            ML.first_name,
            ML.last_name,
            ML.loan_amount,
            ML.loan_date
        )
        .filter(MA.agent_id.in_(agent_id))
        .order_by(MR.call_in_date_time.desc())
    )
    # LeadMember.purchased_user_id.is_(None)
    try:
        count = query.distinct(ML.mortgage_id).count()
    except:
        db.session.rollback()
        count = 0
    if not count:
        raise NoContent()
    total_pages = ceil(count / per_page)
    with ThreadPoolExecutor(max_workers=5) as executor:
        for page in range(1, total_pages + 1):
            executor.submit(
                all_mailer_leads_except_mailed_thread,
                page,
                per_page,
                query,
                thread_response,
            )
    for page in range(1, total_pages + 1):
        val = thread_response.get(timeout=120)
        if isinstance(val, list):
            result.extend(val)
        else:
            raise InternalError()
    return result


def thread_download_leads_with_time_type(
    page: int, per_page: int, db_query: Query, thread_response
    ):
    with app.app_context():
        response = []
        with db.session.begin():
            try:
                leads = db_query.paginate(page=page, per_page=per_page, error_out=False)
                for data in leads.items:
                    data = data._asdict()
                    data |= (
                        dict(
                            lead_status=LEAD_STATUS.get(data.pop("lead_status")),
                            loan_date=date_object_to_string(data['loan_date'])
                            )
                        )
                    data["call_in_time"] = date_time_obj_to_str(data.pop("call_in_date_time", None))
                    response.append(data)
                print(len(response))
                thread_response.put(response)
            except Exception as e:
                print(f"thread_download_leads_with_time_type Exception: {e}")
                logging.error(f"thread_download_leads_with_time_type Exception: {e}")
                db.session.rollback()
                thread_response.put(str(e))
        db.session.close()
    return True


def report_download_processed_mailer_leads(data: Dict, page: int) -> List:
    per_page, result, thread_response = 10000, [], queue.Queue()
    leads_query = (
        MA.query.join(ML, ML.mortgage_id == MA.mortgage_id)
        .join(MR, MR.mortgage_id == ML.mortgage_id)
        .join(Agent, Agent.id == MA.agent_id)
        .join(User, User.id == Agent.user_id)
        .with_entities(
            MA.mortgage_id,
            ML.full_name,
            ML.state,
            ML.city,
            ML.address,
            MA.agent_id,
            MA.campaign_name,
            MA.lead_status,
            MR.ivr_response,
            MR.completed,
            MR.call_in_date_time,
            User.name.label("agent_name"),
            ML.zip,
            ML.lender_name,
            ML.loan_amount,
            ML.loan_date
        )
        .filter(
            MR.call_in_date_time.between(
                datetime.strptime(f"{data['start_date']}", "%m-%d-%Y"),
                datetime.strptime(f"{data['end_date']}", "%m-%d-%Y") + timedelta(days=1),
            )
        )
        .order_by(MR.call_in_date_time.desc())
    )
    if "completed" in data:
        leads_query = leads_query.filter(MR.completed == data["completed"])
    if not page:
        try:
            count = leads_query.distinct(MA.mortgage_id).count()
        except:
            count = 0
            db.session.rollback()
        if count == 0:
            raise NoContent()
        return {"total": count, "pages": ceil(count / per_page)}
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.submit(
            thread_download_leads_with_time_type,
            int(page),
            per_page,
            leads_query,
            thread_response,
        )
    val = thread_response.get(timeout=180)
    if isinstance(val, list):
        result.extend(val)
    else:
        raise InternalError()
    return result

def download_campaign_leads(campaign: str) -> List:
    query = ML.query.join(MA, MA.mortgage_id == ML.mortgage_id).filter(
        MA.campaign_name == campaign
    )
    if g.user["role_id"] != 1:
        query = query.filter(MA.agent_id.in_(g.user['mailing_agent_ids']))

    query = query.with_entities(
        ML.mortgage_id, ML.full_name, ML.agent_id, ML.state, ML.city, ML.address, ML.zip,
        ML.lender_name, ML.first_name, ML.last_name, ML.loan_type, ML.loan_amount,
        ML.loan_date
    ).order_by(ML.mortgage_id)

    return threaded_file_download(
        query=query,
        campaign=campaign
    )

def threaded_file_download(
    query: Query,
    campaign: str,
    per_page: int = 15000,
    timeout: int = 120
) -> List:
    result, thread_response = [], queue.Queue()
    total = query.distinct(ML.mortgage_id).count()
    if not total:
        raise NoContent()

    total_pages = ceil(total / per_page)

    with ThreadPoolExecutor(max_workers=5) as executor:
        for page in range(1, total_pages + 1):
            executor.submit(
                thread_download_mortgage_file,
                query,
                page,
                per_page,
                campaign,
                thread_response,
            )

    for _ in range(1, total_pages + 1):
        val = thread_response.get(timeout=timeout)
        if isinstance(val, list):
            result.extend(val)
        else:
            raise InternalError()

    return result


