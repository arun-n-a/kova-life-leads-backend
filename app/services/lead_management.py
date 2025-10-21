from typing import (List, Dict, Tuple)

from flask import g
from sqlalchemy import (func, and_)

from app.models import (
     MailingAssignee as MA,
     MailingLead as ML,
     MailingResponse as MR,
     Agent
)
from app.services.custom_errors import *


def get_agents_leads_count(agent_id: int = None, purchased_user_id: str = None) -> Dict:
    if agent_id:
        agent_ids = [agent_id]
        if g.user['role_id'] != 1:
            raise Forbidden()
    else:
        agent_ids = g.user['mailing_agent_ids']
    result = (
        MA.query
        .outerjoin(MR, MR.mortgage_id == MA.mortgage_id)
        .filter(
            MA.agent_id.in_(agent_ids),
            MA.purchased_user_id == purchased_user_id
            )
        .with_entities(
            func.count(MR.mortgage_id).filter(
                and_(
                    MR.completed == True,
                    MA.lead_status != 7 
                )
            ).label("completed"),
            func.count(func.distinct(MA.mortgage_id)).filter(
                and_(
                    MR.completed == False,
                    MA.lead_status != 7  
                )
            ).label("incomplete"),    
            func.count(func.distinct(MA.mortgage_id)).filter(
                    and_(
                        MA.lead_status == 7
                    )
                ).label("sold"),
            func.count(func.distinct(MA.mortgage_id)).filter(
                    and_(
                        MR.mortgage_id == None
                    )
                ).label("mailed")
            )
        .first()
        )
    return result._asdict()


