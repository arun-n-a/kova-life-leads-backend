from flask import Blueprint, jsonify, request

from app.api.auth import tokenAuth
from app.services.auth import admin_authorizer
from app.services.stripe_subscriptions import (
    paginated_subscriptions_listing, 
    get_my_current_subscription,
    updating_subscribed_states,
    listing_subscription_invoices,
    handle_subscription_cancellation, 
    list_previous_subscriptions,
    )
from app.services.orders import (
    download_admin_listing_subscription_invoices,
    admin_listing_subscription_invoices
    )

stripe_subscriptions_bp = Blueprint('Stripe Subscriptions', __name__) 


@stripe_subscriptions_bp.route("/paginated/<user_id>", methods=['GET'])
@tokenAuth.login_required
def subscription_list_paginated(user_id):
    """
    Get paginated subscriptions for a user
    ---
    tags:
      - Stripe Subscriptions
    summary: Retrieve paginated list of subscriptions
    description: >
      Returns a paginated list of subscriptions for the specified user.  
      Admins (role_id=1) can access all users' data.  
      Other users can only access their own subscriptions.

    security:
      - BearerAuth: []

    parameters:
      - in: path
        name: user_id
        required: true
        type: string
        description: ID of the user

      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number for pagination

      - in: query
        name: per_page
        type: integer
        required: false
        default: 1
        description: Number of results per page

      - in: query
        name: time_zone
        type: string
        required: false
        description: Time zone to convert created_at timestamps

      - in: query
        name: status
        type: string
        required: false
        description: Optional status filter for subscriptions

    responses:
      200:
        description: Paginated list of subscriptions
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  name:
                    type: string
                  stripe_subscription_id:
                    type: string
                  discounted_price:
                    type: number
                  status:
                    type: string
                  started_at:
                    type: string
                    format: date-time
                  cancel_at:
                    type: string
                    format: date-time
                  cancelled_at:
                    type: string
                    format: date-time
                  cancelation_reason:
                    type: string
                  acknowledgment_id:
                    type: string
                  states_chosen:
                    type: array
                    items:
                      type: string
                  created_at:
                    type: string
                    format: date-time
            pagination:
              type: object
              properties:
                total:
                  type: integer
                current_page:
                  type: integer
                per_page:
                  type: integer
                length:
                  type: integer
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200

      204:
        description: No subscriptions found

      403:
        description: Forbidden – user not authorized
    """
    data = paginated_subscriptions_listing(
        user_id, int(request.args.get('page', 1)), 
        int(request.args.get('per_page', 1)),
        request.args.get('time_zone') ,
        request.args.get('status'))
    return jsonify({'data': data[0], 'message': 'Success', 'status': 200, 'pagination': data[1]})

@stripe_subscriptions_bp.route("/cancellation/<subscription_id>", methods=['POST'])
@tokenAuth.login_required
def cancel_subcription(subscription_id):
    """
    Cancel a subscription
    ---
    tags:
      - Stripe Subscriptions
    summary: Cancel a Stripe subscription
    description: >
      Cancels an active Stripe subscription associated with the user.  
      Requires the user's own subscription ID and a cancellation reason.

    security:
      - BearerAuth: []

    parameters:
      - in: path
        name: subscription_id
        required: true
        type: string
        description: Internal subscription ID to be canceled

      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - cancelation_reason
          properties:
            cancelation_reason:
              type: string
              description: Reason for cancelling the subscription
              example: No longer needed

    responses:
      200:
        description: Subscription canceled successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Subscription cancelled successfully
            status_code:
              type: integer
              example: 200

    """
    handle_subscription_cancellation(subscription_id, request.json.get("cancelation_reason"))
    return jsonify({"message": "Subscription cancellation request has been submitted please wait for a while","status": 200})



@stripe_subscriptions_bp.route("/current/<user_id>", methods=['GET'])
@tokenAuth.login_required
def getting_current_subscription(user_id):
    """
    Get current subscription details
    ---
    tags:
      - Stripe Subscriptions
    summary: Get the latest subscription info for a user
    description: >
      Returns the latest active subscription for a user.  
      If there is no active subscription, it returns the most recent one.  
      Only the user or an admin (role_id=1) is allowed to access this data.

    security:
      - BearerAuth: []

    parameters:
      - in: path
        name: user_id
        required: true
        type: string
        description: ID of the user whose subscription should be fetched

    responses:
      200:
        description: Latest subscription information
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                status:
                  type: string
                  example: active
                accepted_terms_and_conditions:
                  type: boolean
                  example: true
                name:
                  type: string
                  example: Weekly Mailer
                discounted_price:
                  type: number
                  example: 499.00
                states_chosen:
                  type: array
                  items:
                    type: string
                  example: ["Texas", "Florida"]
                started_at:
                  type: string
                  example: 08-01-2025
                stripe_product_id:
                  type: string
                  example: prod_ABC123
                db_subscription_id:
                  type: string
                  example: 12345
                db_pricing_id:
                  type: string
                  example: 54321
                title:
                  type: string
                  example: Basic Weekly Plan
                net_price:
                  type: number
                  example: 499.00
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200

    """
    data = get_my_current_subscription(user_id)
    return jsonify({'data': data, 'message': 'Success', 'status': 200})


@stripe_subscriptions_bp.route("/chosen-states/<subscription_id>", methods=['PATCH'])
@tokenAuth.login_required
def update_subscribed_states(subscription_id):
    """
    Update chosen states for a subscription
    ---
    tags:
      - Stripe Subscriptions
    summary: Update states in a user's subscription
    description: >
      Updates the list of chosen states for a specific subscription.  
      Allowed only if the number of states is between 3 and 10.  
      Updates both the user's and subscription's records.

    security:
      - BearerAuth: []

    parameters:
      - in: path
        name: subscription_id
        required: true
        type: string
        description: ID of the subscription to update

      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - states_chosen
          properties:
            states_chosen:
              type: array
              minItems: 3
              maxItems: 10
              description: List of 3–10 states to associate with the subscription
              items:
                type: string
              example: ["Texas", "California", "Florida"]

    responses:
      200:
        description: States updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200

    """
    updating_subscribed_states(subscription_id, request.json['states_chosen'])
    return jsonify({'message': 'Success', 'status': 200})


@stripe_subscriptions_bp.route("/order-summary", methods=['GET'])
@tokenAuth.login_required
def list_subscription_invoices():
    """
    List subscription invoice orders
    ---
    tags:
      - Stripe Subscriptions
    summary: Retrieve paginated list of subscription invoice orders
    description: >
      Returns a paginated list of past subscription invoice orders for the logged-in user.  
      This includes information such as payment status, description, and selected states.

    security:
      - BearerAuth: []

    parameters:
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number for pagination

      - in: query
        name: per_page
        type: integer
        required: false
        default: 1
        description: Number of results per page

    responses:
      200:
        description: Paginated list of subscription invoice orders
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                    example: "order_123"
                  description:
                    type: string
                    example: Weekly Mailer Plan
                  created_at:
                    type: string
                    format: date-time
                    example: 2025-07-11T18:30:00Z
                  amount_received:
                    type: number
                    example: 499.00
                  payment_status:
                    type: string
                    example: paid
                  states_chosen:
                    type: array
                    items:
                      type: string
                    example: ["Texas", "California"]
            pagination:
              type: object
              properties:
                total:
                  type: integer
                  example: 20
                current_page:
                  type: integer
                  example: 1
                per_page:
                  type: integer
                  example: 5
                length:
                  type: integer
                  example: 5
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
    """
    data = listing_subscription_invoices(
        int(request.args.get('page', 1)), 
        int(request.args.get('per_page', 1))
        )
    return jsonify({'data': data[0], 'message': 'Success', 'status': 200, 'pagination': data[1]})


@stripe_subscriptions_bp.route("", methods=['GET'])
@tokenAuth.login_required
@admin_authorizer
def admin_list_subscription_invoices():
    """
    Admin listing of subscription invoices
    ---
    tags:
      - Subscriptions
    summary: Get admin subscription order summary
    description: >
      Returns paginated subscription invoice records for all users.  
      Filters available: payment status, date range, and user name.
    parameters:
      - name: page
        in: query
        type: integer
        required: false
        default: 1
        description: Page number
      - name: per_page
        in: query
        type: integer
        required: false
        default: 10
        description: Items per page
      - name: payment_status
        in: query
        type: string
        required: false
        description: "Filter by payment status (e.g., paid, failed)"
      - name: start_date
        in: query
        type: string
        format: date
        required: false
        description: "Filter by start date (format: mm-dd-yyyy)"
      - name: end_date
        in: query
        type: string
        format: date
        required: false
        description: "Filter by end date (format: mm-dd-yyyy)"
      - name: name
        in: query
        type: string
        required: false
        description: "Filter by user name (partial match)"
    responses:
      200:
        description: Successful response with paginated invoice list
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 123
                  description:
                    type: string
                  created_at:
                    type: string
                  amount_received:
                    type: number
                  payment_status:
                    type: string
                  states_chosen:
                    type: array
                    items:
                      type: string
                  user_id:
                    type: integer
                  name:
                    type: string
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
            pagination:
              type: object
              properties:
                total:
                  type: integer
                current_page:
                  type: integer
                per_page:
                  type: integer
                length:
                  type: integer

    """
    data = admin_listing_subscription_invoices(
        int(request.args.get('page', 1)), 
        int(request.args.get('per_page', 1)),
        request.args.get('payment_status'), 
        request.args.get('start_date'), 
        request.args.get('end_date'),
        request.args.get('name')
        )
    return jsonify({'data': data[0], 'message': 'Success', 'status': 200, 'pagination': data[1]})


@stripe_subscriptions_bp.route('/download/admin/order-summary', methods = ['GET'])
@tokenAuth.login_required
@admin_authorizer
def download_admin_list_subscription_invoices():
    """
    Download Admin Order Summary
    ---
    tags:
      - Subscriptions
    summary: Download subscription order summary (Admin only)
    description: "Returns a list of all subscription orders for admin users with optional filters"

    parameters:
      - name: payment_status
        in: query
        type: string
        required: false
        description: "Filter by payment status (e.g., paid, pending)"

      - name: start_date
        in: query
        type: string
        format: date
        required: false
        description: "Filter by start date (format: mm-dd-yyyy)"

      - name: end_date
        in: query
        type: string
        format: date
        required: false
        description: "Filter by end date (format: mm-dd-yyyy)"

      - name: name
        in: query
        type: string
        required: false
        description: "Filter by customer name"

    responses:
      200:
        description: Order data retrieved successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
            data:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 101
                  description:
                    type: string
                    example: Subscription to Weekly Plan
                  created_at:
                    type: string
                    example: 08-01-2025
                  amount_received:
                    type: number
                    example: 99.99
                  payment_status:
                    type: string
                    example: paid
                  states_chosen:
                    type: array
                    items:
                      type: string
                  user_id:
                    type: integer
                    example: 42
                  name:
                    type: string
                    example: John Doe
    """
    data = download_admin_listing_subscription_invoices(request.args.get('payment_status'), request.args.get('start_date'), 
        request.args.get('end_date'), request.args.get('name'))
    return jsonify({'data': {"orders": data[0], "new_file_name": data[1]}, 'message': 'Success', 'status': 200})
  

@stripe_subscriptions_bp.route('/previous/paginated', methods = ['GET'])
@tokenAuth.login_required
def previous_subscription_list_paginated():
    """
    Get paginated list of previous (inactive) subscriptions.

    ---
    tags:
      - Stripe Subscriptions
    parameters:
      - name: page
        in: query
        type: integer
        required: false
        description: Page number for pagination (default is 1)
      - name: per_page
        in: query
        type: integer
        required: false
        description: Number of items per page (default is 10)
      - name: time_zone
        in: query
        type: string
        required: false
        description: Time zone string (e.g., Asia/Kolkata)
      - name: user_id
        in: query
        type: string
        required: false
        description: Optional user ID to fetch another user's subscriptions (admin only)
    security:
      - BearerAuth: []
    responses:
      200:
        description: Successful response with paginated subscription data
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  name:
                    type: string
                  status:
                    type: string
                  started_at:
                    type: string
                  cancel_at:
                    type: string
                    nullable: true
                  cancelation_reason:
                    type: string
                    nullable: true
                  stripe_subscription_id:
                    type: string
            pagination:
              type: object
              properties:
                total:
                  type: integer
                current_page:
                  type: integer
                per_page:
                  type: integer
                length:
                  type: integer
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    data, pagination = list_previous_subscriptions(
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10)), 
        request.args.get('time_zone'), 
        request.args.get('user_id')
        )
    return jsonify(
        {"data": data, "pagination": pagination, "message": "success", "status": 200}
    )

