import json
from typing import (
    Dict, List, Optional, Union, Tuple
)
from datetime import (
    datetime, timedelta, time
    )

import stripe
from flask import (
    g, render_template, request
    )

from app.services.custom_errors import *
from app.models import (
    StripeCustomerSubscription as SCS,
    User, PaymentMethod as PM,
    PromotionCode as PC,
    SubscriptionOrderSummary as SOS,
    PricingDetail as PD
    
    )
from app.services.crud import CRUD
from app.services.utils import (
    add_redis_ttl_data,
    convert_datetime_to_timezone_date,
    get_current_date_time,
    utc_to_timezone_conversion
    )
from app.services.sendgrid_email import SendgridEmailSending
from app import db, redis_obj
from config import Config_is
from constants import STRIPE_COMMISSION_FEE


def getting_session_status_subscription(session_id: str) -> Dict:
    result = StripeService().get_session_status(session_id)
    if result.get('invoice_id'):
        add_redis_ttl_data(result['subscription_id'], .29, result['invoice_id'])
    print(f"get_session_status ->{result}")
    return result


def getting_session_status_marketplace(session_id: str) -> Dict:
    result = StripeService().get_session_status(session_id)
    # if result.get('invoice_id'):
        # add_redis_ttl_data(result['subscription_id'], .25, result['invoice_id'])
    print(f"getting_session_status_marketplace ->{result}")
    return result
    


# def stripe_payment_status_update(id_: str, payment_status: Optional[str], session_id: str = None, order_id: str = None) -> bool:
#     print(f'stripe_payment_status_update {id_}')
#     order_obj = None
#     if session_id:
#         order_obj = OS.query.filter_by(session_id=session_id).first()
#     elif order_id:
#         order_obj = OS.query.get(order_id)
#     elif id_.startswith('pi_'):
#         order_obj = OS.query.filter_by(payment_id=id_).first()
#     elif id_.startswith('sub_'):
#         order_obj = OS.query.filter(OS.subscription_id == id_).order_by(OS.created_at.desc()).first()
#     if not order_obj:
#         user_obj = User.query.filter_by(stripe_customer_id=request.json['data']['object']['customer']).with_entities(User.id).first()
#         if  id_.startswith('pi_'):
#             order_obj = OS.query.filter(
#                 OS.total_amount == request.json['data']['object']['amount']/100,
#                 OS.user_id == user_obj.id, OS.payment_id == None
#                 ).order_by(OS.created_at.desc()).first()
#     print(f"order_obj status {order_obj} {payment_status}")
#     if order_obj:
#         if payment_status:
#             order_obj.payment_status =  payment_status.split('.')[-1]
#         if id_.startswith("pi_") and not order_obj.payment_id:
#             order_obj.payment_id = id_
#         elif id_.startswith('sub_'):
#             if not order_obj.subscription_id:
#                 order_obj.subscription_id = id_
#             SCS.query.filter(SCS.stripe_subscription_id == id_, SCS.acknowledgment_id == None).update({'acknowledgment_id': order_obj.id}) 
#         CRUD.db_commit()
#         return True
#     return False


# def alert_new_subscription_purchase_to_admin(payment_id: str, stripe_customer_id: str, payment_status: Optional[str]) -> bool:
#     user_obj = User.query.with_entities(User.id, User.email, User.name).filter(User.stripe_customer_id == stripe_customer_id).first()
#     if not user_obj:
#         SendgridEmailSending(
#         Config_is.DEVELOPERS_EMAIL_ADDRESS, 
#         f"{Config_is.ENVIRONMENT} Webhooks invalid Customer {stripe_customer_id} - {Config_is.APP_NAME}", 
#         f"payload = {request.json}"
#         ).send_email_without_logs()
#         return True
#     order_obj = SOS.query.outerjoin(PC, PC.id == SOS.promo_code_db_id).filter(
#         SOS.payment_id == payment_id).with_entities(
#             SOS.payload, SOS.total_amount, SOS.alert_sent, 
#             SOS.sent_admin_alert, SOS.admin_alert_status, 
#             SOS.subtotal_amount, SOS.id, PC.code).first()
#     if not order_obj:
#         order_obj = SOS.query.outerjoin(PC, PC.id == SOS.promo_code_db_id).filter(
#             SOS.user_id == user_obj.id, SOS.payment_id == None, 
#             SOS.total_amount == request.json['data']['object']['amount']
#             ).with_entities(
#                 SOS.payload, SOS.total_amount, SOS.alert_sent, 
#                 SOS.sent_admin_alert, SOS.admin_alert_status,
#                 SOS.subtotal_amount, SOS.id, PC.code).order_by(
#                     SOS.created_at.desc()
#                     ).first()
#         print('webhook no order_obj matched')
#     if not order_obj:
#         SendgridEmailSending(
#             Config_is.DEVELOPERS_EMAIL_ADDRESS, 
#         f"🛒 {Config_is.ENVIRONMENT} Webhooks invalid orderSummary {payment_id} - {Config_is.APP_NAME}", 
#         f"payload = {request.json}"
#         ).send_email_without_logs()
#         return True
#     if payment_status in (order_obj.admin_alert_status or ''):
#         return True
#     stored_status = payment_status + (f', {order_obj.admin_alert_status}' if order_obj.admin_alert_status else  '')
#     CRUD.update(OS, {'id': order_obj.id}, {'admin_alert_status':  stored_status.strip(), 'sent_admin_alert': True})
#     items = order_obj.payload.get('items') or [order_obj.payload.get('item')] 
#     to_emails = [{'user_id': str(u.id), 'email': u.email} for u in User.query.filter(
#         User.role_id == 1, User.is_active  == True, User.registered == True
#         ).with_entities(User.id, User.email).all()]
#     # admin alert
#     email_body = render_template("admin_alert_purchase.html", 
#                         user_name=user_obj.name, 
#                         total_amount=order_obj.total_amount,
#                         payment_id=payment_id,
#                         payment_status=payment_status, 
#                         subtotal_amount=order_obj.subtotal_amount,
#                         promo_code=order_obj.code,
#                         items= [
#                             {
#                                 'quantity': item['lead_quantity'], 
#                                 'name': item['name'],
#                                 'state': ', '.join(item['states'])
#                                 } 
#                                 for item in items
#                             ]
#                         )
#     SendgridEmailSending(
#         to_emails, 
#         f"🛒 New Purchase Alert - {Config_is.APP_NAME} {payment_id}", 
#         email_body, 6
#         ).send_email()
#     # user email
#     email_body = render_template("admin_alert_purchase.html", 
#                         name=user_obj.name,
#                         user_name=user_obj.name, 
#                         total_amount=order_obj.total_amount,
#                         payment_id=payment_id,
#                         payment_status=payment_status, 
#                         subtotal_amount=order_obj.subtotal_amount,
#                         promo_code=order_obj.code,
#                         items= [
#                             {
#                                 'quantity': item['lead_quantity'], 
#                                 'name': item['name'],
#                                 'state': ', '.join(item['states'])
#                                 } 
#                                 for item in items
#                             ]
#                         )
#     SendgridEmailSending(
#         [{'user_id': str(user_obj.id), 'email': user_obj.email}], 
#         f"🛒 New Purchase Alert - {Config_is.APP_NAME} {payment_id}", 
#         email_body, 6
#         ).send_email()
#     return True


class StripeService:
    """Handle Stripe payment operations"""
    def __init__(self):
        stripe.api_key = Config_is.STRIPE_SECRET_KEY
        self.webhook_secret = Config_is.STRIPE_WEBHOOK_SECRET
    def create_customer(self, user_obj  : User) -> str:
        """
        Create a new Stripe customer for a user
        """
        try:
            customer = stripe.Customer.create(
                email=user_obj.email,
                name=user_obj.name,
                metadata={
                    'user_id': str(user_obj.id)
                }
            )
            return customer.id
        except stripe.error.StripeError as e:
            print(f"Failed to create Stripe customer: {e}")
            raise InternalError("Failed to create customer account")
    # def get_customer(self, user_id: str) -> Dict:
    #     """
    #     Get Stripe customer information
    #     """
    #     try:
    #         user_obj = User.query.get(user_id)
    #         if not user_obj.stripe_customer_id:
    #             # Create customer if doesn't exist
    #             return self.create_customer(user_obj)
    #         customer = stripe.Customer.retrieve(user_obj.stripe_customer_id)
    #         # '{\'id\': \'cus_SIpakkvG93ps6T\', \'object\': \'customer\', \'address\': None, \'balance\': 0, \'created\': 1747123866, \'currency\': None, \'default_source\': None, \'delinquent\': False, \'description\': None, \'discount\': None, \'email\': \'smijith@abacies.com\', \'invoice_prefix\': \'G98EJJNT\', \'invoice_settings\': <InvoiceSettings at 0x7f5aeab938e0> JSON: {\n  "custom_fields": null,\n  "default_payment_method": null,\n  "footer": null,\n  "rendering_options": null\n}, \'livemode\': False, \'metadata\': <StripeObject at 0x7f5aeac99180> JSON: {\n  "user_id": "74f2800a-3715-4e9b-943f-06701729f916"\n}, \'name\': \'Smijith\', \'next_invoice_sequence\': 1, \'phone\': None, \'preferred_locales\': [], \'shipping\': None, \'tax_exempt\': \'none\', \'test_clock\': None}'
    #         return {
    #             'customer_id': customer.id,
    #             'email': customer.email,
    #             'name': customer.name,
    #             'default_payment_method': customer.invoice_settings.default_payment_method,
    #             'created': customer.created
    #         }
    #     except stripe.error.StripeError as e:
    #         print(f"Failed to retrieve Stripe customer: {e}")
    #         raise InternalError("Failed to get customer information")
    def update_customer(self, stripe_customer_id: str, name: str) -> bool:
        """
        Update Stripe customer information
        """
        try:
            stripe.Customer.modify(
                stripe_customer_id,
                name=name
                )
            return True
        except stripe.error.StripeError as e:
            raise InternalError("Failed to update customer information")
    # def delete_customer(self, stripe_customer_id: str) -> bool:
    #     """
    #     Delete Stripe customer
    #     """
    #     try:
    #         stripe.Customer.delete(stripe_customer_id)
    #         return True
    #     except stripe.error.StripeError as e:
    #         print(f"Failed to delete Stripe customer: {e}")
    #         raise InternalError("Failed to delete customer account")
    
    def create_checkout_session_marketplace(self, items: List[Dict], success_url: str, cancel_url: str,  stripe_promotion_id: Optional[str] = None) -> Dict:
        """
        Create a Stripe checkout session for direct payment in marketplace
        """
        #application_fee_amount: int, connected_account_id: str, 
        try:
            session = stripe.checkout.Session.create(
                customer=g.user['stripe_customer_id'],
                payment_method_types=['card'],
                line_items=items,
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                # discounts=[{'promotion_code': stripe_promotion_id}] if stripe_promotion_id else []
                # payment_intent_data={
                #     "application_fee_amount": application_fee_amount,
                #     "transfer_data": {
                #         "destination": connected_account_id}
                #     }
                )
            print(f"create_checkout_session_marketplace {session}")
            return {
                'session_id': session.id,
                'url': session.url,
                'amount_total': session.amount_total / 100,
                "amount_subtotal": session.amount_subtotal / 100
            }
        except stripe.error.StripeError as e:
            print(f"create_checkout_session_marketplace failed: {e} {items}")
            raise InternalError("Failed to create checkout session")

    def create_subscription_checkout_session(self, items: List[Dict], success_url: str, cancel_url: str, subscription_id: str, stripe_promotion_id: Optional[str]) -> Dict:
        """
        Create a Stripe checkout session
        """
        # connected_account_id: str,
        try:
            session = stripe.checkout.Session.create(
                customer=g.user['stripe_customer_id'],
                payment_method_types=['card'],
                line_items=items,
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=subscription_id,
                metadata={
                    'user_id': g.user['id']
                    },
                discounts=[{'promotion_code': stripe_promotion_id}] if stripe_promotion_id else []
                # subscription_data={
                # "application_fee_percent": int(STRIPE_COMMISSION_FEE * 100),
                # "transfer_data": {
                #     "destination": connected_account_id
                # }
                # }
                )         
            print(f"create session {session}")
            return {
                'session_id': session.id,
                'url': session.url,
                'amount_total': session.amount_total,
                "amount_subtotal": session.amount_subtotal,
            }
        except stripe.error.StripeError as e:
            print(f"Stripe checkout session creation failed: {e}")
            raise InternalError("Failed to create checkout session")
        
    # def create_subscription(self, items: List[Dict], utc_billing_cycle_anchor: datetime):
    #     try:
    #         subscription = stripe.Subscription.create(
    #             customer=g.user['stripe_customer_id'],
    #             items=items,
    #             billing_cycle_anchor=int(utc_billing_cycle_anchor.timestamp()),
    #             proration_behavior='none',
    #             payment_behavior='default_incomplete',  # Prevent immediate charge
    #             metadata={
    #                 'needs_immediate_charge': 'true',
    #                 'scheduled_charge_time': utc_billing_cycle_anchor.isoformat()
    #                 }
    #             )
    #         print(f'Create subscription -> {subscription}')
    #         return subscription
    #     except Exception as e:
    #         print(f"Subscription creation {e}")
    #         raise InternalError(f"Subscription creation has been failed please try again later")

    def create_future_subscription(self, total_amount: float, items: List, utc_billing_cycle_anchor: datetime, success_url: str, cancel_url: str):
        # connected_account_id: str 
        try:
            print(f'Stripe create_future_subscription')
            session = stripe.checkout.Session.create(
                customer=g.user['stripe_customer_id'],
                payment_method_types=['card'],
                line_items=items,
                mode='subscription',
                subscription_data={
                    'billing_cycle_anchor': int(utc_billing_cycle_anchor.timestamp()),
                    'proration_behavior': 'none'
                    # "application_fee_percent": int(STRIPE_COMMISSION_FEE * 100),
                    # "transfer_data": {
                    #     "destination": connected_account_id
                    # }
                },
                success_url=success_url,
                cancel_url=cancel_url
            )

            print(f"create_future_subscription--> {session}")
            return {
                'session_id': session.id,
                'url': session.url,
                'amount_total': (session.amount_total or total_amount * 100) /100,
                "amount_subtotal": (session.amount_subtotal or total_amount * 100) / 100 ,
            }
        except Exception as e:
            print(f"Subscription creation has been failed please try again later {e}")
            raise InternalError(f"Subscription creation has been failed please try again later {e}")
    def get_session_status(self, session_id: str) -> Dict:
        """Get status of a checkout session"""
        print('get_session_status')
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            print(f'Try sesssionf {session}')
            return {
                # 'order_id': order_id,
                'payment_intent_id': session.payment_intent,
                'invoice_id': session.invoice,
                'subscription_id': session.subscription,
                'payment_status': session.payment_status,
                'amount_total': session.amount_total/100,
                'customer_email': session.customer_email
                }
        except stripe.error.StripeError as e:
            print(f"Failed to retrieve session status: {e}")
            raise InternalError("Failed to get session status")
    def save_card(self, payment_method_id: str) -> Dict:
        """
        Save a payment method for a user
        """
        if not payment_method_id:
            raise BadRequest("Payment method ID is required")
        try:
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=g.user['stripe_customer_id']
                )
            stripe.Customer.modify(
                g.user['stripe_customer_id'],
                invoice_settings={
                    'default_payment_method': payment_method_id
                }
            )
            # CRUD.create(
            #     PM, dict(user_id=user_id, stripe_payment_method_id=payment_method_id, is_default=True))
            return {
                'payment_method_id': payment_method_id,
                'status': 'saved'
            }
        except stripe.error.StripeError as e:
            print(f"Failed to save card: {e}")
            raise InternalError("Failed to save payment method")
    def delete_card(self, payment_method_id: str) -> bool:
        """Delete a saved payment method"""
        try:
            stripe.PaymentMethod.detach(payment_method_id)
            return True
        except stripe.error.StripeError as e:
            print(f"Failed to delete card: {e}")
            raise InternalError("Failed to delete payment method")
    def list_cards(self) -> List[Dict]:
        """List all saved payment methods for a user"""
        # TODO: cannot get primary card key from list cards?
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=g.user['stripe_customer_id'],
                type='card'
            )
            print(payment_methods.data)
            return [{
                'id': pm.id,
                'card': {
                    'brand': pm.card.brand,
                    'last4': pm.card.last4,
                    'exp_month': pm.card.exp_month,
                    'exp_year': pm.card.exp_year
                },
                # 'is_default': pm.id == user_obj.default_payment_method_id
            } for pm in payment_methods.data]
        except stripe.error.StripeError as e:
            print(f"Failed to list cards: {e}")
            raise InternalError("Failed to list payment methods")
    def set_primary_card(self, payment_method_id: str) -> Dict:
        """
        Set a payment method as primary for a user
        """
        try:
            stripe.Customer.modify(
                g.user['stripe_customer_id'],
                invoice_settings={
                    'default_payment_method': payment_method_id
                }
            )
            return {
            'payment_method_id': payment_method_id,
            'status': 'set_as_primary'
        }
        except stripe.error.StripeError as e:
            print(f"Failed to set primary card: {e}")
            raise InternalError("Failed to set primary payment method")
    def webhook_validation(self, sig_header: str, raw_payload: object) -> bool:
        try:
            event = stripe.Webhook.construct_event(
                raw_payload, sig_header, Config_is.STRIPE_WEBHOOK_SECRET
                )
            print(f"Event is => {event}")
        except ValueError as e:
            print(f'value error {e}')
        except stripe.error.SignatureVerificationError as e:
            print(f'Signature error {e}')
        return True

    # def create_payment_intent(self, amount: int,
    #                           payment_method_id: Optional[str] = None) -> Dict:
    #     """
    #     Create a payment intent for a purchase
    #     """
    #     try:
    #         intent_data = {
    #             'amount': amount,
    #             'currency': 'usd',
    #             'customer': g.user['stripe_customer_id'],
    #             'metadata': {
    #                 'user_id': g.user['id']
    #             }
    #         }
    #         # If using saved card, attach it
    #         if payment_method_id:
    #             intent_data['payment_method'] = payment_method_id
    #             intent_data['off_session'] = True
    #             intent_data['confirm'] = True
    #         payment_intent = stripe.PaymentIntent.create(**intent_data)
    #         return {
    #             'client_secret': payment_intent.client_secret,
    #             'payment_intent_id': payment_intent.id,
    #             'requires_action': payment_intent.status == 'requires_action'
    #         }
    #     except stripe.error.StripeError as e:
    #         print(f"Failed to create payment intent: {e}")
    #         raise InternalError("Failed to process payment")
    # def process_payment(self, payment_intent_id: str, 
    #                 payment_method_id: Optional[str] = None) -> Dict:
    #     """
    #     Process a payment with either saved or new card
    #     Args:
    #         user_id: User ID
    #         payment_intent_id: Stripe payment intent ID
    #         payment_method_id: Optional new payment method ID
    #     """
    #     try:
    #         payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
    #         if payment_intent.status == 'succeeded':
    #             return {
    #                 'status': 'succeeded',
    #                 'payment_intent_id': payment_intent_id
    #             }

    #         # If using new card, confirm the payment
    #         if payment_method_id:
    #             payment_intent = stripe.PaymentIntent.confirm(
    #                 payment_intent_id,
    #                 payment_method=payment_method_id
    #             )

    #         return {
    #             'status': payment_intent.status,
    #             'client_secret': payment_intent.client_secret,
    #             'requires_action': payment_intent.status == 'requires_action'
    #         }

    #     except stripe.error.StripeError as e:
    #         print(f"Payment processing failed: {e}")
    #         raise InternalError("Failed to process payment")


    def create_product(self, data: Dict) -> int:
        """
        Create a Stripe product
        """
        try:
            product = stripe.Product.create(**data)
            return product.id
        except stripe.error.StripeError as e:
            print(f"Failed to create product: {e}")
            raise InternalError("Failed to create product")
        
    def product_update(self, product_id: str, data: Dict) -> bool:
        try:
            stripe.Product.modify(product_id, **data)
            return True
        except stripe.error.StripeError as e:
            print(f"Failed to create product: {e}")
            raise InternalError("Failed to create product")
    
    def deactivate_old_pricing(self, stripe_price_id: str) -> bool:
        try:
            stripe.Price.modify(stripe_price_id, active=False) 
            return True
        except stripe.error.StripeError as e:
            print(f"Failed to deactivate price: {e}")
            raise InternalError("Failed to deactivate price")

    def create_pricing(self, product_id: str, unit_amount: float, currency: str) -> int:
            # metadata: Dict, recurring: bool
            params = {
                "product": product_id,
                "unit_amount": int(unit_amount * 100),
                "currency": currency,
                "recurring": {"interval": "week"}
                # "metadata": metadata or {}
                }
            try:
                price = stripe.Price.create(**params)
                return price.id
            except stripe.error.StripeError as e:
                print(f"Failed to create price: {e}")
                raise InternalError("Failed to create price")
    
    def create_coupon(self, data: Dict) -> str:
        """
        Create a coupon in Stripe

        - duration:"once", "repeating","forever".
        - percent_off : Percentage discount (e.g., 25 for 25% off).
        - amount_off: Fixed discount amount (e.g., 500 for $5.00).
        - currency: if `amount_off` is used (e.g., "usd").
        - duration_in_months : Required if duration is "repeating".
        - id : Optional. A custom coupon ID.(eg:nRO9bq9Z)
        - max_redemptions : Max number of times this coupon can be redeemed.
        - redeem_by : A Unix timestamp for expiration.
        - name :  A name for internal or customer-facing use.
        - metadata :Key-value pairs for additional info.
        """
        try:
            coupon = stripe.Coupon.create(**data)
            return coupon.id
        except stripe.error.StripeError as e:
            print(f"Failed to create coupon: {e}")
            raise InternalError("Failed to create coupon")
        
    def retrieve_coupon(self, coupon_id: str) -> Dict:
        """
            Retrieve a Stripe coupon
        """
        try:
            return stripe.Coupon.retrieve(coupon_id)
        except stripe.error.StripeError as e:
            print(f"Failed to retrieve coupon: {e}")
            raise InternalError("Failed to retrieve coupon")
        
    def update_coupon(self, coupon_id: str, data: Dict) -> bool:
        """
            Update a Stripe coupon
            -coupon_id (str): The ID of the coupon to update(eg:nRO9bq9Z).
            -name: "Summer Promo Coupon"}
        """
        try:
            stripe.Coupon.modify(coupon_id, **data)
            return True
        except stripe.error.StripeError as e:
            print(f"Failed to update coupon: {e}")
            raise InternalError("Failed to update coupon")
        
    def delete_coupon(self, coupon_id: str) -> bool:
        """
            Delete a Stripe coupon
        """
        try:
            stripe.Coupon.delete(coupon_id)
            return True
        except stripe.error.StripeError as e:
            print(f"Failed to delete coupon: {e}")
            raise InternalError("Failed to delete coupon")
        
    def list_coupons(self, params: Dict) -> Dict:
        """
            List Stripe coupons
            limit: Number of coupons to return (default and max is 100).

         """
        try:
            return stripe.Coupon.list(**params)
        except stripe.error.StripeError as e:
            print(f"Failed to list coupon: {e}")
            raise InternalError("Failed to list coupon")


    # def pause_subscription(subscription_id):
    #     paused = stripe.Subscription.modify(
    #         subscription_id,
    #         pause_collection={'behavior': 'mark_uncollectible'}  # Or 'keep_as_draft' or 'void'
    #         )
    #     return paused
    # def cancel_at_period_end(subscription_id):
    #     updated = stripe.Subscription.modify(
    #         subscription_id,
    #         cancel_at_period_end=True
    #         )
    #     return updated
    # def cancel_subscription(subscription_id):
    #     canceled = stripe.Subscription.delete(subscription_id)
    #     return canceled
    # def list_subscriptions(customer_id):
    #     subscriptions = stripe.Subscription.list(customer=customer_id)
    #     return subscriptions


    def create_stripe_promotion(self, data: Dict) -> str:
        """
            Create a promotion code in Stripe
            - coupon : The ID of the coupon to attach to this promotion code.(eg: nRO9bq9Z)
            - code : The actual code to be used by customers.(eg: JUNE2025)
            - max_redemptions : Maximum number of times the promotion code can be redeemed.
            - expires_at : Timestamp when the promotion code expires.
            - active : Whether the promotion code is currently active.
        """
        try:
            promotion = stripe.PromotionCode.create(**data)
            return promotion
        except stripe.error.StripeError as e:
            print(f"Failed to create promotion : {e}")
            raise InternalError("Failed to create promotion")
        except stripe.error.InvalidRequestError as e:
            index = str(e).find(':') + 2
            raise BadRequest(str(e)[index:].strip())
    # def retrieve_stripe_promotion(self, promo_id: str) -> Dict:
    #     """
    #     Retrieve a promotion code from Stripe.
    #     -promo_id : The ID of the promotion code to retrieve.(eg: promo_1RVmLNHFuUbT6ZjVNBZVbLF8)
    #     """
    #     try:
    #         return stripe.PromotionCode.retrieve(promo_id)
    #     except stripe.error.StripeError as e:
    #         print(f"Failed to retrieve promotion code: {e}")
    #         raise InternalError("Failed to retrieve promotion code")

    def update_stripe_promotion(self, promo_id: str, data: Dict) -> bool:
        """
        Update a promotion code on Stripe.
        promo_id : The ID of the promotion code to update.
        data : Fields to update. Can include:
            - metadata (dict)
            - active (bool): To activate/deactivate the promotion.
        """
        try:
            stripe.PromotionCode.modify(promo_id, **data)
            return True
        except stripe.error.StripeError as e:
            print(f"Failed to update promotion: {e}")
            raise InternalError("Failed to update promotion")

    def delete_stripe_promotion(self, promo_id: str) -> bool:
        """
        Deactivate a promotion code in Stripe by setting 'active' to False.
        -promo_id: The ID of the promotion code to deactivate.
        -active: True/ False for deactivate the promotion code.
        """
        try:
            stripe.PromotionCode.modify(promo_id, active=False)
            return True
        except stripe.error.StripeError as e:
            print(f"Failed to delete promotion: {e}")
            raise BadRequest("Failed to delete promotion")

    # def create_stripe_subscription(customer_id: str, price_id: str, promo_code_id: str ) -> str
    #     try:
    #         subscription_params = {
    #             "customer": customer_id,
    #             "items": [{"price": price_id}],
    #         }
        
    #         if promo_code_id:
    #             subscription_params["discounts"] = [{"promotion_code": promo_code_id}]
        
    #         subscription = stripe.Subscription.create(**subscription_params)
    #         return subscription
    
    #     except stripe.error.StripeError as e:
    #         print(f"Stripe subscription creation failed: {e}")
    #         raise Exception("Failed to create subscription")
    

    def retrieve_stripe_subscription(self, subscription_id: str) -> Dict:
        """
        Retrieves a Stripe subscription and its applied discounts.
        - subscription_id: str (eg: sub_1RWHd5HFuUbT6ZjVZQ6fR3vF)
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id, expand=["discount", "items.data.price.product"] )
            return subscription
        except stripe.error.StripeError as e:
            print(f"Failed to retrieve subscription: {e}")
            raise InternalError("Failed to retrieve subscription")
        
    def update_stripe_subscription(self, subscription_id: str, data: Dict) -> bool:
        """
        Update a Stripe subscription. You can modify metadata, price, discounts, etc.(eg:sub_1RWHd5HFuUbT6ZjVZQ6fR3vF)
        """
        try:
            stripe.Subscription.modify(subscription_id, **data)
            return True
        except stripe.error.StripeError as e:
            print(f"Stripe subscription update failed: {e}")
            raise Exception("Failed to update subscription")
        
    def cancel_stripe_subscription(self, subscription_id: str) -> bool:
        """
        Cancel a Stripe subscription by ID.
        """
        try:
            stripe.Subscription.cancel(subscription_id)
            return True
        except stripe.error.StripeError as e:
            print(f"Stripe subscription cancellation failed: {e}")
            raise Exception("Failed to cancel subscription")
        
    def list_stripe_subscriptions(self, params: Dict) -> Dict:
        """
        List subscriptions from Stripe'.
        -params: Dictionary of optional query parameters (e.g., limit, status, starting_after, etc.)    """
        try:
            subscriptions = stripe.Subscription.list(**params)
            return [sub for sub in subscriptions.auto_paging_iter()]
        except stripe.error.StripeError as e:
            print(f"Failed to list subscriptions: {e}")
            raise Exception("Failed to list subscriptions")

    def retrieve_stripe_invoice(self, invoice_id: str) -> Dict:
        try:
            return stripe.Invoice.retrieve(invoice_id)
        except Exception as e:
            print(f"retrive invoice stripe : {e}")
            raise Exception("Failed to fetch invoice data")
    def deactivate_product(self, stripe_product_id: str) -> bool:
        try:
            stripe.Product.modify(stripe_product_id, active=False)
            return True
        except stripe.error.StripeError as e:
            print(f"Failed to deactivate product: {e}")
            raise InternalError("Failed to deactivate product")
    
    def retrieve_payment_intent(self, payment_intent_id: str):
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    
    def retrieve_payment_method(self, payment_method_id: str):
        return stripe.PaymentMethod.retrieve(payment_method_id) 
    