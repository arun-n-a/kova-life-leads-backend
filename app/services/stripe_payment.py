import json
import queue
from typing import (
    Dict, List, Optional, Union, Tuple
)
from math import floor
from decimal import Decimal
from datetime import (
    datetime, timedelta, time
    )
from threading import Thread
from random import randrange
from time import sleep
from concurrent.futures import ThreadPoolExecutor


import stripe
from flask import (
    g, render_template, request
    )
from sqlalchemy import or_, desc
from app.services.custom_errors import *
from app.models import (
    StripeCustomerSubscription as SCS,
    User, PaymentMethod as PM,
    PromotionCode as PC,
    SubscriptionOrderSummary as SOS,
    MarketplaceOrderSummary as MOS,
    ShoppingCart as SC,
    PricingDetail as PD, UserPromotionCodeHistory as UPCH
    )
from app.services.crud import CRUD
from app.services.utils import (
    add_redis_ttl_data,
    convert_datetime_to_timezone_date,
    get_current_date_time,
    utc_to_timezone_conversion
    )
from app.services.sendgrid_email import SendgridEmailSending
from app.services.stripe_service import StripeService
from app.services.coupon_service import PromotionService
from app.services.shopping_cart import assigning_reserved_mailing_leads
from app import db, redis_obj
from config import Config_is
from constants import (
    STRIPE_COMMISSION_FEE,
    COMPANY_INVOICE_ADDRESS
    )

def truncate(num: Union[float, int], decimals=2) -> float:
    factor = 10 ** decimals
    return floor(num * factor) / factor

def update_payment_failed_status(payload: Dict):
    data = payload['data']['object']
    customer_obj = User.query.filter_by(stripe_customer_id=data['customer']).with_entities(User.id, User.name, User.email).first()
    if data.get('description') and data.get('description', '') and 'subscription' in data.get('description', '').lower(): 
        scs_obj = SCS.query.filter(SCS.user_id == customer_obj.id, or_(
            SCS.total_amount == data['amount']/100,
            SCS.net_price == data['amount']/100,
            )).with_entities(
                SCS.name, SCS.id, SCS.stripe_product_id, 
                SCS.stripe_subscription_id,
            ).order_by(SCS.created_at.desc()).first()
        if not scs_obj:
            scs_obj = {}
        else:
            scs_obj = scs_obj._asdict()
        CRUD.create_or_update(
            SOS, 
            {'stripe_payment_id': data['id']}, 
            {'user_id': customer_obj.id,
             'stripe_payment_id': data['id'],
             'stripe_subscription_id': scs_obj.get('stripe_subscription_id'),
             'subtotal_amount': data['amount']/100,
             'subscription_db_id': scs_obj.get('id'),
             'stripe_product_id': scs_obj.get('stripe_product_id'),
             'description': scs_obj.get('name'),
             'payment_status': data['status']
             })
    else:
        CRUD.update(MOS, {'stripe_payment_id': data['id'], 'payment_status': 'failed'} )
    customer_template = render_template(
        "customer_payment_failed_alert.html",
        customer_name=customer_obj.name,
        amount=data['amount']/100,
        )
    SendgridEmailSending(
        [{'user_id': customer_obj.id, 'email': customer_obj.email}],
        f"[SheildNest Payment Failed]: {data['id']}",
        customer_template, 12
        ).send_email()  
    admin_template = render_template(
        "admin_payment_failed_alert.html",
        customer_name=customer_obj.name,
        amount=data['amount']/100,
        customer_email=customer_obj.email
        )
    SendgridEmailSending(
        to_emails=Config_is.ALERT_EMAIL,
            html_content=admin_template,
            subject=f"[SheildNest Payment Failed]: {customer_obj.name} {data['id']}"
        ).send_email_without_logs()
    return True

def stripe_payment_status_update(payload: Dict) -> bool:
    print(f'stripe_payment_status_update {payload}')
    if payload['type'] == 'payment_intent.created':
        return True
    data = payload['data']['object']
    if data.get('description') and 'subscription' in data.get('description').lower():
        subscription_payment_status_update(payload)
    else:
        # Marketplace direct purchase
        payment_status_update_direct_checkout(payload)
    return True

def payment_status_update_direct_checkout(payload: Dict):
    data = payload['data']['object']
    thread_response, cart_items = queue.Queue(), []
    # if not data.get('cart_details'):
    #     raise BadRequest('Shopping cart is empty. Please try again')
    
    cart_temp_ids_with_pricing_id = redis_obj.get(f"mp_order_{data['customer']}_{data['amount']}")
    print(f'cart_temp_ids_with_pricing_id {cart_temp_ids_with_pricing_id}')
    # if not cart_temp_ids_with_pricing_id:
    #     order_obj = MOS.query.filter_by(stripe_payment_id=data['id']).first()
    if not cart_temp_ids_with_pricing_id:
        SendgridEmailSending(
            to_emails=Config_is.DEVELOPERS_EMAIL_ADDRESS,
            html_content=f"<body><p>first failed payload is marketplace or not confirm {payload}</p></body>",
                    subject=f"payment_status_update_direct_checkout: {data['id']}"
                ).send_email_without_logs()
        return
    cart_temp_ids_with_pricing_id = json.loads(cart_temp_ids_with_pricing_id)
    order_id = cart_temp_ids_with_pricing_id.pop('order_id')
    campaign_name = cart_temp_ids_with_pricing_id.pop('campaign_name')
    user_info = cart_temp_ids_with_pricing_id.pop('user_info')
    failed_lead_assigning_details, cart_id_with_temp_id = [], {}
    for k, cart_id in cart_temp_ids_with_pricing_id.items():
        redis_data = redis_obj.get(k)
        if not redis_data:
            failed_lead_assigning_details.append({"key": k, "cart_id": cart_id})
        cart_id_with_temp_id[cart_id] = k.split('_')[-1]
    if failed_lead_assigning_details:
        SendgridEmailSending(
            to_emails=Config_is.DEVELOPERS_EMAIL_ADDRESS,
            html_content=f"<body><p>Failed  issue with data in redis  redis_data={redis_data}<br> order_id {order_id} Error: {str(e)}</p></body>",
                    subject=f"issue with redis purchse webhook{user_info['id']} {user_info['name']} {campaign_name}"
                ).send_email_without_logs()
        return True
    today_is = convert_datetime_to_timezone_date(datetime.utcnow())
    #TODO: Order campaign handle
    carts_obj = (
        SC.query.join(PD, PD.id == SC.pricing_id)
        .filter(
            SC.user_id == user_info['id'], 
            SC.id.in_(list(cart_id_with_temp_id.keys())), 
            SC.is_active == True
            )
        .with_entities(
            SC.id, SC.state, PD.month, SC.quantity, 
            PD.source, PD.category, PD.title,
            SC.pricing_id, PD.completed, PD.unit_price
            )
        )
    with ThreadPoolExecutor(max_workers=5) as executor: 
        for cart_obj in carts_obj.all():
            cart_item = cart_obj._asdict()
            cart_items.append(cart_item) 
            executor.submit(
                    assigning_reserved_mailing_leads, 
                    user_info, 
                    campaign_name,
                    cart_item,
                    cart_id_with_temp_id[str(cart_obj.id)],
                    order_id, 
                    today_is,
                    thread_response
                    )

    order_obj = MOS.query.filter(
        MOS.user_id == user_info['id'], 
        MOS.stripe_payment_id == data['id']
    ).first()
    if not order_obj:
        order_obj = MOS.query.filter(
            MOS.user_id == user_info['id'], 
            MOS.id == order_id
        ).first()
    invoice_data = order_obj.invoice_data
    if data.get("charges"):
        charge = data["charges"]["data"][0]
        card = charge["payment_method_details"]["card"]
        invoice_data["payment_details"] = {
            "method": charge["payment_method_details"]["type"],
            "card_brand": card["brand"],
            "card_last4": card["last4"],
            "card_expiry": f"{card['exp_month']}/{card['exp_year']}"
        }
        order_obj.invoice_data = invoice_data
    order_obj.stripe_payment_id = data['id']
    order_obj.amount_received = data['amount_received'] / 100
    order_obj.payment_status = data['status']
    print(invoice_data)
    CRUD.db_commit()
    failed_thread = 0
    for _ in range(len(cart_id_with_temp_id)):
        try:
            res = thread_response.get(timeout=20)
            if not isinstance(res, bool):
                failed_thread += 1
        except queue.Empty:
            failed_thread +=1
    if failed_thread:
        SendgridEmailSending(
            to_emails=Config_is.DEVELOPERS_EMAIL_ADDRESS,
            html_content=f"<body><p>EMpty Queue  {cart_id_with_temp_id}<br> order_id {order_id} failed {payload}</p></body>",
                    subject=f"MP Lead assign Failed: {user_info['id']} {user_info['name']} {campaign_name}"
                ).send_email_without_logs()
        return 
    show_purchased_tem = render_template(
        "lead_purchase_summary.html",
        name=user_info['name'],
        total_paid_amount=data['amount_received']/100,
        cart_items=cart_items
        )
    SendgridEmailSending(
        [{'user_id': user_info['id'], 'email': user_info['email']}],
        f"[Marketplace PURCHASE CONFIRMATION]: {campaign_name}",
        show_purchased_tem, 11
        ).send_email()  
    return True

def subscription_payment_status_update(payload: Dict):
    print(f'*subscription_payment_status_update')
    stripe_obj = StripeService()
    data = payload['data']['object']
    result = (
        SCS.query.join(User, User.id == SCS.user_id)
        .filter(
            User.stripe_customer_id == data.get('customer'), 
            SCS.status == 'active'
            )
        .with_entities(SCS, User).order_by(SCS.modified_at.desc())
        .first()
    )
    if not result:
        # Send slert
        pass
    subscription, user_obj = result
    payment_intent = stripe_obj.retrieve_payment_intent(data['id'])
    payment_method = stripe_obj.retrieve_payment_method(payment_intent.payment_method)
    duplicated_obj = None
    if datetime.utcnow().date() == subscription.created_at.date():
        sleep(randrange(3, 8))
        duplicated_obj = SOS.query.filter(SOS.user_id==user_obj.id, SOS.subscription_db_id == subscription.id, SOS.created_at >= subscription.created_at).first()
    os_obj = SOS.query.filter(SOS.stripe_payment_id == data['id']).first()
    if (duplicated_obj and os_obj) and duplicated_obj.stripe_payment_id != data['id']:
        db.session.delete(duplicated_obj)
    today_is = utc_to_timezone_conversion(datetime.utcnow())
    if not os_obj:
        promo_obj = None

        if data['status'] == 'succeeded':   
            subscription_data = stripe.Subscription.retrieve(
                subscription.stripe_subscription_id,
                expand=['discounts']
            )

            promo_code_id = (subscription_data.get('discounts') or [{}])[0].get('promotion_code')
            if promo_code_id:
                promo_obj = PC.query.filter(PC.stripe_promotion_id == promo_code_id).first()

        os_obj = CRUD.create_or_update(
            SOS,
            dict(stripe_payment_id=data['id']),
            dict(
                stripe_payment_id=data['id'],
                payment_status=data['status'],
                subtotal_amount=payment_intent.amount / 100,
                amount_received=payment_intent.amount_received / 100,
                discounted_price=None,
                stripe_price_id=subscription.stripe_price_id,
                states_chosen=subscription.states_chosen,
                user_id=subscription.user_id,
                subscription_db_id=subscription.id,
                stripe_subscription_id=subscription.stripe_subscription_id,
                description=subscription.name,
                promo_code_db_id=promo_obj.id if promo_obj else None,
            )
        )

        if promo_obj:
            promo_used_before = (UPCH.query
                    .filter(
                        UPCH.promotion_id == promo_obj.id,
                        UPCH.user_id == subscription.user_id,
                        UPCH.subscription_order_id == os_obj.id
                    )
                    .order_by(desc(UPCH.created_at))
                    .first()
                )

            if not promo_used_before:
                CRUD.create(UPCH, dict(
                    promotion_id=promo_obj.id,
                    user_id=subscription.user_id,
                    pricing_id=subscription.pricing_id,
                    subscription_order_id=os_obj.id
                ))
    
    invoice_data = {
            "from": COMPANY_INVOICE_ADDRESS,
            'commission': STRIPE_COMMISSION_FEE * 100,
            'bill_to': {'name': user_obj.name, 'agency_name': user_obj.agency_name, 'email': user_obj.email, 'phone': user_obj.phone},
            "card_brand": payment_method.card.brand,
            "card_last4": payment_method.card.last4,
            "card_expiry": f"{payment_method.card.exp_month}/{payment_method.card.exp_year}",
            "status": data["status"],
            "currency": payment_intent.currency,
            "description": subscription.name,
            "method": payment_method.type,
            "amount": payment_intent.amount/100,
            "start_date": today_is.strftime('%m-%d-%Y'),
            "end_date": (today_is+timedelta(days=7)).strftime('%m-%d-%Y'),
            'invoice_number': f"INV-{today_is.strftime('%Y%m%d')}-{os_obj.invoice_id}"
            }
    os_obj.invoice_data = invoice_data    
    CRUD.db_commit()
    email_body = render_template(
        "stripe_payment_email.html", 
        name=user_obj.name, description=os_obj.description, 
        total_amount=payment_intent.amount/100, 
        paid_amount=payment_intent.amount_received/100, 
        payment_date=datetime.strftime(convert_datetime_to_timezone_date(os_obj.created_at), '%m-%d-%Y'), 
        payment_id=os_obj.stripe_payment_id, 
        subscription_id=os_obj.stripe_subscription_id
        )
    SendgridEmailSending(
        [{'user_id': str(user_obj.id), 'email': user_obj.email}], 
        f"🛒 New payment Alert - {Config_is.APP_NAME} {os_obj.stripe_payment_id}", 
        email_body, 6
        ).send_email()
    # redis_obj.delete(subscription.stripe_subscription_id)
    return False


# def marketplace_direct_purchase_checkout(payload: Dict):
#     #arun
#     """
#     - Marektplace direct purchase with immmediate debit checkout
#     """
#     print('marketplace_direct_purchase_checkout')
#     print(payload)
#     total_amount, subtotal = 0.0, 0.0
#     required_fields = ['items', 'success_url', 'cancel_url']
#     if not all(field in payload for field in required_fields):
#         raise BadRequest("Missing required fields")
#     if payload.get('promo_code_db_id'):
#         PromotionService.validate_promo_code(payload['promo_code_db_id'])
#     today_is = convert_datetime_to_timezone_date(datetime.utcnow())
#     cart_details = (
#         SC.query
#         .join(PD, PD.id == SC.pricing_id)
#         .with_entities(
#             PD.title, PD.unit_price, SC.quantity, SC.state, 
#             SC.pricing_id, SC.id, PD.description, PD.completed
#             )
#         .filter(
#             SC.id.in_(list(payload['items'].keys()))
#             ).all()
#         )
#     print(f"card details--> {cart_details}")
#     cart_temp_ids_with_pricing_id = {'user_info': g.user}
#     items = []
#     invoice_data =  {
#         'bill_to': {'name': g.user['name'], 'agency_name': g.user['agency_name'], 'email': g.user['email'], 'phone': g.user['phone']},
#         "from": COMPANY_INVOICE_ADDRESS, 
#         "purchase_date": today_is.strftime("%B %d, %Y"), 
#         'commission': STRIPE_COMMISSION_FEE * 100,
#         "items": [],
#         "payment_details": {}
#         }
#     stripe_amount_will_be = 0
#     for item in cart_details:
#         subtotal += item.unit_price * item.quantity
#         invoice_data['items'].append(
#             {
#                 "title": item.title,
#                 "description": f"{item.description} {'(completed)' if item.completed else '(Incomplete)'}",
#                 'unit_price': item.unit_price, 
#                 'quantity': item.quantity,
#                 'state': item.state,
#                 'subtotal': item.unit_price * item.quantity
#             }
#         )
#         unit_amount_with_commision = ((item.unit_price * STRIPE_COMMISSION_FEE + item.unit_price) * 100)
#         print(f"arun {unit_amount_with_commision}")
#         print(subtotal)
#         print(item.unit_price, STRIPE_COMMISSION_FEE, item.unit_price)
#         items.append({
#             'price_data': {
#                 'currency': 'usd', 
#                 'unit_amount': int(unit_amount_with_commision),
#                 'product_data': {
#                     'name': f"{item.title} ({item.state})"
#                     }
#                 },
#             'quantity': item.quantity
#             } 
#         )
#         stripe_amount_will_be += int(unit_amount_with_commision)
#         print("items is")
#         print(items[-1])
#         print(f"stripe_amount_will_be {stripe_amount_will_be}")
#         total_amount += unit_amount_with_commision * item.quantity
#         cart_temp_ids_with_pricing_id[
#                 f"reserve_cart_{item.pricing_id}_{payload['items'][str(item.id)]['shopping_cart_temp_id']}"] = str(item.id)
#     invoice_data['subtotal'] = subtotal
#     # #TODO apply discount code calculation
#     total_amount = total_amount / 100
#     if redis_obj.get(f"mp_order_{g.user['stripe_customer_id']}_{stripe_amount_will_be}"):
#         raise BadRequest("sorry same amount has been tried few minutes back, so please wait for 2 minutes and try again")
    
#     print(f"Now total_amount is {total_amount}")
#     total_amount = int(total_amount* 100) / 100.0
#     print(f"new total is: {total_amount}")
#     if total_amount  != payload['total_amount']:
#         print(f"count mismatch total_amount={total_amount} subtotal={subtotal} {payload} {invoice_data['items']}")
#         # raise BadRequest("Sorry an issue occurred with the total price, please try again later")
#     invoice_data['total_amount'] = payload['total_amount']
#     total_orders_today = MOS.query.filter(MOS.user_id == g.user['id'], MOS.local_purchase_date == today_is, MOS.payment_status == 'succeeded').count()
#     campaign_name = f"M{today_is.strftime('%m%d%Y')}"
#     if total_orders_today > 0:
#         if total_orders_today > 0:
#             campaign_name = f"{campaign_name}({total_orders_today})"
#     order_obj = CRUD.create(
#         MOS,
#         dict(
#             user_id=g.user['id'], 
#             subtotal = subtotal,
#             promo_code_db_id=payload.get('promo_code_db_id'),
#             # original_price=payload['amount_subtotal'], 
#             total_amount=payload['total_amount'],
#             # TODO discounted_price logic is wrong and promo_code_db_idhas to be done
#             # discounted_price=payload['total_amount'] if payload['total_amount'] < round(subtotal + (subtotal * STRIPE_COMMISSION_FEE)) else None,
#             local_purchase_date=today_is,
#             campaign_name=campaign_name
#             )
#         )
#     print(f"order_obj is {order_obj}")
#     cart_temp_ids_with_pricing_id |= {'campaign_name': campaign_name, 'order_id': str(order_obj.id)}
#     print(f"cart_temp_ids_with_pricing_id is {cart_temp_ids_with_pricing_id}")
#     add_redis_ttl_data(f"mp_order_{g.user['stripe_customer_id']}_{stripe_amount_will_be}", hours=.033, data=json.dumps(cart_temp_ids_with_pricing_id))
#     stripe_obj = StripeService()
#     print(f"itemns {items}")
#     result = stripe_obj.create_checkout_session_marketplace(
#         items=items,
#         success_url=payload['success_url'],
#         cancel_url=payload['cancel_url'],
#         # application_fee_amount= int(payload['amount_subtotal'] * STRIPE_COMMISSION_FEE * 100),
#         # connected_account_id = Config_is.SELLER_STRIPE_ACCOUNT_ID,
#         stripe_promotion_id=payload.get('stripe_promotion_id')
#     )
#     session_response = stripe_obj.get_session_status(result['session_id'])
#     order_obj.stripe_payment_id = session_response['payment_intent_id']
#     invoice_data['invoice_number'] =  f"INV-{today_is.strftime('%Y%m%d')}-{order_obj.invoice_id}" 
#     result['invoice_number'] = invoice_data['invoice_number']
#     order_obj.invoice_data = invoice_data
#     print('arun test')
#     print(invoice_data)
#     print(result)
#     # if order_obj.stripe_payment_id:
#     #     add_redis_ttl_data(f"mp_stripe_payment_id{g.user['stripe_customer_id']}_{int(payload['amount_subtotal'])}", hours=0.033, data=order_obj.stripe_payment_id)

#     # if result.get('amount_subtotal'):
#     #     order_obj.original_price = result.get('amount_subtotal')
#     # if result.get('amount_total'):
#     #     order_obj.discounted_price = result.get('amount_total')
#     # amount_received= via webhook
#     # SC.query.filter(SC.id.in_(list(payload['items'].keys()))).update({'is_active': False})     
#     CRUD.db_commit()
#     return result
    
def marketplace_direct_purchase_checkout(payload: Dict):

    """
    - Marektplace direct purchase with immmediate debit checkout
    """
    print('marketplace_direct_purchase_checkout')
    print(payload)
    total_amount, subtotal = 0.0, 0.0
    required_fields = ['items', 'success_url', 'cancel_url']
    if not all(field in payload for field in required_fields):
        raise BadRequest("Missing required fields")
    if payload.get('promo_code_db_id'):
        PromotionService.validate_promo_code(payload['promo_code_db_id'])
    today_is = convert_datetime_to_timezone_date(datetime.utcnow())
    cart_details = (
        SC.query
        .join(PD, PD.id == SC.pricing_id)
        .with_entities(
            PD.title, PD.unit_price, SC.quantity, SC.state, 
            SC.pricing_id, SC.id, PD.description, PD.completed
            )
        .filter(
            SC.id.in_(list(payload['items'].keys()))
            ).all()
        )
    print(f"card details--> {cart_details}")
    cart_temp_ids_with_pricing_id = {'user_info': g.user}
    items = []
    invoice_data =  {
        'bill_to': {'name': g.user['name'], 'agency_name': g.user['agency_name'], 'email': g.user['email'], 'phone': g.user['phone']},
        "from": COMPANY_INVOICE_ADDRESS, 
        "purchase_date": today_is.strftime("%B %d, %Y"), 
        'commission': STRIPE_COMMISSION_FEE * 100,
        "items": [],
        "payment_details": {}
        }
    print(f"Invocie {payload['total_amount']}")
    description = ''
    for item in cart_details:
        subtotal += (item.unit_price * item.quantity)
        invoice_data['items'].append(
            {
                "title": item.title,
                "description": f"{item.description} {'(completed)' if item.completed else '(Incomplete)'}",
                'unit_price': item.unit_price, 
                'quantity': item.quantity,
                'state': item.state,
                'subtotal': item.unit_price * item.quantity
            }
        )
        print(f"Item--- {payload['total_amount']}")
    
        description += f"{item.description} ({item.quantity} {'completed' if item.completed else 'Incomplete'})\n"
        print(subtotal)
        cart_temp_ids_with_pricing_id[
                f"reserve_cart_{item.pricing_id}_{payload['items'][str(item.id)]['shopping_cart_temp_id']}"] = str(item.id)
    print(f"out llopp {payload['total_amount']}")
    invoice_data['subtotal'] = subtotal
    # #TODO apply discount code calculation
    commission = subtotal * STRIPE_COMMISSION_FEE
    commission = float((Decimal(str(commission)) * 100).to_integral_value() / 100)
    total_amount = subtotal + commission
    print(f"TT {payload['total_amount']}")
    if total_amount  != payload['total_amount'] and abs(total_amount - payload['total_amount']) > 1:
        print("abs")
        print(f"count mismatch total_amount={total_amount} subtotal={subtotal} {payload} {invoice_data['items']}")
        raise BadRequest("Sorry an issue occurred with the total price, please try again later")
    if redis_obj.get(f"mp_order_{g.user['stripe_customer_id']}_{payload['total_amount']}"):
        raise BadRequest("sorry same amount has been tried few minutes back, so please wait for 20 minutes and try again")
    invoice_data['total_amount'] = payload['total_amount']
    print(f"INVOICE {payload['total_amount']}")
    total_orders_today = MOS.query.filter(MOS.user_id == g.user['id'], MOS.local_purchase_date == today_is, MOS.payment_status == 'succeeded').count()
    campaign_name = f"M{today_is.strftime('%m%d%Y')}"
    if total_orders_today > 0:
        if total_orders_today > 0:
            campaign_name = f"{campaign_name}({total_orders_today})"
    order_obj = CRUD.create(
        MOS,
        dict(
            user_id=g.user['id'], 
            subtotal = subtotal,
            promo_code_db_id=payload.get('promo_code_db_id'),
            # original_price=payload['amount_subtotal'], 
            total_amount=payload['total_amount'],
            # TODO discounted_price logic is wrong and promo_code_db_idhas to be done
            # discounted_price=payload['total_amount'] if payload['total_amount'] < round(subtotal + (subtotal * STRIPE_COMMISSION_FEE)) else None,
            local_purchase_date=today_is,
            campaign_name=campaign_name
            )
        )
    print(f"order_obj is {order_obj}")
    cart_temp_ids_with_pricing_id |= {'campaign_name': campaign_name, 'order_id': str(order_obj.id)}
    print(f"cart_temp_ids_with_pricing_id is {cart_temp_ids_with_pricing_id}")
    stripe_obj = StripeService()
    print(f"foo1 {payload['total_amount']}")
    stripe_total_amount = int(Decimal(str(payload['total_amount'])) * Decimal(str(100)))
    items = [{
        'price_data': {
            'currency': 'usd', 
            'unit_amount': stripe_total_amount,
            'product_data': {
                'name': description
                }
                },
                'quantity': 1
            }
        ]    
    print(f'items is {items}')
    result = stripe_obj.create_checkout_session_marketplace(
        items=items,
        success_url=payload['success_url'],
        cancel_url=payload['cancel_url'],
        # application_fee_amount= int(payload['amount_subtotal'] * STRIPE_COMMISSION_FEE * 100),
        # connected_account_id = Config_is.SELLER_STRIPE_ACCOUNT_ID,
        stripe_promotion_id=payload.get('stripe_promotion_id')
    )
    session_response = stripe_obj.get_session_status(result['session_id'])
    order_obj.stripe_payment_id = session_response['payment_intent_id']
    invoice_data['invoice_number'] =  f"INV-{today_is.strftime('%Y%m%d')}-{order_obj.invoice_id}" 
    result['invoice_number'] = invoice_data['invoice_number']
    order_obj.invoice_data = invoice_data
    print('arun test')
    print(invoice_data)
    print(result)   
    CRUD.db_commit()
    add_redis_ttl_data(f"mp_order_{g.user['stripe_customer_id']}_{stripe_total_amount}", hours=.33, data=json.dumps(cart_temp_ids_with_pricing_id))
    return result
    
