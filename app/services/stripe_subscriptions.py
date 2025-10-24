from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from random import randrange
from typing import (
    List, Dict, Tuple, Optional
    )

from flask import g, render_template
from app.models import (
    StripeCustomerSubscription as SCS, 
    PricingDetail as PD, StripePriceId as SPI,
    User, SubscriptionOrderSummary as SOS, 
    MailingLead as ML
    )
from app.services.sendgrid_email import SendgridEmailSending
from app.services.crud import CRUD
from app.services.utils import (
    date_time_obj_to_str, 
    convert_utc_to_timezone, 
    get_current_date_time,
    convert_datetime_to_timezone_date
    )

from app.services.stripe_service import (
    StripeService, 
    getting_session_status_subscription
    )
from app.services.coupon_service import PromotionService
from app.services.custom_errors import *
from config import Config_is
from app import redis_obj


# def create_immediate_charge_with_subscription(
#         id_: str, payload: Dict, items: List, billing_anchor: datetime):
#     """
#     Creates both:
#     1. An immediate payment for the current period
#     2. A subscription starting today for future payments
#     """
#     stripe_obj = StripeService()
#     # First create the subscription
#     subscription = stripe_obj.create_subscription(items, billing_anchor)
#     # Then create a checkout session for the immediate payment
#     session = stripe_obj.create_subscription_checkout_session(subscription.id, items, payload['success_url'], payload['cancel_url'], payload.get('stripe_promotion_id'))
#     CRUD.create(SCS, dict(id=id_, name=payload['item']['name'], original_price=payload['item']['total_amount'], stripe_price_id=payload['price_id'], stripe_product_id=payload['stripe_product_id'], user_id=g.user['id'], accepted_terms_and_conditions=True, states_chosen=payload['item']['states'], pricing_id=payload['item']['pricing_id'], started_at=billing_anchor.astimezone(ZoneInfo('UTC'))))
#         # payload.get('stripe_promotion_id')#TODO: Discount check////////
#         # original_price = db.Column(db.Float, nullable=True)
#         # discounted_price = db.Column(db.Float, nullable=True)
#         # stripe_subscription_id = db.Column(db.String(40), nullable=True)
#         # status = db.Column(db.String(120))
#         # stripe_setup_intent = db.Column(db.String(40), nullable=True)
#         # cancel_at = db.Column(db.DateTime)
#         # cancelled_at = db.Column(db.DateTime)
#         # cancelation_reason = db.Column(db.Text) TODO: check
#     return session


def creating_future_subscription(id_: str, payload: Dict, items: List, billing_anchor: datetime):
    """
    Creates a subscription with future billing on next Wednesday at 6PM IST
    """
    result = StripeService().create_future_subscription(payload['item']['total_amount'], items, billing_anchor.astimezone(ZoneInfo('UTC')), payload['success_url'], payload['cancel_url'])
    User.query.filter_by(id=g.user['id']).update({'states_chosen': payload['item']['states'], 'modified_at': User.modified_at})
    CRUD.create(SCS, dict(
        id=id_, 
        name=payload['item']['name'], 
        total_amount=payload['item']['total_amount'],
        net_price=payload['item']['net_price'],
        unit_price=payload['item']['unit_price'],    
        # discounted_price=result.get('amount_total'),
        stripe_price_id=payload['price_id'], 
        stripe_product_id=payload['stripe_product_id'], 
        user_id=g.user['id'], 
        accepted_terms_and_conditions=True, 
        states_chosen=payload['item']['states'], 
        pricing_id=payload['item']['pricing_id'], 
        started_at=billing_anchor.astimezone(ZoneInfo('UTC'))
        )
    )
    return result


def create_subscription_with_possible_initial_charge(id_: str, payload: Dict):
    """
    Creates a subscription that:
    - Charges immediately AND creates subscription if on Wednesday after 9AM 
    - Creates normal subscription (with future billing) otherwise
    """
    required_fields = ['item', 'success_url', 'cancel_url']
    if not all(field in payload for field in required_fields):
        raise BadRequest("Missing required fields")
    if payload.get('promo_code_db_id'):
        PromotionService.validate_promo_code(payload['promo_code_db_id'])
    items = [
        {
            'price': payload['price_id'],
            'quantity': payload['item']['quantity']
        }
        ]
    current_time = get_current_date_time(datetime.utcnow())
    target_time = current_time.replace(hour=23, minute=59, second=59, microsecond=59)
    stripe_obj = StripeService()
    #TODO changed to 2 from 3 confirm before move to production
    if current_time.weekday() ==  Config_is.RENEWAL_DAY_OF_WEEK and (current_time + timedelta(minutes=15)) < target_time:
        print("today is wednesday***")
        result = stripe_obj.create_subscription_checkout_session(items, payload['success_url'], payload['cancel_url'], id_, payload.get('stripe_promotion_id'))
        getting_session_status_subscription(result['session_id'])
        User.query.filter_by(id=g.user['id']).update({'states_chosen': payload['item']['states'], 'modified_at': User.modified_at})
        CRUD.create(SCS, dict(
            id=id_, 
            name=payload['item']['name'], 
            total_amount=result.get('amount_subtotal')/100 if result.get('amount_subtotal') else payload['item']['total_amount'], 
            net_price=payload['item']['net_price'],
            unit_price=payload['item']['unit_price'],
            # discounted_price=result.get('amount_total') or payload['item']['total_amount'],
            stripe_price_id=payload['price_id'], 
            stripe_product_id=payload['stripe_product_id'], 
            user_id=g.user['id'], 
            accepted_terms_and_conditions=True, 
            states_chosen=payload['item']['states'], 
            pricing_id=payload['item']['pricing_id'], 
            started_at=datetime.utcnow())
            )

    else:
        print("else")
        days_until_wednesday = (Config_is.RENEWAL_DAY_OF_WEEK - current_time.weekday()) % 7
        next_wednesday = current_time + timedelta(days=days_until_wednesday)
        billing_anchor = next_wednesday.replace(hour=8, minute=randrange(0, 59), second=randrange(0, 59), microsecond=randrange(0, 59))
        result = creating_future_subscription(id_, payload, items, billing_anchor)
    return result
    
        # original_price = db.Column(db.Float, nullable=True)
        # discounted_price = db.Column(db.Float, nullable=True)
        # stripe_subscription_id = db.Column(db.String(40), nullable=True)
        # status = db.Column(db.String(120))
        # stripe_setup_intent = db.Column(db.String(40), nullable=True)
        # cancel_at = db.Column(db.DateTime)
        # cancelled_at = db.Column(db.DateTime)
        # cancelation_reason = db.Column(db.Text)

    
def paginated_subscriptions_listing(
        user_id: str, page: int, per_page: int, 
        time_zone: str, status: Optional[str]
        ) -> Tuple:
    result = []
    if user_id != g.user['id'] and g.user['role_id'] != 1:
        raise Forbidden()
    query = SCS.query.filter(SCS.user_id == user_id)
    if status:
        query = query.filter(SCS.status == status)
    scs_objs = query.with_entities(
        SCS.name, SCS.stripe_subscription_id, SCS.unit_price, SCS.net_price, 
        SCS.total_amount, SCS.status, SCS.started_at, SCS.cancel_at, 
        SCS.cancelation_reason, SCS.cancelled_at, SCS.acknowledgment_id, 
        SCS.states_chosen, SCS.id).order_by(SCS.modified_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False)
    for scs_obj in scs_objs.items:
        scs =  scs_obj._asdict()
        for dt in ['started_at', 'cancel_at', 'cancelled_at']:
            if getattr(scs_obj, dt):
                scs[dt] = date_time_obj_to_str(getattr(scs_obj, dt))
        scs['created_at'] = convert_utc_to_timezone(scs_obj.started_at, time_zone)
        result.append(scs)
    if result:
        return result, {'total': scs_objs.total, 'current_page': page, 'per_page': per_page, 'length': len(result)}
    raise NoContent()


def subscription_webhook(hook_id: str, payload: Dict) -> bool:
    data = payload['data']['object']
    if payload.get('type') == 'customer.subscription.created':
        scs_obj, *user_obj = SCS.query.join(User, User.id == SCS.user_id).filter(
            SCS.stripe_price_id == data['plan']['id'], 
            SCS.stripe_product_id == data['plan']['product'], 
            User.stripe_customer_id == data['customer'], 
            SCS.stripe_subscription_id == None
            ).with_entities(
                SCS, User.id, User.email, User.name).order_by(SCS.created_at.desc()).first()
        if not scs_obj:
            scs_obj, *user_obj = SCS.query.join(User, User.id == SCS.user_id).filter(
            SCS.stripe_price_id == data['plan']['id'], 
            SCS.stripe_product_id == data['plan']['product'], 
            User.stripe_customer_id == data['customer'], 
            SCS.stripe_subscription_id == data['id']
            ).with_entities(
                SCS, User.id, User.email, User.name).order_by(SCS.created_at.desc()).first()
        if not scs_obj:
            SendgridEmailSending(
                Config_is.DEVELOPERS_EMAIL_ADDRESS, 
                f"{Config_is.ENVIRONMENT} {Config_is.APP_NAME} failed subscription webhook {hook_id}", 
                f'<p>Failed customer_id validation</p><p>payload={payload}</p>', 8
                ).send_email_without_logs()
            return False
        print('updating stripe id in db')
        scs_obj.stripe_subscription_id = data['id']
        scs_obj.started_at=datetime.fromtimestamp(data['items']['data'][0]['current_period_start'])
        scs_obj.status=data['status']
        CRUD.db_commit()
        current_time = get_current_date_time(datetime.utcnow())
        target_time = current_time.replace(hour=23, minute=59, second=59, microsecond=59)
        if current_time.weekday() == Config_is.RENEWAL_DAY_OF_WEEK and (current_time + timedelta(minutes=15)) < target_time:
            StripeService().update_stripe_subscription(scs_obj.stripe_subscription_id, dict(billing_cycle_anchor='now', proration_behavior='none'))
    
        print('committed')
        # TODO: check the amount fo discount sale
        # amount=payload['data']['object']['items']['data'][0]['plan']['amount']/100,
        email_body = render_template(
            "subscription_email_notification.html", 
            name=user_obj[2],
            user_name=user_obj[2],
            item_name=scs_obj.name,
            states=scs_obj.states_chosen,
            subscription_status=scs_obj.status,
            subscription_id=scs_obj.stripe_subscription_id,
            subscription_amount=data['items']['data'][0]['plan']['amount']/100
            )
        SendgridEmailSending(
            [{'user_id': str(user_obj[0]), 'email': user_obj[1]}],
            f"{Config_is.APP_NAME} Subscription: {scs_obj.name}", 
            email_body, 8).send_email()
    elif payload.get('type') == 'customer.subscription.deleted':
         return process_cancelled_subscription(payload, hook_id)
    else:
        # CRUD.update(SCS, {'stripe_subscription_id': payload['data']['object']['id']}, {'status': payload['data']['object']['status']}):
        SendgridEmailSending(
            Config_is.DEVELOPERS_EMAIL_ADDRESS, 
            f"{Config_is.ENVIRONMENT} {Config_is.APP_NAME} subscription webhook other than created {hook_id}", 
            f'<p>Failed customer_id validation</p><p>payload={payload}</p>', 8
            ).send_email_without_logs()
    return True


def process_cancelled_subscription(payload: Dict, hook_id: str) -> bool:
    data = payload['data']['object']
    scs_obj, *user_obj = SCS.query.join(User, User.id == SCS.user_id).filter(
        SCS.stripe_subscription_id ==  data['id']
    ).with_entities(SCS, User.id, User.email, User.name).first()
    if scs_obj:
        scs_obj.cancelled_at = datetime.fromtimestamp(data['canceled_at'])
        scs_obj.status = data['status']
        User.query.filter_by(id=scs_obj.user_id).update({'states_chosen': [], 'modified_at': User.modified_at})
        CRUD.db_commit()
        email_body = render_template(
            "subscription_cancellation_notification.html",
            name=user_obj[2],
            subscription_id = data['id'],
            canceled_at = datetime.fromtimestamp(data['canceled_at']).strftime("%Y-%m-%d %H:%M:%S"),
            item_name = scs_obj.name,
            subscription_status = data['status']
        )
        SendgridEmailSending(
            [{'user_id': str(user_obj[0]), 'email': user_obj[1]}],
            f"{Config_is.APP_NAME}s Subscription Cancelled: {scs_obj.name}",
            email_body, 8
        ).send_email()
    else:
        SendgridEmailSending(
            Config_is.DEVELOPERS_EMAIL_ADDRESS,
            f"{Config_is.ENVIRONMENT} Subscription Deletion: Subscription ID not found {hook_id}",
            f"<p>Subscription ID: {data['status']}</p><p>payload={payload}</p>",
            8
        ).send_email_without_logs()
    return True
   

def handle_subscription_cancellation(subscription_id: str, cancelation_reason: str) -> bool:
    subscription = SCS.query.filter_by(
        id=subscription_id,
        user_id=g.user["id"]
        ).first()
    if subscription.stripe_subscription_id:
        StripeService().cancel_stripe_subscription(subscription.stripe_subscription_id)
    subscription.cancel_at = datetime.utcnow()
    subscription.cancelation_reason = cancelation_reason
    subscription.status = 'canceled'
    CRUD.db_commit()
    return True
      
     
def get_my_current_subscription(user_id: str) -> Dict:
    if g.user['role_id'] != 1 and user_id != g.user['id']:
        raise Forbidden()
    subscription_obj = SCS.query.join(PD, PD.id == SCS.pricing_id).with_entities(
        SCS.status, SCS.accepted_terms_and_conditions, SCS.name, 
        SCS.states_chosen, SCS.started_at, SCS.stripe_product_id, 
        SCS.total_amount, SCS.unit_price, SCS.net_price, SCS.stripe_subscription_id,
        SCS.id.label('db_subscription_id'), PD.id.label('db_pricing_id'), PD.title,
        SCS.started_at).filter(SCS.user_id == user_id, SCS.status == "active").first()
    if not subscription_obj:
        subscription_obj = SCS.query.join(PD, PD.id == SCS.pricing_id).with_entities(
            SCS.status, SCS.accepted_terms_and_conditions, SCS.name, 
            SCS.states_chosen, SCS.started_at, SCS.stripe_product_id, SCS.total_amount,
            SCS.id.label('db_subscription_id'), PD.id.label('db_pricing_id'), PD.title,
            SCS.unit_price, SCS.net_price, SCS.stripe_subscription_id).filter(SCS.user_id == user_id).order_by(
                SCS.created_at.desc()).first()
    if not subscription_obj:
        raise NoContent('Please subscribe to any weekly mailer leads')
    data = subscription_obj._asdict()
    data['started_at'] = datetime.strftime(convert_datetime_to_timezone_date(data['started_at']), '%m-%d-%Y')
    return data


def updating_subscribed_states(subscription_id: str, states: List) -> bool:
    if 5 <= len(states) <= 10:
        User.query.filter_by(id=g.user['id']).update({'states_chosen': states, 'modified_at': User.modified_at})
        CRUD.update(
            SCS, 
            dict(user_id=g.user['id'], id=subscription_id), 
            {'states_chosen': states}
            )
        return True
    raise BadRequest('You have to select minum 3 states and can have maximum 10')

def get_next_morgage_id_expecting():
    mortgage_ids = []
    lead_objs = ML.query.with_entities(ML.mortgage_id, ML.temp_mortgage_id).all()

    for each in lead_objs:
        if each.mortgage_id.isdigit():
            mortgage_ids.append(int(each.mortgage_id))

        if each.temp_mortgage_id and each.temp_mortgage_id.isdigit():
            mortgage_ids.append(int(each.temp_mortgage_id))

    highest_id = max(mortgage_ids,  default=0) 
    redis_obj.set('new_file_name', highest_id+1)
    return highest_id+1


def listing_subscription_invoices(page: int, per_page: int) -> Tuple:
    orders_obj = SOS.query.filter(
        SOS.user_id == g.user['id'], SOS.stripe_subscription_id != None
        ).with_entities(
            SOS.id, SOS.description, SOS.created_at, SOS.amount_received, 
            SOS.payment_status, SOS.states_chosen, SOS.payment_status
            ).order_by(SOS.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False)
    result = []
    for order in orders_obj.items:
        order = order._asdict()
        order['description'] = order['description'].split(' (at')[0 ].split(' × ')[0]
        order['created_at'] = convert_datetime_to_timezone_date(order['created_at'])
        result.append(order)
    if result:
        return result, {'total': orders_obj.total,'current_page': page, 'per_page': per_page, 'length': len(result)}
    raise NoContent()


def list_previous_subscriptions(page: int, per_page: int, time_zone: str, user_id: str = None) -> Dict:
    if user_id:
        if g.user['role_id'] != 1 and user_id != g.user['id']:
            raise Forbidden()
    else:
        user_id = g.user['id']
    scs_objs = SCS.query.filter(SCS.user_id == user_id, SCS.status != "active").with_entities(SCS.name, SCS.status, 
                SCS.started_at, SCS.cancel_at, SCS.cancelation_reason, SCS.stripe_subscription_id).order_by(
                SCS.modified_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    result = []
    for scs_obj in scs_objs.items:
        scs = scs_obj._asdict()
        scs['started_at'] = convert_utc_to_timezone(scs.get('started_at'), time_zone)
        scs['cancel_at'] = convert_utc_to_timezone(scs.get('cancel_at'), time_zone)
        result.append(scs)
    if result:
        return result, {'total': scs_objs.total, 'current_page': page, 'per_page': per_page, 'length': len(result)}
    raise NoContent()
