from flask import Blueprint, request, jsonify

from app.api.auth import tokenAuth
from app.models import StripeWebhook
from app.services.stripe_service import (
    # alert_new_subscription_purchase_to_admin,
    getting_session_status_subscription,
    getting_session_status_marketplace,
    StripeService
    )
from app.services.stripe_subscriptions import (
    subscription_webhook,
    process_cancelled_subscription, 
    create_subscription_with_possible_initial_charge,
    )
from app.services.stripe_payment import (
    stripe_payment_status_update,
    marketplace_direct_purchase_checkout,
    update_payment_failed_status
    )
from app.services.crud import CRUD
    
from app.services.custom_errors import *
from config import Config_is

stripe_bp = Blueprint('stripe', __name__)


@stripe_bp.route('/create-checkout-session/<id_>', methods=['POST'])
@tokenAuth.login_required
def creating_subscription_checkout_session(id_):
    """
    Create a new Stripe subscription checkout session
    ---
    tags:
      - Stripe
    summary: Create subscription checkout session
    description: >
      Creates a subscription checkout session for the user.  
      - If today is **Wednesday before 11:59 PM IST**, the user is charged immediately and a subscription is created.  
      - Otherwise, the subscription is scheduled to begin on the **next Wednesday at 6:00 PM IST**.

      The session will be created using Stripe.  
      User’s chosen states will also be saved.

    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: id_
        required: true
        type: string
        description: Internal subscription ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - price_id
            - stripe_product_id
            - success_url
            - cancel_url
            - item
          properties:
            price_id:
              type: string
              description: Stripe price ID for the plan
              example: price_1NqK3vFzAbCdEf
            stripe_product_id:
              type: string
              description: Stripe product ID
              example: prod_Market123
            success_url:
              type: string
              description: URL to redirect on successful checkout
              example: https://yourapp.com/success
            cancel_url:
              type: string
              description: URL to redirect if checkout is canceled
              example: https://yourapp.com/cancel
            stripe_promotion_id:
              type: string
              description: Optional Stripe promotion ID
              example: promo_12345
            item:
              type: object
              required:
                - name
                - quantity
                - total_amount
                - pricing_id
                - states
              properties:
                name:
                  type: string
                  description: Name of the plan or item
                  example: Weekly Mailer Plan
                quantity:
                  type: integer
                  description: Quantity of the plan
                  example: 1
                total_amount:
                  type: number
                  description: Total amount to be charged
                  example: 499.00
                pricing_id:
                  type: string
                  description: Internal pricing ID reference
                  example: abc123
                states:
                  type: array
                  description: List of selected states for the subscription
                  items:
                    type: string
                  example: ["Texas", "California", "Florida"]
    responses:
      200:
        description: Session created or subscription scheduled successfully
        schema:
          type: object
          properties:
            data:
              type: object
              description: Result data including session or subscription info
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    print(f"creating_subscription_checkout_session payload = {request.json}")
    result = create_subscription_with_possible_initial_charge(id_, request.json)
    print(f"create session result {result}")
    return jsonify({'data': result, 'message': 'success', 'status': 200})


@stripe_bp.route('/session/<session_id>', methods=['GET'])
@tokenAuth.login_required
def fetch_session_status_subscription(session_id):
    """
    Get Stripe checkout session status
    ---
    tags:
      - Stripe
    summary: Fetch Stripe checkout session status and cache invoice ID if present
    description: >
      Retrieves the current status of a Stripe checkout session using the session ID.  
      If an `invoice_id` is present in the response, it is cached using Redis with a short TTL.  
      This endpoint is primarily used to validate whether the payment has been completed and to fetch associated metadata like `subscription_id`, `payment_intent_id`, etc.
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: session_id
        required: true
        type: string
        description: Stripe session ID
    responses:
      200:
        description: Checkout session status fetched successfully
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                session_id:
                  type: string
                  example: cs_test_a1b2c3d4e5
                payment_status:
                  type: string
                  example: paid
                subscription_id:
                  type: string
                  example: sub_1Nxyz456AbCDef
                payment_intent_id:
                  type: string
                  example: pi_3Xyz123abc456
                invoice_id:
                  type: string
                  example: in_1ZYX123abc456
                amount_total:
                  type: number
                  example: 49900
                currency:
                  type: string
                  example: usd
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    print('session get called')
    result = getting_session_status_subscription(session_id)
    return jsonify({'data': result, 'message': 'success', 'status': 200})



@stripe_bp.route('/marketplace-create-checkout-session', methods=['POST'])
@tokenAuth.login_required
def creating_checkout_session_marketplace():
    """
    Direct marketplace checkout for multiple pricing items
    ---
    tags:
      - Marketplace
    summary: Marketplace direct checkout
    description: >
      Creates a Stripe checkout session for selected marketplace cart items.  
      Also applies discounts and stores order tracking data using Redis.  
      Handles pricing validation, quantity, and optional promo code.

    consumes:
      - application/json
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - items
            - success_url
            - cancel_url
            - amount_subtotal
            - total_amount
          properties:
            items:
              type: object
              additionalProperties:
                type: object
                properties:
                  shopping_cart_temp_id:
                    type: string
                    example: temp_cart_abc123
              example:
                "1": { "shopping_cart_temp_id": "temp_1" }
                "3": { "shopping_cart_temp_id": "temp_2" }
            success_url:
              type: string
              example: https://yourapp.com/success
            cancel_url:
              type: string
              example: https://yourapp.com/cancel
            amount_subtotal:
              type: number
              example: 100.00
            total_amount:
              type: number
              example: 106.00
            promo_code_db_id:
              type: string
              example: abc-promo-001
            stripe_promotion_id:
              type: string
              example: promo_1Nzx88abCdEf
    responses:
      200:
        description: Stripe checkout session created
        schema:
          type: object
          properties:
            session_id:
              type: string
              example: cs_test_a1b2c3d4e5
            amount_total:
              type: number
              example: 106.00
            amount_subtotal:
              type: number
              example: 100.00
            url:
              type: string
              example: https://checkout.stripe.com/pay/cs_test_...
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    print(f"create_marketplae_checkout_session payload = {request.json}")
    result = marketplace_direct_purchase_checkout(request.json)
    print(f"create session result {result}")
    return jsonify({'data': result, 'message': 'success', 'status': 200})


@stripe_bp.route('/marketplace-session/<session_id>', methods=['GET'])
@tokenAuth.login_required
def fetch_session_status_marketplace(session_id):
    """
    Get Stripe marketplace checkout session status
    ---
    tags:
      - Stripe
    summary: Retrieve Stripe marketplace checkout session status
    description: >
      Retrieves the status and metadata of a Stripe checkout session initiated through the marketplace.  
      This endpoint is used to validate payment completion and capture session-related details.  
      Unlike standard subscriptions, no invoice data is cached in Redis.

    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: session_id
        required: true
        type: string
        description: Stripe session ID to retrieve
    responses:
      200:
        description: Marketplace checkout session status retrieved successfully
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                session_id:
                  type: string
                  example: cs_test_a1b2c3d4e5
                payment_status:
                  type: string
                  example: paid
                payment_intent_id:
                  type: string
                  example: pi_3XYZ987abc123
                amount_total:
                  type: number
                  example: 9900
                currency:
                  type: string
                  example: usd
                customer_email:
                  type: string
                  example: buyer@example.com
                mode:
                  type: string
                  example: payment
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
      401:
        description: Unauthorized – invalid or missing authentication token
      404:
        description: Session not found
    """
    print('getting_session_status_marketplace get called')
    result = getting_session_status_marketplace(session_id)
    return jsonify({'data': result, 'message': 'success', 'status': 200})


@stripe_bp.route('/webhook/payment_status', methods=['POST'])
def stripe_webhook_validation():
    """
    Stripe Webhook Listener
    ---
    tags:
      - Stripe
    summary: Handle Stripe webhook events
    description: |
      Handles incoming webhook events from Stripe such as `payment_intent.succeeded`, `customer.subscription.created`, `customer.subscription.deleted`, etc.
    consumes:
      - application/json
    parameters:
      - in: header
        name: Stripe-Signature
        required: true
        type: string
        description: Webhook signature for verification
      - in: body
        name: payload
        required: true
        schema:
          type: object
          properties:
            id:
              type: string
              example: evt_1AB2CD3EF4
            type:
              type: string
              example: customer.subscription.created
            data:
              type: object
              properties:
                object:
                  type: object
                  description: Stripe event data
    responses:
      200:
        description: Webhook handled successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    hook = CRUD.create(StripeWebhook, {'payload': request.json, 'event': request.json.get('type')})
    # if 'invoice' in request.json.get('type'):
    #         return jsonify({'message': 'success', 'status': 200})
    status = StripeService().webhook_validation(
        request.headers['STRIPE_SIGNATURE'],  
        request.data
        )
    if status:
        if request.json.get('type') in ('payment_intent.payment_failed', 'payment_intent.canceled'):
          update_payment_failed_status(request.json)
        elif 'payment_intent'  in request.json.get('type'):
            print(f'Payload {request.json}')          
            stripe_payment_status_update(request.json)
            # alert_new_subscription_purchase_to_admin(request.json['data']['object']['id'], request.json['data']['object']['customer'], request.json['type'])
        elif request.json['type'] == 'customer.subscription.deleted':
            process_cancelled_subscription(request.json, hook.id)
        elif 'subscription' in request.json['type']:
            if 'customer.subscription.updated' != request.json['type']:
                subscription_webhook(str(hook.id), request.json)
            # if 'customer.subscription.created' in request.json['type']:
            #     subscription_webhook(str(hook.id), request.json)
    return jsonify({'message': 'success', 'status': 200})

# @stripe_bp.route('/cards/save', methods=['POST'])
# @tokenAuth.login_required
# def save_card():
#     """Save a new payment method"""
#     result = StripeService().save_card(
#         request.json.get('payment_method_id')
#         )
#     return jsonify({'data': result, 'message': 'success', 'status': 200})

# @stripe_bp.route('/cards/<payment_method_id>', methods=['DELETE'])
# @tokenAuth.login_required
# def delete_card(payment_method_id):
#     """Delete a saved payment method"""
#     result = StripeService().delete_card(payment_method_id)
#     return jsonify({'data': result, 'message': 'success', 'status': 200})

# @stripe_bp.route('/cards/list', methods=['GET'])
# @tokenAuth.login_required
# def list_cards():
#     """List all saved payment methods"""
#     result = StripeService().list_cards()
#     return jsonify({'data': result, 'message': 'success', 'status': 200})

# @stripe_bp.route('/cards/<payment_method_id>/primary', methods=['POST'])
# @tokenAuth.login_required
# def set_primary_card(payment_method_id):
#     """Set a payment method as primary"""
#     result = StripeService().set_primary_card(payment_method_id)
#     return jsonify({'data': result, 'message': 'success', 'status': 200})

# @stripe_bp.route('/payment-intent', methods=['POST'])
# @tokenAuth.login_required
# def create_payment_intent():
#     """Create a payment intent"""
#     if 'amount' not in request.json:
#         raise BadRequest("Amount is required")
#     result = StripeService().create_payment_intent(
#         user_id=request.user.id,
#         amount=request.json['amount'],
#         payment_method_id=request.json.get('payment_method_id')
#     )
#     return jsonify({'data': result, 'message': 'success', 'status': 200})

# @stripe_bp.route('/payment-intent/<payment_intent_id>/confirm', methods=['POST'])
# @tokenAuth.login_required
# def process_payment(payment_intent_id):
#     """Process a payment"""
#     result = StripeService().process_payment(
#         payment_intent_id=payment_intent_id,
#         payment_method_id=request.json.get('payment_method_id')
#     )
#     return jsonify({'data': result, 'message': 'success', 'status': 200})


# @stripe_bp.route('/webhook/payment_status', methods=['POST'])
# def stripe_webhook_validation():
#     print(request.headers.get('stripe-signature'))
#     print(f'Payload {request.json}')
#     from app.models import StripeWebhook
#     from app.services.crud import CRUD
#     hook = CRUD.create(StripeWebhook, {'payload': request.json, 'event': request.json.get('type')})
#     if 'invoice' in request.json.get('type'):
#             return jsonify({'message': 'success', 'status': 200})
#     status = StripeService().webhook_validation(
#         request.headers['STRIPE_SIGNATURE'],  
#         request.data
#         )
#     print(f"hook is {hook}")
#     if status:
#         if 'payment_intent' in request.json.get('type'):
#             stripe_payment_status_update(request.json['data']['object']['id'], request.json['type'])
#             alert_new_subscription_purchase_to_admin(request.json['data']['object']['id'], request.json['data']['object']['customer'], request.json['type'])
#         elif 'subscription' in request.json['type']:
#             subscription_webhook(str(hook.id), request.json)
#     """
#     EVENTS

# subscription_schedule.released
# subscription_schedule.updated
# subscription_schedule.created
# subscription_schedule.completed
# subscription_schedule.expiring
# subscription_schedule.aborted
# subscription_schedule.canceled
# customer.subscription.updated
# customer.subscription.resumed
# customer.subscription.paused
# customer.subscription.deleted
# customer.subscription.created
# payment_intent.canceled
# payment_intent.payment_failed
# payment_intent.requires_action
# payment_intent.succeeded
#     """
#     return jsonify({'message': 'success', 'status': 200})




# @stripe_bp.route('/create-price', methods=['POST'])
# @tokenAuth.login_required
# def create_product_price():
#     """Create a new product with pricing in Stripe"""
#     if not request.json:
#         raise BadRequest("Request body is required")
#     required_fields = ['product_name', 'amount']
#     if not all(field in request.json for field in required_fields):
#         raise BadRequest("Required fields: product_name, amount")
#     result = StripeService().create_price(
#         product_name=request.json['product_name'],
#         amount=request.json['amount'],
#         currency=request.json.get('currency', 'usd'),
#         recurring=request.json.get('recurring')
#     )
#     return jsonify({'data': result, 'message': 'success', 'status': 200})