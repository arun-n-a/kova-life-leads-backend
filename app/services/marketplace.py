from typing import (List, Dict, Tuple)
from datetime import (datetime, timedelta)
from collections import defaultdict

from flask import g
from sqlalchemy import (
    case, func, literal, or_, cast, Date, Integer
    )
from app.models import (
    MailingLead as ML, 
    MailingAssignee as MA,
    MailingResponse as MR,
    MarketplaceOrderSummary as MOS,
    PricingDetail as PD,
    ShoppingCart as SC,
    User
    )
from app.services.utils import (
    convert_datetime_to_timezone_date, 
    date_time_obj_to_str, 
    date_object_to_string,
    convert_utc_to_timezone
)
from app.services.custom_errors import *
from app import redis_obj
from constants import USA_STATES


def mailing_completed_incomplete_statewise_count_for_sale(page: int, per_page: int, states: str = None) -> Tuple:
    states = list(USA_STATES.values()) if not states else states.split(',')
    # TODO: category and source based have to be done
    db_query = (
        MR.query
        .join(ML, ML.mortgage_id == MR.mortgage_id)
        .filter(
            ~ML.lead_assigned_members.any(MA.agent_id.in_(g.user['mailing_agent_ids'])), 
            or_(
                ML.last_purchased_date == None,
                ML.last_purchased_date < (datetime.utcnow() - timedelta(days=30)).date()
            ),
            ML.disabled_in_marketplace == False,
            ML.is_in_checkout == False,
            ML.can_sale == True,
            ML.state.in_(states),
            MR.call_in_date_time < (datetime.utcnow() - timedelta(days=30)),
            MR.call_in_date_time >= (datetime.utcnow() - timedelta(days=730)),
            )
        .with_entities(
            ML.state,
            func.count(ML.mortgage_id).filter(MR.completed== True).label("completed"),
            func.count(ML.mortgage_id).filter(MR.completed== False).label("incomplete")
        )
        .group_by(ML.state)
    ).paginate(page=page, per_page=per_page, error_out=False)
    result = []
    # Only include 'complete' and 'incomplete' in the result if their counts are non-zero
    # This eliminates zero-count entries from the output JSON
    for ld in db_query.items:
        item = {"state": ld.state}
        if ld.completed:
            item["completed"] = ld.completed
        if ld.incomplete:
            item["incomplete"] = ld.incomplete
        result.append(item)
    if result:
        return result, {'total': db_query.total, 'current_page': db_query.page, 'length': len(result), 
                            'per_page': db_query.per_page}
    raise NoContent('Sorry leads are not available for sale.')

    
def specific_state_available_leads(state: str) -> List:
     # TODO: category and source based have to be done
    today = datetime.utcnow()
    today_date = today.date()
    days_diff_expression = cast(
        literal(today_date) - cast(MR.call_in_date_time, Date),
        Integer
        )
    result = defaultdict(dict)
    days_diff_expression = cast(
        func.extract('epoch', literal(today) - MR.call_in_date_time) / (60 * 60 * 24),
        Integer
        )
    month_bucket_expr = case(
        ((days_diff_expression >= 30) & (days_diff_expression <= 60), 1),
        ((days_diff_expression > 60) & (days_diff_expression <= 90), 2),
        ((days_diff_expression > 90) & (days_diff_expression <= 180), 3),
        ((days_diff_expression > 180) & (days_diff_expression <= 270), 6),
        ((days_diff_expression > 270) & (days_diff_expression <= 730), 9)
        )
    db_query = (
        ML.query
        .join(MR, MR.mortgage_id == ML.mortgage_id)
        .filter(
            ~ML.lead_assigned_members.any(MA.agent_id.in_(g.user['mailing_agent_ids'])),
            or_(
                ML.last_purchased_date == None,
                ML.last_purchased_date < (today_date - timedelta(days=30))
            ),
            ML.disabled_in_marketplace == False,
            ML.is_in_checkout == False,
            ML.can_sale == True,
            ML.state == state,
            MR.call_in_date_time >= (datetime.utcnow()-timedelta(days=730)),
            MR.call_in_date_time < (datetime.utcnow()-timedelta(days=30)))
        .with_entities(
            MR.completed,
            month_bucket_expr.label("month"),
            func.count(ML.mortgage_id).label("count")
            )
        .group_by(
            MR.completed,
            month_bucket_expr
            )
        )
    for ld in db_query.all():
        result[ld.month] |= {'completed' if ld.completed else 'incomplete': ld.count, 'month': ld.month}
    if result:
        pop_none = result.pop(None, None)
        sorted_dict = {key: result[key] for key in sorted(result.keys())}
        return list(sorted_dict.values())
    raise NoContent("Sorry there is not leads available for purchase")

def listing_marketplace_orders(user_id: str, page: int, per_page: int, timezone: str, payment_status: str = None, 
        order_id: int = None) -> Dict:
    if g.user['role_id'] != 1 and user_id != g.user['id']:
        raise Forbidden()
    orders_objs = MOS.query.filter_by(user_id=user_id).with_entities(
            MOS.id, MOS.stripe_payment_id, MOS.total_amount,
            MOS.discounted_price, MOS.amount_received,
            MOS.payment_status, MOS.created_at,
            MOS.invoice_data
        )
    if payment_status:
        if payment_status == 'succeeded':
            orders_objs = orders_objs.filter(MOS.payment_status == payment_status)
        else:
            orders_objs = orders_objs.filter(
                MOS.payment_status.is_not(None), 
                MOS.payment_status != 'succeeded'
                )
    else:
        orders_objs = orders_objs.filter(MOS.payment_status.is_not(None))
    if order_id:
        orders_objs = orders_objs.filter(MOS.id == order_id)
    orders_objs= orders_objs.order_by(MOS.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    orders = []
    for order in orders_objs.items:
        order_dict = order._asdict()
        print(order_dict)
        order_dict["created_at"] = convert_datetime_to_timezone_date(order_dict['created_at'], timezone)
        orders.append(order_dict)
    return orders, {"total": orders_objs.total,"current_page": orders_objs.page, 
            "length": len(orders),"per_page": orders_objs.per_page}

def getting_leads_orders(
        user_id: int,page: int, per_page: int, 
        order_id: str, cart_item_id: str = None
        ) -> Dict:
    if user_id != g.user['id'] and g.user['role_id'] != 1:
        raise Forbidden()
    leads_query = (
        ML.query
        .join(MA, MA.mortgage_id == ML.mortgage_id)
        .join(MR, MR.mortgage_id == MA.mortgage_id)
        )
    if order_id:
        leads_query = leads_query.join(
            SC, SC, SC.order_id == MA.cart_item_id
            ).filter(SC.order_id == order_id)
    elif cart_item_id:
        leads_query = leads_query.filter(MA.cart_item_id == cart_item_id)
    leads_query = leads_query.filter(
        MA.purchased_user_id == user_id
        ).with_entities(
            ML.mortgage_id, ML.source_id, ML.full_name, ML.state, ML.city,
            MA.id.label("assignee_id"), MA.agent_id, MA.notes,
            MA.lead_status, MA.suppression_rejection_msg, MA.campaign_name,
            MR.call_in_date_time, MR.completed, MR.ivr_response, MR.ivr_logs,
            ML.zip, ML.address, ML.first_name, ML.last_name,
            ML.lender_name, ML.loan_amount, ML.loan_date,
            MA.purchased_date
            )
    result = []
    leads = leads_query.paginate(page=page, per_page=per_page, error_out=False)
    for row in leads.items:
        data = row._asdict()
        data['loan_date'] = date_object_to_string(data.get('loan_date'))
        data['call_in_date_time'] = date_time_obj_to_str(data.get('call_in_date_time'))
        result.append(data)
    if result:
        return result, {'total': leads.total,'current_page': leads.page,'per_page': leads.per_page,'length': len(result)
        }
    raise NoContent()

