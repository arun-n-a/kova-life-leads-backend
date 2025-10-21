import random
import ssl
from datetime import datetime, timedelta
from typing import List, Dict

from flask import render_template
from celery import Celery
from celery.schedules import crontab
from twilio.rest import Client
from celery.signals import task_postrun, task_failure

from app import create_app, db, redis_obj
from app.models import (
    MailingAssignee as MA, 
    MailingResponse as MR,
    MailingLead as ML, 
    User, Agent
    )
from app.services.crud import CRUD
from app.services.sendgrid_email import SendgridEmailSending
from config import Config_is
from constants import (DISABLED_STATES, FLAGGED_IVR_RESULT)


app = create_app()
app.app_context().push()
app = Celery('tasks', broker=Config_is.REDIS_URL)


app.conf.broker_use_ssl = {
    'ssl_cert_reqs': ssl.CERT_NONE,
    'ssl_check_hostname': False
}

app.conf.beat_schedule = {
    # 'run-every-6-minute': {
    #     'task': 'app.tasks.clear_expired_reserved_leads',
    #     'schedule': timedelta(seconds=360)
    # },
    'run-every-2-minute': {
        'task': 'app.tasks.clear_latest_ivr_temp_data',
        'schedule': timedelta(seconds=120)
    },
}

app.conf.timezone = 'UTC'

@task_postrun.connect
def close_session(*args, **kwargs):
    """
    Signal handler to close the database session after each task.
    """
    db.session.remove()


@task_failure.connect
def log_task_failure(sender=None, task_id=None, exception=None, *args, **kwargs):
    print(f"Task {task_id} failed: {exception}")
    db.session.rollback()
    db.session.remove()

@app.task
def celery_twilio_sms(to: str, body: str, twilio_from_numbers: list = Config_is.TWILIO_SMS_NUMBERS) -> bool:
    # body = f'{body}\nIf you would no longer like to receive these messages REPLY STOP to unsubscribe.'
    print('started celery_twilio_sms')
    print(twilio_from_numbers)
    try:
        client = Client(Config_is.TWILIO_SID, Config_is.TWILIO_TOKEN)
        message_send = client.messages.create(
            body=body,
            from_=random.choice(twilio_from_numbers),
            to=to)
    except Exception as e:
        print('twilio exceptiomn')
        print(e)
    return True


@app.task
def latest_ivr_response_alert_to_agents(mortgage_info: Dict, subject: str, ivr_response: Dict) -> bool:
    print(mortgage_info, subject, ivr_response)
    lead_members_obj = (
        MA.query.join(Agent, Agent.id == MA.agent_id)
        .join(User, User.id == Agent.user_id)
        .filter(
            MA.mortgage_id == mortgage_info['mortgage_id'],
            User.is_active == True
            )
        .with_entities(
            User.email, User.phone, User.name.label('agent_name'), 
            MA.copied_from_agent_id, MA.moved, MA.purchased_user_id,
            User.id.label('user_id')
            )
        .order_by(MA.created_at.desc()).all()
        )
    mortgage_info |= dict(
            health=FLAGGED_IVR_RESULT.get(ivr_response.get('health'), ''), 
            tobacco=FLAGGED_IVR_RESULT.get(ivr_response.get('tobacco'), ''),
            call_in_time=(datetime.strptime(ivr_response['timestamp'], "%m-%d-%Y %H:%M:%S")).strftime('%m-%d-%Y %I:%M%p'),
            incoming_number=ivr_response.get('ani'), age=ivr_response.get('age', ''),
            coborrower=FLAGGED_IVR_RESULT.get(ivr_response.get('coborrower'), ''),
            callback_number=ivr_response.get('number', ''),
            url=f"{Config_is.FRONT_END_URL}/single-mortgage-public/{mortgage_info['mortgage_id']}/{mortgage_info['uuid']}"
            )
    # if source_id==3:
                #     data.update({'spouse': FLAGGED_IVR_RESULT.get(ivr_response.get('spouse'), '')})
    sms_body = f"{subject} {mortgage_info['mortgage_id']} {mortgage_info['call_in_time']}"
    if ivr_response.get('number'):
        sms_body = f"{sms_body} Callback: {ivr_response['number']}"
    if ivr_response.get('age'):
        sms_body = f"{sms_body} Age: {ivr_response['age']}"
    sms_body = f"{sms_body} {mortgage_info['url']}"
    for ld_mem in lead_members_obj:
        SendgridEmailSending([{'user_id': str(ld_mem.user_id), 'email': ld_mem.email}], subject, render_template("email_ivr_response.html", data=mortgage_info), 9).send_email()
        # celery_twilio_sms.delay(row.phone, body)
    return True


@app.task
def clear_latest_ivr_temp_data():
    from app.services.twilio_call_sms import get_twilio_status_call_back
    for mr in MR.query.filter(MR.call_in_date_time <= (datetime.utcnow()-timedelta(minutes=5))).with_entities(MR.call_sid, MR.temp_data).all():
        if mr.temp_data and mr.temp_data:
            get_twilio_status_call_back({"CallSid": mr.call_sid, 'CallStatus': 'completed'})
    return True

@app.task
def clear_expired_reserved_leads(shopping_cart_temp_ids: str):
    """
    Reserved leads in marketplace will be cleared after 17mins if its not assigned successfully
    """
    print(f"clear_expired_reserved_leads -> {shopping_cart_temp_ids}")
    ML.query.filter(ML.item_reserved_temp_by.in_(shopping_cart_temp_ids)).update(
        {'is_in_checkout': False, 
        'shopping_cart_temp_id': None, 
        'item_reserved_temp_by': None, 
        'modified_at': ML.modified_at
        })
    CRUD.db_commit()
    return True
