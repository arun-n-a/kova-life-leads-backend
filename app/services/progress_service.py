from app.models import MailingLead as ML, MailingAssignee as MA, MailingResponse as MR
from app.services.custom_errors import NoContent
from flask import g
from typing import Dict
from sqlalchemy import (func, and_)
from constants import (
    EXCLUDED_STATUS_FILTER_FROM_SALE
)

def get_agent_progress(query_filters: Dict) -> Dict:
    query = (
        MA.query
        .outerjoin(MR, MR.mortgage_id == MA.mortgage_id)
        .filter(MA.agent_id.in_(g.user["mailing_agent_ids"])))
    if query_filters.get("campaign"):
        query = query.filter(MA.campaign_name == query_filters["campaign"])
    result = query.with_entities(
        func.count(MR.mortgage_id).label("total"),
        func.count(MR.mortgage_id).filter(
            and_(
                MR.completed.is_(True),
                ~MA.lead_status.in_(EXCLUDED_STATUS_FILTER_FROM_SALE))).label("completed"),
        func.count(MR.mortgage_id).filter(
            and_(
                MR.completed.is_(False),
                ~MA.lead_status.in_(EXCLUDED_STATUS_FILTER_FROM_SALE)
            )
        ).label("incomplete"),
        func.count(MR.mortgage_id).filter(
            MA.lead_status == 7).label("sold")
    ).first()
    return {
        "total": result.total,
        "completed": result.completed,
        "incomplete": result.incomplete,
        "sold": result.sold,
        "suppressed": result.suppressed
    }


