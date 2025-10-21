import json
from typing import (
    Dict, List, Tuple, Optional,
    Union
    )
from datetime import datetime

from flask import render_template, g
from sqlalchemy import func

from app.models import (
    InterestedUser as IU, 
    MailingAssignee as MA,
    MailingResponse as MR,
    User, Agent, 
    
    logout_user_from_all_devices
    )
from app.services.utils import email_format_validation
from app.services.sendgrid_email import SendgridEmailSending
from app.services.crud import CRUD
from app.services.utils import (
    discard_crucial_user_data,
    generate_short_code, 
    add_redis_ttl_data
    )
from app.services.stripe_service import StripeService
from app.services.custom_errors import *
from app import db, redis_obj
from config import Config_is
from constants import LEAD_CATEGORY
from app import tasks


def verify_registration_short_url(id_: str) -> str:
    data = redis_obj.get(f'sms_invitation_{id_}')
    if not data:
        raise BadRequest("This linked has expired")
    data = json.loads(data)
    token = redis_obj.get(data['token_key'])
    if not token or token not in data['url'].replace('$$$$$', '.'):
        raise BadRequest("This linked has expired")
    return data['url']


def sent_email_invitation(
        user_id: str, name: str, phone: str, 
        agency_name: str, auth_token: str, 
        to_email: Dict) -> bool:
    """
    Sent email invitation to new users with signup link
    """
    registration_url=(
            f"{Config_is.FRONT_END_REGISTRATION_URL}/{auth_token}?name="
            f"{name.replace(' ', '+')}&phone={phone}&agency_name={agency_name}"
        )
    invitation_html = render_template(
        "user_invitation.html",
        name=name,
        registration_url=registration_url
        )
    temp_id = generate_short_code()
    print(temp_id)
    add_redis_ttl_data(
        f'sms_invitation_{temp_id}', 
        Config_is.AUTH_TOKEN_EXPIRES, 
        json.dumps({"token_key": f"{user_id}_invitation", "url": registration_url})
        )
    print('redis added')
    response = SendgridEmailSending(
        [to_email], "KovaLifeLeads Application Invitation", 
        invitation_html, 1
        ).send_email()
    print('sendgrid email sent*****')
    print(f"You are invited to join KovaLifeLeads {Config_is.FRONT_END_REGISTRATION_SHORT_URL}/{temp_id}")
    tasks.celery_twilio_sms(
        to=phone, 
        body=f"You are invited to join KovaLifeLeads {Config_is.FRONT_END_REGISTRATION_SHORT_URL}/{temp_id}", 
        twilio_from_numbers=[Config_is.TWILIO_SMS_NUMBER_FOR_INVITATION]
        )
    
    if response:
        return True
    raise InternalError("The system encountered an issue while sending the email invitation. Please try resending the invitation after some time.")


def interested_user_invitation(data: Dict) -> bool:
    """
    Sent user info to the admin
    """
    data["email"] = email_format_validation(data["email"])
    html_template = render_template("interested_users.html", data=data)
    response = SendgridEmailSending(
        Config_is.INVITATION_EMAIL_TO, 
        f"Review Needed: New KovaLifeLeads User Submission {data['name']}", 
        html_template, 4
        ).send_email_without_logs()
    user_obj = IU.query.filter(IU.email == data['email']).first()
    if user_obj.is_active == True or (user_obj.is_acitve is False and user_obj.rejection_message == None):
        raise BadRequest()
    data['is_active'] = True
    CRUD.create_or_update(IU, {'email': data['email']}, {'email': data['email'], 'payload': data})
    if response:
        return True
    raise InternalError()


def paginated_intered_users(page: int, per_page: int) -> Tuple:
    user_objs = IU.query.order_by(IU.created_at.desc()).filter(IU.is_active == True).paginate(
        page=page, per_page=per_page, error_out=False
        )
    data = [{'id': user_obj.id, **user_obj.payload} for user_obj in user_objs.items]
    if data:
        return data, {
            "total": user_objs.total,
            "current_page": user_objs.page,
            "per_page": user_objs.per_page,
            "length": len(data),
        }
    raise NoContent()


def agent_exist_or_not(agents: List) -> bool:
    ids = [i["id"] for i in agents]
    if ids:
        existing = [ag_obj.id for ag_obj in Agent.query.with_entities(
            Agent.id).filter(Agent.id.in_(ids)).all()
            ]
        if existing:
            raise BadRequest(
                f"Agent id {', '.join(str(i) for i in existing)} already exists."
            )
    return True


def add_agents(user_id: str, agents: Dict) -> bool:
    for key in ['human', 'auto']:
        for agent in agents.get(key, []):
            u = Agent(user_id=user_id, **agent)
            db.session.add(u)
    return True


def adding_new_user(data: Dict, agents: Dict) -> str:
    """
    Adding new user and sent email invitation
    """
    data["email"] = email_format_validation(data["email"])
    agent_exist_or_not(agents.get("human", []))
    user_obj = User.query.filter_by(email=data["email"]).first()
    if not user_obj:
        user_obj = User(**data)
        db.session.add(user_obj)
        CRUD.transaction_flush()
    elif user_obj.registered:
        raise Conflict("This email address has already been registered.")
    else:
        raise Conflict(f"This email address already exists but not registered yet")
    add_agents(user_obj.id, agents)
    token = user_obj.generate_auth_token('invitation', Config_is.AUTH_TOKEN_EXPIRES)  # token expires after 7 days
    sent_email_invitation(
        user_obj.id, user_obj.name, user_obj.phone, user_obj.agency_name, token.replace('.', '$$$$$'), 
        {'user_id': user_obj.id, 'email': user_obj.email}
        )
    for column, value in {"is_active": True, "registered": False, "is_invited": True, 'invited_at': datetime.utcnow(), **data}.items():
        setattr(user_obj, column, value)
    if not user_obj.stripe_customer_id:
        user_obj.stripe_customer_id = StripeService().create_customer(user_obj)
    CRUD.db_commit()
    return token


def edit_user_details(
        user_id: str, agents: Dict, remove_agents: List, 
        edit_agents: List, data: Dict) -> bool:
    if g.user["role_id"] != 1:
        data = discard_crucial_user_data(['role_id', 'email'])
        if g.user["id"] != user_id:
            raise Forbidden()
    else:
        if remove_agents:
            Agent.query.filter(Agent.id.in_(remove_agents)).delete()
            CRUD.db_commit()
        if edit_agents:
            for ag in edit_agents:
                Agent.query.filter_by(id=ag.pop("id")).update(ag)
            CRUD.db_commit()
        if agents.get("human"):
            agent_exist_or_not(agents.get("human", []))
        add_agents(user_id, agents)
    CRUD.update(User, {"id": user_id}, data)
    user_obj = User.query.filter_by(id=user_id).with_entities(User.registered).first()
    if user_obj.registered:
        logout_user_from_all_devices(user_id)
    return True


def change_user_active_inactive_status(
        user_id: str, is_active: bool) -> bool:
    if g.user["id"] == user_id:
        raise Forbidden()
    user_obj = User.query.filter_by(id=user_id).first()
    if is_active:
        user_obj.is_active = True
        deactivated_at = None
        data = dict(
            status_text='reactivated', 
            login_url=Config_is.FRONT_END_URL
            )
    else:
        user_obj.is_active = False
        data = dict(status_text='deactivated')
        user_obj.deactivated_at = datetime.utcnow()
        logout_user_from_all_devices(user_id)
    data |= dict(
        name=user_obj.name, 
        is_active=user_obj.is_active
        )
    alert_template = render_template(
        "user_active_inactive_alert.html",
        data=data
        )
    SendgridEmailSending(
        [{'user_id': user_id, 'email': user_obj.email}], 
        "KovaLifeLeads Application Account status", 
        alert_template, 3
        ).send_email()
    return True


def list_users_with_filter(page: int, per_page: int, query_filters: Dict) -> Tuple:
    users_obj = User.query
    if query_filters.get('name'):
        users_obj =  users_obj.filter(User.name.ilike(f"%{query_filters.pop('name')}%"))
    for k, v in query_filters.items():
         users_obj =  users_obj.filter(getattr(User, k) == v)
    users_obj = users_obj.order_by(User.modified_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    data = [user_obj.to_dict() for user_obj in users_obj.items]
    if data:
        return data, {
            "total": users_obj.total,
            "current_page": users_obj.page,
            "per_page": users_obj.per_page,
            "length": len(data),
        }

    raise NoContent()


def list_agents_with_filter(page: int, per_page: int, category_id: int = None, 
                            agent_id_or_name: Union[int, str, None] = None, 
                            status: str = None
                            ) -> Tuple:
    agents_obj = Agent.query.join(
        User, User.id == Agent.user_id
        ).with_entities(
            Agent.id, Agent.category, Agent.source, 
            Agent.user_id, User.email, User.name, 
            User.phone, User.is_active, User.states_chosen
            )
    if category_id:
        agents_obj = agents_obj.filter(Agent.category == category_id)
    if status is not None:
        agents_obj = agents_obj.filter(User.is_active == status)
    if agent_id_or_name:
        if agent_id_or_name.strip().isdigit():
            agents_obj = agents_obj.filter(
                Agent.id == agent_id_or_name,
            ).first()
            if agents_obj:
                return [
                    agents_obj._asdict()
                ], {
                    "total": 1,
                    "current_page": 1,
                    "per_page": 1,
                    "length": 1
                    }
            raise NoContent()
        else:
            agents_obj = agents_obj.filter(
                User.name.ilike(f"%{agent_id_or_name}%")
                )
    agents_obj = agents_obj.order_by(User.modified_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    result = [agent_obj._asdict() for agent_obj in agents_obj.items]
    if result:
        return result, {
            "total": agents_obj.total,
            "current_page": agents_obj.page,
            "per_page": agents_obj.per_page,
            "length": len(result),
        }
    raise NoContent()


def list_agents_of_category_source(
        category: int, source_id: int, page: int, 
        per_page: int) -> Tuple:
    agent_objs = (
        Agent.query.join(User, User.id == Agent.user_id)
        .with_entities(Agent.id, User.name)
        .filter_by(source=source_id, category=category)
        .order_by(Agent.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    result = [u._asdict() for u in agent_objs.items]
    if result:
        return result, {
            "total": agent_objs.total,
            "current_page": agent_objs.page,
            "per_page": agent_objs.per_page,
            "length": len(result),
        }
    raise NoContent()


def list_agents_for_assignment(
        data: Dict, category_id: int, 
        page: int, per_page: int, 
        source_id: Optional[int] = None) -> Tuple:
    """
    List agents who is engaged in this specific category with optional source filter or agent filter
    """
    db_query = Agent.query.join(User, User.id == Agent.user_id).filter(
        Agent.category == category_id)
    if source_id:
        db_query = db_query.filter(Agent.source == source_id)
    if data.get("name"):
        db_query = db_query.filter(User.name.ilike(f"%{data['name']}%"))
    elif data.get("agent_id"):
        db_query = db_query.filter(Agent.id == data["agent_id"])
    db_query = db_query.with_entities(
        Agent.id.label("agent_id"),
        Agent.category,
        Agent.source,
        User.name,
        User.id.label("user_id"),
    ).paginate(page=page, per_page=per_page, error_out=False)
    result = [u._asdict() for u in db_query.items]
    if result:
        return result, {
            "total": db_query.total,
            "current_page": page,
            "per_page": per_page,
            "length": len(result),
        }
    raise NoContent()


def handle_user_intent_request(id_: str, action: str, rejection_message: str) -> bool:
    """
    Handle user request approval or rejection.
    """
    interested_user = IU.query.filter_by(id=id_, is_active=True).first()
    if not interested_user:
        raise NoContent("User request not found")
    interested_user.is_active = False
    if action == "reject":
        if rejection_message:
            rejection_template = render_template(
                "user_request_rejection.html",
                name=interested_user.payload.get("name"),
                message=rejection_message
            )
            SendgridEmailSending(
                to_emails=[interested_user.payload.get("email")],
                html_content=rejection_template,
                subject="KovaLifeLeads Application Status Update"
                ).send_email_without_logs()
        else:
            interested_user.message = "No reason"
        CRUD.db_commit()
        return True

    user_data = interested_user.payload | {'user_intents': True}
    agents = {
            'auto': [
        {
            'id': None,
            'source': source,
            'category': category
        }
            for category, val in LEAD_CATEGORY.items() for source in val['sources'].keys()
            ]}
    adding_new_user(user_data, agents)
    CRUD.db_commit()
    return True


def getting_user_active_inactive_count() -> Dict:
    """
    Returns the count of users grouped by is_active (True/False)
    """
    active_group = User.query.filter(User.registered == True).with_entities(
        User.is_active,
        func.count(User.id).label('count')
        ).group_by(User.is_active)
    result = dict()
    for is_active, count in active_group.all():
        if is_active:
            result["active"] = count
        else:
            result["inactive"] = count
    return result


def getting_agents_count() -> Dict:
    """
    In agent management page agents active and inactive counts required
    """
    result  = dict()
    agents_obj = (
        Agent.query
        .join(User, User.id == Agent.user_id)
        .filter(User.registered == True).with_entities(
            User.is_active,
            func.count(Agent.id).label('count'), 
            )
        ).group_by(User.is_active)
    for agent_obj in agents_obj.all():
        if agent_obj.is_active:
            result["active"] = agent_obj.count
        else:
            result["inactive"] = agent_obj.count
    
    return result


def admin_getting_total_leads_and_sold_count() -> Dict:
    query_objs = (
        MA.query
        .join(MR, MR.mortgage_id == MA.mortgage_id)
        .with_entities(
            func.count(func.distinct(MR.mortgage_id)).filter(MA.lead_status == 7).label("sold"),
            func.count(func.distinct(MR.mortgage_id)).filter(
                MR.completed == True,
                MA.lead_status != 7
                ).label("completed"),
            func.count(MR.mortgage_id).filter(
                MR.completed == False,
                MA.lead_status == 7).label("incomplete")
                )
            ).first()
    return query_objs._asdict()