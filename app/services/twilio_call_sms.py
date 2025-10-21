"""API Endpoints related to IVR calls and SMS."""
import json
from datetime import datetime
from typing import Dict

from sqlalchemy import or_
from app.services.crud import CRUD
from app.services.custom_errors import *
from app.models import MailingLead as ML, MailingResponse as MR
from app.services.utils import (
    convert_utc_to_timezone
    )
from config import Config_is
from constants import LEAD_CATEGORY
from app import tasks

def loan_date_format_with_suffix(date_obj: datetime.date) -> str:
    if not date_obj:
        return ''
    day = date_obj.day
    if 11 <= day <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return date_obj.strftime(f"%B {day}{suffix} %Y")

def twilio_mortgage_id_validation(data: Dict) -> Dict:
    try:
        data["mortgage_id"] = data["mortgage_id"].replace("#", "").replace("*", "")
        leads = ML.query.outerjoin(MR, MR.mortgage_id == ML.mortgage_id)
        if len(data['mortgage_id']) == 5:
            leads = leads.filter(ML.temp_mortgage_id == data["mortgage_id"])
        else:
            leads = leads.filter(ML.mortgage_id == data["mortgage_id"])
    except Exception as e:
        leads = None
        print(e)
    leads = leads.order_by(ML.created_at.desc()).with_entities(ML, MR).first()
    if not leads:
        # return {
        #     "name": "",
        #     "bank": "",
        #     "date": "",
        #     "url": "",
        #     "status": "invalid",
        #     "message": "Failed",
        #     "state": "",
        # }
        return {}
    if leads[1] and leads[1].temp_data and leads[1].call_sid:
        get_twilio_status_call_back({'CallSid': leads[1].call_sid, 'CallStatus': 'completed'})
    try:
        data = json.dumps(data).replace("#", "").replace("*", "")
        data = json.loads(data)
    except Exception as e:
        print(e)
    data["timestamp"] = convert_utc_to_timezone(datetime.utcnow())
    updates = dict(
        call_sid=data['sid'], call_in_date_time=data["timestamp"], temp_data=data
    )
    if leads[-1]:
        CRUD.update(MR, {"id": leads[-1].id}, updates)
    else:
        CRUD.create(MR, {"mortgage_id": leads[0].mortgage_id, **updates})
    return dict(
        name=leads[0].full_name,
        mortgage_id=leads[0].mortgage_id,
        lender_name=leads[0].lender_name,
        loan_date=loan_date_format_with_suffix(leads[0].loan_date),
        # loan_amount=leads[0].loan_amount,
        source=LEAD_CATEGORY[1]['sources'][leads[0].source_id]['name'],
        url=f"{Config_is.FRONT_END_URL}/single-mortgage-public/{leads[0].mortgage_id}/{leads[0].uuid}",
        state=leads[0].state
    )


def temp_twilio_mortgage_id_validation(data: Dict) -> Dict:
    try:
        data["mortgage_id"] = data["mortgage_id"].replace("#", "").replace("*", "")
        leads = ML.query.outerjoin(MR, MR.mortgage_id == ML.mortgage_id)
        if len(data['mortgage_id']) == 5:
            leads = leads.filter(ML.temp_mortgage_id == data["mortgage_id"])
        else:
            leads = leads.filter(ML.mortgage_id == data["mortgage_id"])
    except Exception as e:
        leads = None
        print(e)
    # leads = leads.order_by(MR.created_at.desc()).with_entities(ML, MR).first()
    leads = leads.order_by(ML.created_at.desc()).with_entities(ML, MR).first()
    if not leads:
        # return {
        #     "name": "",
        #     "bank": "",
        #     "date": "",
        #     "url": "",
        #     "status": "invalid",
        #     "message": "Failed",
        #     "state": "",
        # }
        return {}
    if leads[1] and leads[1].temp_data and leads[1].call_sid:
        get_twilio_status_call_back({'CallSid': leads[1].call_sid, 'CallStatus': 'completed'})
    try:
        data = json.dumps(data).replace("#", "").replace("*", "")
        data = json.loads(data)
    except Exception as e:
        print(e)
    data["timestamp"] = convert_utc_to_timezone(datetime.utcnow())
    updates = dict(
        call_sid=data['sid'], call_in_date_time=data["timestamp"], temp_data=data
    )
    if leads[-1]:
        CRUD.update(MR, {"id": leads[-1].id}, updates)
    else:
        CRUD.create(MR, {"mortgage_id": leads[0].mortgage_id, **updates})
    return dict(
        name=leads[0].full_name,
        mortgage_id=leads[0].mortgage_id,
        lender_name=leads[0].lender_name,
        loan_date=loan_date_format_with_suffix(leads[0].loan_date),
        # loan_amount=leads[0].loan_amount,
        source=LEAD_CATEGORY[1]['sources'][leads[0].source_id]['name'],
        url=f"{Config_is.FRONT_END_URL}/single-mortgage-public/{leads[0].mortgage_id}/{leads[0].uuid}",
        state=leads[0].state
    )


def temp_twilio_mortgage_id_validation_for_file(data: Dict, file_id: int = None) -> Dict:
    try:
        data["mortgage_id"] = data["mortgage_id"].replace("#", "").replace("*", "")
        leads = ML.query.outerjoin(MR, MR.mortgage_id == ML.mortgage_id)
        leads = leads.filter(or_(ML.temp_mortgage_id == data["mortgage_id"], ML.mortgage_id == data["mortgage_id"]))
        if file_id:
            leads = leads.filter(ML.file_id == file_id)
    except Exception as e:
        leads = None
        print(e)
    # leads = leads.order_by(MR.created_at.desc()).with_entities(ML, MR).first()
    leads = leads.order_by(ML.created_at.desc()).with_entities(ML, MR).first()
    if not leads:
        return {}
    if leads[1] and leads[1].temp_data and leads[1].call_sid:
        get_twilio_status_call_back({'CallSid': leads[1].call_sid, 'CallStatus': 'completed'})
    try:
        data = json.dumps(data).replace("#", "").replace("*", "")
        data = json.loads(data)
    except Exception as e:
        print(e)
    data["timestamp"] = convert_utc_to_timezone(datetime.utcnow())
    updates = dict(
        call_sid=data['sid'], call_in_date_time=data["timestamp"], temp_data=data
    )
    if leads[-1]:
        CRUD.update(MR, {"id": leads[-1].id}, updates)
    else:
        CRUD.create(MR, {"mortgage_id": leads[0].mortgage_id, **updates})
    data = dict(
        name=leads[0].full_name,
        mortgage_id=leads[0].mortgage_id,
        lender_name=leads[0].lender_name,
        loan_date=loan_date_format_with_suffix(leads[0].loan_date),
        # loan_amount=leads[0].loan_amount,
        source=LEAD_CATEGORY[1]['sources'][leads[0].source_id]['name'],
        url=f"{Config_is.FRONT_END_URL}/single-mortgage-public/{leads[0].mortgage_id}/{leads[0].uuid}",
        state=leads[0].state
        )
    return data

def get_twilio_status_call_back(data: Dict) -> bool:
    print(f"get_twilio_status_call_back {data}")
    if data.get("CallStatus") != "completed" or not data.get("CallSid"):
        return False
    lead_is = (
        ML.query.join(MR, MR.mortgage_id == ML.mortgage_id)
        .filter(MR.call_sid == data.pop("CallSid"))
        .with_entities(ML, MR)
        .order_by(MR.modified_at.desc())
        .first()
    )
    print(f"lead_is {lead_is}")
    if not lead_is or not lead_is.MailingResponse.temp_data:
        print('no response')
        return False
    lead, response = lead_is
    temp_data = response.temp_data
    for i in ["coborrower", "health", "tobacco", "spouse"]:
        if temp_data.get(i) == "2":
            temp_data[i] = "0"
    response.ivr_logs = response.ivr_logs + [temp_data]
    print(f'LOg is {response.ivr_logs}')
    mortgage_info= dict(
        state=lead.state, city=lead.city, uuid=lead.uuid, 
        source_id=lead.source_id, full_name=lead.full_name, 
        zip=lead.zip, address=lead.address, 
        lender_name=lead.lender_name, 
        loan_amount=lead.loan_amount,
        mortgage_id=lead.mortgage_id
        )
    if not response.completed:
        if len(temp_data) > 2 and (
            all(temp_data.get(r) for r in ["age", "health", "number", "tobacco"])
            and any(temp_data.get(r) for r in ["spouse", "coborrower"])
        ):
            response.completed = True
    if response.completed:
        sub = f"🔥 New Completed Lead Alert -{lead.mortgage_id}! Contact Immediately! 🔥"
    else:
        sub = f"🔥 New Incomplete Lead Alert -{lead.mortgage_id}! Contact Immediately! 🔥"
    response.ivr_response = temp_data
    response.temp_data = {}
    # response.call_sid = ""
    CRUD.db_commit()
    # Email and SMS alert
    tasks.latest_ivr_response_alert_to_agents.delay(mortgage_info, sub, temp_data)
    return True


def twilio_call_response_incomplete(data: Dict) -> bool:
    try:
        data = json.dumps(data).replace("#", "").replace("*", "")
        data = json.loads(data)
    except Exception as e:
        print(e)
    print(f"twilio_call_response_incomplete {data}")
    if not data.get("mortgage_id"):
        print('no mortgage')
        return False
    data["timestamp"] = convert_utc_to_timezone(datetime.utcnow())
    for i in ["coborrower", "health", "tobacco", "spouse"]:
        if data.get(i) == "2":
            data[i] = "0"
    lead_is = (
        ML.query.outerjoin(MR, ML.mortgage_id == MR.mortgage_id)
        .filter(ML.mortgage_id == data.get("mortgage_id"))
        .with_entities(ML.mortgage_id, MR.id)
        .first()
    )
    print(f"lead is {lead_is}")
    if not lead_is:
        return False
    if lead_is.id:
        print(f"lead_is.id {lead_is.id}")
        CRUD.update(
            MR, {"id": lead_is.id}, {"temp_data": data, "call_sid": data['sid']}
        )
    else:
        CRUD.create(
            MR,
            {"mortgage_id": data["mortgage_id"]},
            {
                "temp_data": data,
                "call_sid": data['sid'],
                "timestamp": data["timestamp"],
            },
        )
    return True

