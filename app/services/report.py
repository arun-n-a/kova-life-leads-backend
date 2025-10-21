from typing import (
    List, Dict, Union, 
    Optional, Tuple
    )
from datetime import datetime, timedelta

from flask import g
from sqlalchemy import func
from sqlalchemy.sql.expression import over

from app.models import (
    MailingAssignee as MA,
    MailingLead as ML,
    MailingResponse as MR,
    MailingLeadMemberStatusLog as MLMSL
)
from app.services.custom_errors import *
from app import db

class ReportAndAnalytics:
    def __init__(self, start_date: str, end_date: str):
        self.start_date = datetime.strptime(start_date, "%m-%d-%Y")
        self.end_date = datetime.strptime(end_date, "%m-%d-%Y") 
    
    def get_state_wise_call_sold_count(self) -> List[Dict]:
        query_objs = (
            ML.query
            .join(MA, MA.mortgage_id == ML.mortgage_id)
            .filter(
                MA.sold_date >= self.start_date, 
                MA.sold_date <= self.end_date,
                MA.lead_status == 7
                )
            .with_entities(
                func.count(func.distinct(MA.mortgage_id)).label('sold'),
                ML.state
                )
            .group_by(ML.state)
            )
        data = [query_obj._asdict() for query_obj in query_objs.all()]
        if data:
            return data
        raise NoContent()

    def get_lead_status_based_count(self) -> List[Dict]:
        subq = (
            db.session
            .query(
                MA.mortgage_id,
                MA.lead_status,
                MA.lead_status_changed_at,
                over(
                    func.row_number(),
                    partition_by=MA.mortgage_id,
                    order_by=MA.lead_status_changed_at.desc()
                ).label("rn")
            )
            .filter(MA.lead_status_changed_at.between(self.start_date, self.end_date))
        .subquery()
        )

        result = (
            db.session.query(
            subq.c.lead_status,
            func.count(func.distinct(subq.c.mortgage_id)).label('count')
            )
            .filter(subq.c.rn == 1)
            .group_by(subq.c.lead_status)
        )
        data = [res._asdict() for res in result.all()]
        if data:
            return data
        raise NoContent()

    def getting_total_leads_and_sold_count(self) -> Dict:
        leads_query = (
            MA.query
            .join(MR, MR.mortgage_id == MA.mortgage_id)
            .filter(
                MR.call_in_date_time >= self.start_date, 
                MR.call_in_date_time <= self.end_date
                )
            .with_entities(
                 func.count(MR.mortgage_id).filter(MA.lead_status == 7).label("sold"),
                 func.count(MR.mortgage_id).filter(
                      MR.completed == True,
                      MA.lead_status != 7
                      ).label("completed"),
                 func.count(MR.mortgage_id).filter(
                      MR.completed == False,
                      MA.lead_status == 7).label("incomplete")
                 )
            ).first()
        data = leads_query._asdict()
        if data:
             return data
        raise NoContent()