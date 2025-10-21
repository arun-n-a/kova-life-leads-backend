from typing import List, Dict, Union, Optional, Tuple

from flask import g
from sqlalchemy import func, and_
from app.models import (
    MailingLead as ML,
    MailingAssignee as MA,
    StripeCustomerSubscription as SCS,
    MailingResponse as MR
)
from app.services.custom_errors import *


def get_statewise_territory_leads_count(
        category: int, page: int, per_page: int, 
        states: List) -> Tuple:
    if category == 1:
        leads_data = (
            ML.query
            .outerjoin(MR, ML.mortgage_id == MR.mortgage_id)
            .join(MA, ML.mortgage_id == MA.mortgage_id)
            .filter(
                ML.state.in_(states),
                MA.agent_id.in_(g.user['mailing_agent_ids'])
                )
            .with_entities(
                ML.state,
                func.count(MA.mortgage_id).filter(
                    and_(
                        MR.completed== True,
                        MA.lead_status != 7
                    )
                ).label("completed"),
                func.count(MA.mortgage_id).filter(
                    and_(
                        MR.completed== False,
                        MA.lead_status != 7
                        )
                ).label("incomplete"),
                func.count(MA.mortgage_id).filter(
                        MA.lead_status == 7
                    ).label("sold")
                )
            .group_by(ML.state)
            .paginate(
                page=page, per_page=per_page, error_out=False
                )
        )
        result = [row._asdict() for row in leads_data.items]
        return result, {
            'current_page': leads_data.page,
            'per_page': leads_data.per_page,
            'total': leads_data.total,
            'length': len(result)
        }


def listing_assigned_leads_states(category: int) -> Dict:
    if category == 1:
        data = [
            ml.state  for ml in ML.query.join(
                MA, MA.mortgage_id == ML.mortgage_id
                ).filter(
                    MA.agent_id.in_(g.user['mailing_agent_ids'])
                    ).with_entities(func.distinct(ML.state).label('state')).all()
            ]
    if data:
        return {'states': data}
    raise NoContent()


def getting_total_and_sold_count(category: int, states: List) -> Dict:
    if category:
        query_obj = (
            ML.query
            .join(MA, MA.mortgage_id == ML.mortgage_id)
            .join(MR, MR.mortgage_id == ML.mortgage_id)
            .filter(
                ML.state.in_(states),
                MA.agent_id.in_(g.user['mailing_agent_ids'])
                )
            .with_entities(
                func.count(MA.mortgage_id).label("total"),
                (
                    func.count(MA.mortgage_id).filter(
                        MA.lead_status == 7).label("sold")
                )
            )
            ).first()
        
    data =  query_obj._asdict()
    print('arun')
    print(data)
    if data:
        return data
    raise NoContent()



def get_states_chosen_for_active_subscription(category: int) -> Dict:
    if category:
        sub = (
            SCS.query
            .filter(
                SCS.user_id == g.user["id"],
                SCS.status == "active",
                SCS.is_active.is_(True)
            )
            .with_entities(SCS.states_chosen)
            .order_by(SCS.modified_at.desc())
            .first()
        )
    if sub :
        return {'states': sub.states_chosen}
    raise NoContent()
