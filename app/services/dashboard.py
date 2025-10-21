from datetime import datetime, timedelta
from typing import (List, Dict, Tuple)
from concurrent.futures import ThreadPoolExecutor
import queue
from dateutil.relativedelta import relativedelta
from collections import defaultdict


from flask import g
from sqlalchemy import func, and_, case, or_
from app.models import (
     MailingAssignee as MA,
     MailingLead as ML,
     MailingResponse as MR,
     User,
     MarketplaceOrderSummary as MOS,
     SubscriptionOrderSummary as SOS,
     UploadedFile as UF, 
     StripeCustomerSubscription as SCS
)
from app.services.utils import (
    date_time_obj_to_str, get_current_date_time)
from app import  app,db
from config import Config_is
from app.services.custom_errors import *


def get_dashboard_recent_leads(limit: int) -> List[Dict]:
        lead_query = (
                ML.query
                .join(MR, MR.mortgage_id == ML.mortgage_id)
                .join(MA, MA.mortgage_id == ML.mortgage_id)
                .filter(
                        MA.agent_id.in_(g.user['mailing_agent_ids'])
                        )
                .with_entities(
                        ML.mortgage_id, ML.full_name, ML.first_name, 
                        ML.last_name, ML.state, ML.zip, ML.city, 
                        MR.call_in_date_time, MA.lead_status,
                        MR.ivr_response
                        )
                .order_by(MR.call_in_date_time.desc()).limit(limit)
            )
        result = []
        for ld in lead_query:
            ld = ld._asdict()
            ld['call_in_date_time'] = date_time_obj_to_str(ld['call_in_date_time'])
            result.append(ld)
        if result:
            return result
        raise NoContent()
  

def get_leads_sold_complete_incomplete_count(category: int) -> List[Dict]:
    if category == 1:
        leads_query = (
             ML.query
             .join(MR, MR.mortgage_id == ML.mortgage_id)
             .join(MA, MA.mortgage_id == ML.mortgage_id)
             .filter(
                  MA.agent_id.in_(g.user['mailing_agent_ids'])
                  )
            .with_entities(
                 func.count(MR.mortgage_id).filter(MA.lead_status == 7).label("sold"),
                 func.count(MR.mortgage_id).filter(
                      MR.completed == True,
                      MA.lead_status != 7
                      ).label("completed"),
                 func.count(MR.mortgage_id).filter(
                      MR.completed == False,
                      MA.lead_status != 7).label("incomplete")
                 )
            ).first()
    data = leads_query._asdict()
    if data:
         return data
    raise NoContent()


def get_dashboard_count(time_zone: str):
    current_time = get_current_date_time(datetime.utcnow(), time_zone)
    first_of_this_month = current_time.replace(day=1)
    last_month_start = (first_of_this_month - timedelta(days=1)).replace(day=1)
    if current_time.month == 12:
          first_of_next_month = current_time.replace(year=current_time.year + 1, month=1, day=1)
    else:
          first_of_next_month = current_time.replace(month=current_time.month + 1, day=1)
    dashboard_count = {}
    mr_obj = MR.query.join(MA, MR.mortgage_id == MA.mortgage_id).with_entities(
          func.count(func.distinct(case((and_(MR.call_in_date_time >= last_month_start, MR.call_in_date_time < first_of_this_month,
                MA.lead_status != 7), MR.mortgage_id), else_= None))).label("last_month_total_leads"),
          func.count(func.distinct(case((and_(MA.sold_date >= last_month_start, MA.sold_date < first_of_this_month,
               MA.lead_status == 7), MR.mortgage_id),else_=None))).label("last_month_sold"),
          func.count(func.distinct(case((and_(MR.call_in_date_time >= first_of_this_month, MR.call_in_date_time < first_of_next_month,
                MA.lead_status != 7), MR.mortgage_id), else_= None))).label("this_month_total_leads"),
          func.count(func.distinct(case((and_(MA.sold_date >= first_of_this_month, MA.sold_date < first_of_next_month,
               MA.lead_status == 7), MR.mortgage_id), else_=None))).label("this_month_sold")).first()
    dashboard_count.update(mr_obj._asdict())
    user_obj = User.query.with_entities(
          func.sum(case((and_(User.is_active == True, User.registered == True, User.registered_at >= last_month_start,
                User.registered_at < first_of_this_month), 1), else_= 0)).label("last_month_users"),
          func.sum(case((and_(User.is_active == True, User.registered == True, User.registered_at >= first_of_this_month,
                User.registered_at < first_of_next_month), 1), else_= 0)).label("this_month_users")).first()
    dashboard_count.update(user_obj._asdict())
    if current_time.weekday() == Config_is.RENEWAL_DAY_OF_WEEK:
        sos_end_date = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        days_to_skip = 1  # exclude today, if today is wednesday
        days_diff = (first_of_next_month.date() - current_time.date()).days
        remaining_wednesdays = 0
        for i in range(days_to_skip, days_diff):
            day = current_time.date() + timedelta(days=i)
            if day.weekday() == Config_is.RENEWAL_DAY_OF_WEEK:
                remaining_wednesdays += 1

        active_subscriptions_count = SCS.query.filter(SCS.status == 'active').count()
        estimated_future_revenue = remaining_wednesdays * active_subscriptions_count
    else:
        sos_end_date = first_of_next_month
        estimated_future_revenue = 0
    revenue_obj = SOS.query.join(SCS, SOS.subscription_db_id == SCS.id).with_entities(
          func.sum(case((and_(SOS.created_at >= last_month_start, SOS.created_at < first_of_this_month, SOS.payment_status == 'paid',
               SCS.status == 'active'), SOS.amount_received), else_=0)).label("last_month_revenue"),
          func.sum(case((and_(SOS.created_at >= first_of_this_month, SOS.created_at < sos_end_date, SOS.payment_status == 'paid',
               SCS.status == 'active'), SOS.amount_received), else_=0)).label("this_month_revenue")).first()
    if revenue_obj:
        revenue_dict = revenue_obj._asdict()
        dashboard_count["this_month_revenue"] = revenue_dict.get("this_month_revenue") + estimated_future_revenue
    marketplace_obj = MOS.query.with_entities(
          func.count(case((and_(MOS.created_at >= last_month_start, MOS.created_at < first_of_this_month, 
               MOS.payment_status == 'succeeded'), 1), else_=0)).label("last_month_marketplace_sales"),
          func.count(case((and_(MOS.created_at >= first_of_this_month, MOS.created_at < first_of_next_month, 
               MOS.payment_status == 'succeeded'), 1), else_=0)).label("this_month_marketplace_sales")).first()
    dashboard_count.update(marketplace_obj._asdict())
    return dashboard_count


def get_recent_user(q: queue.Queue):
    try:
        with app.app_context():
            with db.session.begin():
                data = (
                    db.session.query(User)
                    .filter(User.registered == True)
                    .with_entities(User.id, User.registered_at, User.name)
                    .order_by(User.registered_at.desc())
                    .first()
                )
                q.put({"latest_user": data._asdict()})
    except Exception as e:
        db.session.rollback()
        q.put(("latest_user", str(e)))

def get_latest_purchase(q: queue.Queue):
    try:
        with app.app_context():
            with db.session.begin():
                data = (
                    db.session.query(MOS)
                    .join(User, MOS.user_id == User.id)
                    .with_entities(MOS.amount_received, MOS.created_at, MOS.id, User.name) 
                    .filter(MOS.payment_status == 'succeeded')
                    .order_by(MOS.created_at.desc())
                    .first()
                )
                q.put({"latest_purchase": data._asdict()})
    except Exception as e:
        db.session.rollback()
        q.put(("latest_purchase", str(e)))


def get_latest_territory(q: queue.Queue):
    try:
        with app.app_context():
            with db.session.begin():
                data = (
                    db.session.query(SOS)
                    .join(User, SOS.user_id == User.id)
                    .with_entities(SOS.description, SOS.id, User.name, SOS.states_chosen)
                    .order_by(SOS.created_at.desc())
                    .first()
                )
                q.put({"latest_territory": data._asdict()})
    except Exception as e:
        db.session.rollback()
        q.put(("latest_territory", str(e)))
        
def get_latest_upload(q: queue.Queue):
    try:
        with app.app_context():
            with db.session.begin():
                data = (
                    db.session.query(UF)
                    .with_entities(UF.name, UF.id, UF.total_records, UF.created_at)
                    .order_by(UF.created_at.desc())
                    .first()
                )
                q.put({"latest_upload": data._asdict()})
    except Exception as e:
        db.session.rollback()
        q.put(("latest_upload", str(e)))

def get_recent_activity_overview() -> Dict:
    result = {}
    thread_response = queue.Queue()

    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.submit(get_recent_user, thread_response)
        executor.submit(get_latest_purchase, thread_response)
        executor.submit(get_latest_territory, thread_response)
        executor.submit(get_latest_upload, thread_response)

    for _ in range(4):
        data = thread_response.get(timeout=7)
        result.update(data)

    return result


def mr_count(q: queue.Queue, params):
    try:
        with app.app_context():
            with db.session.begin():
                result = MR.query.join(MA, MR.mortgage_id == MA.mortgage_id).with_entities(
                    func.count(func.distinct(case((and_(MR.call_in_date_time >= params["last_month_start"], MR.call_in_date_time < params["first_of_this_month"],
                        MA.lead_status != 7), MR.mortgage_id), else_= None))).label("last_month_total_leads"),
                    func.count(func.distinct(case((and_(MA.sold_date >= params["last_month_start"], MA.sold_date < params["first_of_this_month"],
                        MA.lead_status == 7), MR.mortgage_id),else_=None))).label("last_month_sold"),
                    func.count(func.distinct(case((and_(MR.call_in_date_time >= params["first_of_this_month"], MR.call_in_date_time < params["first_of_next_month"],
                        MA.lead_status != 7), MR.mortgage_id), else_= None))).label("this_month_total_leads"),
                    func.count(func.distinct(case((and_(MA.sold_date >= params["first_of_this_month"], MA.sold_date < params["first_of_next_month"],
                        MA.lead_status == 7), MR.mortgage_id), else_=None))).label("this_month_sold")).first()
                q.put({"mr_data": result._asdict()})
    except Exception as e:
        db.session.rollback()
        q.put({"mr_data": f"Error: {str(e)}"})


def user_count(q: queue.Queue, params):
    try:
        with app.app_context():
            with db.session.begin():
                result = User.query.with_entities(
                    func.sum(case((and_(User.is_active == True, User.registered == True, User.registered_at >= params["last_month_start"],
                        User.registered_at < params["first_of_this_month"]), 1), else_= 0)).label("last_month_users"),
                    func.sum(case((and_(User.is_active == True, User.registered == True, User.registered_at >= params["first_of_this_month"],
                        User.registered_at < params["first_of_next_month"]), 1), else_= 0)).label("this_month_users")).first()
                q.put({"user_data": result._asdict()})
    except Exception as e:
        db.session.rollback()
        q.put({"user_data": f"Error: {str(e)}"})


def total_revenue(q: queue.Queue, params):
    try:
        with app.app_context():
            with db.session.begin():
                if params["current_time"].weekday() == Config_is.RENEWAL_DAY_OF_WEEK:
                    sos_end_date = params["current_time"].replace(hour=0, minute=0, second=0, microsecond=0)
                    days_to_skip = 1
                    days_diff = (params["first_of_next_month"].date() - params["current_time"].date()).days
                    remaining_wednesdays = 0
                    for i in range(days_to_skip, days_diff):
                        day = params["current_time"].date() + timedelta(days=i)
                        if day.weekday() == Config_is.RENEWAL_DAY_OF_WEEK:
                            remaining_wednesdays += 1
                    active_subscriptions_count = SCS.query.filter(SCS.status == 'active').count()
                    estimated_future_revenue = remaining_wednesdays * active_subscriptions_count
                else:
                    sos_end_date = params["first_of_next_month"]
                    estimated_future_revenue = 0

                result = SOS.query.join(SCS, SOS.subscription_db_id == SCS.id).with_entities(
                    func.sum(case((and_(SOS.created_at >= params["last_month_start"], SOS.created_at < params["first_of_this_month"], SOS.payment_status == 'paid',
                        SCS.status == 'active'), SOS.amount_received), else_=0)).label("last_month_revenue"),
                    func.sum(case((and_(SOS.created_at >= params["first_of_this_month"], SOS.created_at < sos_end_date, SOS.payment_status == 'paid',
                        SCS.status == 'active'), SOS.amount_received), else_=0)).label("this_month_revenue")).first()
                revenue_dict = result._asdict() if result else {}
                revenue_dict["this_month_revenue"] = revenue_dict.get("this_month_revenue", 0) + estimated_future_revenue
                q.put({"revenue_data": revenue_dict})
    except Exception as e:
        db.session.rollback()
        q.put({"revenue_data": f"Error: {str(e)}"})


def marketplace_sales(q: queue.Queue, params):
    try:
        with app.app_context():
            with db.session.begin():
                result = MOS.query.with_entities(
                    func.count(case((and_(MOS.created_at >= params["last_month_start"], MOS.created_at < params["first_of_this_month"], 
                        MOS.payment_status == 'succeeded'), 1), else_=0)).label("last_month_marketplace_sales"),
                    func.count(case((and_(MOS.created_at >= params["first_of_this_month"], MOS.created_at < params["first_of_next_month"], 
                        MOS.payment_status == 'succeeded'), 1), else_=0)).label("this_month_marketplace_sales")).first()
                q.put({"marketplace_data": result._asdict()})
    except Exception as e:
        db.session.rollback()
        q.put({"marketplace_data": f"Error: {str(e)}"})


def dashboard_count(time_zone: str) -> Dict:
    current_time = get_current_date_time(datetime.utcnow(), time_zone)
    first_of_this_month = current_time.replace(day=1)
    last_month_start = (first_of_this_month - timedelta(days=1)).replace(day=1)
    if current_time.month == 12:
        first_of_next_month = current_time.replace(year=current_time.year + 1, month=1, day=1)
    else:
        first_of_next_month = current_time.replace(month=current_time.month + 1, day=1)

    params = {
        "current_time": current_time,
        "last_month_start": last_month_start,
        "first_of_this_month": first_of_this_month,
        "first_of_next_month": first_of_next_month
    }

    q = queue.Queue()
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.submit(mr_count, q, params)
        executor.submit(user_count, q, params)
        executor.submit(total_revenue, q, params)
        executor.submit(marketplace_sales, q, params)

    dashboard_count = {}
    for _ in range(4):
        data = q.get(timeout=7)
        dashboard_count.update(data)

    return dashboard_count


def get_dashboard_lead_flow(time_zone: str):
    end_date = get_current_date_time(datetime.utcnow(), time_zone).replace(day=1, hour=0, minute=0, second=0, microsecond=0) + relativedelta(months=1)
    start_date = end_date - relativedelta(months=6)
    data = defaultdict(lambda: {"month": None, "total": 0, "sold": 0})
    lead_objs = MR.query.join(MA, MR.mortgage_id == MA.mortgage_id).with_entities(func.date_trunc('month', MR.call_in_date_time).label('month'),
                func.count(func.distinct(MR.mortgage_id)).label('total')).filter(MR.call_in_date_time >= start_date, 
                MR.call_in_date_time < end_date).group_by('month').all()
    for obj in lead_objs:
        data[obj.month]["month"] = obj.month.month
        data[obj.month]["total"] = obj.total
    sold_objs =  MR.query.join(MA, MR.mortgage_id == MA.mortgage_id).with_entities(func.date_trunc('month', MA.sold_date).label('month'), 
                func.count(func.distinct(MA.mortgage_id)).label('sold')).filter(MA.lead_status == 7, MA.sold_date >= start_date, 
                MA.sold_date < end_date).group_by('month').all()
    for obj in sold_objs:
        data[obj.month]["month"] = obj.month.month
        data[obj.month]["sold"] = obj.sold
    return [data[month] for month in sorted(data.keys())]
