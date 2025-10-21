from datetime import datetime
from typing import (
    List, Tuple
    )

from sqlalchemy import or_
from app.models import (
    User, SubscriptionOrderSummary as SOS, 
    MarketplaceOrderSummary as MOS
    )
from app.services.utils import convert_datetime_to_timezone_date

from app.services.custom_errors import *
from app import redis_obj


def admin_listing_subscription_invoices(page: int, per_page: int,  payment_status: str = None, start_date: str = None,
        end_date: str = None, name: str = None) -> Tuple:
    orders_objs = SOS.query.join(User, User.id == SOS.user_id)
    if start_date:
        orders_objs = orders_objs.filter(SOS.created_at >= datetime.strptime(start_date, "%m-%d-%Y"))
    if end_date:
        orders_objs = orders_objs.filter(SOS.created_at < datetime.strptime(end_date, "%m-%d-%Y"))
    if payment_status:
        if payment_status == 'succeeded':
            orders_objs = orders_objs.filter(SOS.payment_status == payment_status)
        else:
            orders_objs = orders_objs.filter(
                SOS.payment_status.is_not(None), 
                SOS.payment_status != 'succeeded'
                )
    else:
        orders_objs = orders_objs.filter(SOS.payment_status.is_not(None))
    if name:
        orders_objs = orders_objs.filter(User.name.ilike(f"%{name}%"))
    orders_objs = orders_objs.with_entities(
            SOS.id, SOS.description, SOS.created_at, SOS.amount_received, 
            SOS.payment_status, SOS.states_chosen, SOS.payment_status, SOS.user_id, User.name
            ).order_by(SOS.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False)
    result = []
    for order in orders_objs.items:
        order = order._asdict()
        order['created_at'] = convert_datetime_to_timezone_date(order['created_at'])
        result.append(order)
    if result:
        return result, {'total': orders_objs.total, 'current_page': page, 'per_page': per_page, 'length': len(result)}
    raise NoContent()


def download_admin_listing_subscription_invoices(payment_status: str = None, start_date: str = None, 
    end_date: str = None, name: str = None) -> List:
    orders_objs = SOS.query.join(User, User.id == SOS.user_id)
    if start_date:
        orders_objs = orders_objs.filter(SOS.created_at >= datetime.strptime(start_date, "%m-%d-%Y"))
    if end_date:
        orders_objs = orders_objs.filter(SOS.created_at < datetime.strptime(end_date, "%m-%d-%Y"))
    if payment_status:
        if payment_status == 'succeeded':
            orders_objs = orders_objs.filter(MOS.payment_status == payment_status)
        else:
            orders_objs = orders_objs.filter(
                SOS.payment_status.is_not(None), 
                SOS.payment_status != 'succeeded'
                )
    else:
        orders_objs = orders_objs.filter(SOS.payment_status.is_not(None))
    if name:
        orders_objs = orders_objs.filter(User.name.ilike(f"%{name}%"))
    orders_objs = orders_objs.with_entities(
            SOS.id, SOS.description, SOS.created_at, SOS.amount_received, 
            SOS.payment_status, SOS.states_chosen, SOS.user_id, User.name
            ).order_by(SOS.created_at.desc())
    result = []
    for order in orders_objs.all():
        order = order._asdict()
        order['created_at'] = convert_datetime_to_timezone_date(order['created_at'])
        result.append(order)
    if result:
        return result, redis_obj.get("new_file_name")
    raise NoContent()



def admin_listing_marketplace_invoices(page: int, per_page: int,  payment_status: str = None, start_date: str = None,
        end_date: str = None, name: str = None) -> Tuple:
    orders_objs = MOS.query.join(User, User.id == MOS.user_id)
    if start_date:
        orders_objs = orders_objs.filter(MOS.created_at >= datetime.strptime(start_date, "%m-%d-%Y"))
    if end_date:
        orders_objs = orders_objs.filter(MOS.created_at < datetime.strptime(end_date, "%m-%d-%Y"))
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
    if name:
        orders_objs = orders_objs.filter(User.name.ilike(f"%{name}%"))
    orders_objs = orders_objs.with_entities(
            MOS.id, MOS.created_at, MOS.amount_received, 
            MOS.payment_status, MOS.user_id, 
            User.name, MOS.invoice_data
            ).order_by(MOS.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False)
    result = []
    for order in orders_objs.items:
        order = order._asdict()
        order['created_at'] = convert_datetime_to_timezone_date(order['created_at'])
        result.append(order)
    if result:
        return result, {'total': orders_objs.total, 'current_page': page, 'per_page': per_page, 'length': len(result)}
    raise NoContent()


def download_admin_listing_marketplace_invoices(payment_status: str = None, start_date: str = None, 
    end_date: str = None, name: str = None) -> List:
    orders_objs = MOS.query.join(User, User.id == MOS.user_id)
    if start_date:
        orders_objs = orders_objs.filter(MOS.created_at >= datetime.strptime(start_date, "%m-%d-%Y"))
    if end_date:
        orders_objs = orders_objs.filter(MOS.created_at < datetime.strptime(end_date, "%m-%d-%Y"))
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
    if name:
        orders_objs = orders_objs.filter(User.name.ilike(f"%{name}%"))
    orders_objs = orders_objs.with_entities(
            MOS.id, MOS.created_at, MOS.amount_received, 
            MOS.payment_status, MOS.user_id, User.name, 
            MOS.invoice_data
            ).order_by(MOS.created_at.desc())
    result = []
    for order in orders_objs.all():
        order = order._asdict()
        order['created_at'] = convert_datetime_to_timezone_date(order['created_at'])
        result.append(order)
    if result:
        return result, redis_obj.get("new_file_name")
    raise NoContent()