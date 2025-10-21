from flask import (
    Blueprint, request, jsonify, g
    )

from app.api.auth import tokenAuth
from app.services.auth import admin_authorizer
from app.services.marketplace import (
    mailing_completed_incomplete_statewise_count_for_sale,
    specific_state_available_leads,
    listing_marketplace_orders,
    getting_leads_orders
    )
from app.services.custom_errors import Forbidden


marketplace_bp = Blueprint('Marketplace API', __name__)


@marketplace_bp.route("/completed-incomplete-for-sale-total-count/paginated", methods=["GET"])
@tokenAuth.login_required
def get_ml_completed_incomplete_statewise_count_for_sale():
    """
    Get mailing leads completed incomplete state-wise count for sale (paginated)

    ---
    tags:
      - Marketplace
    summary: Get completed incomplete state-wise counts of mailing leads available for sale
    description: >
        Returns a paginated list of states with counts of completed and incomplete leads available for sale.
        Only includes leads that:
        - Have not been assigned to the current agent.
        - Are not disabled, in checkout, or recently purchased.
        - Are older than 30 days and less than 2 years.

        The `states` parameter accepts a **comma-separated list** of US state abbreviations 
        (e.g., `CA,TX,NY`) to filter the results.

    parameters:
      - name: page
        in: query
        type: integer
        required: false
        default: 1
        description: Page number for pagination.
      - name: per_page
        in: query
        type: integer
        required: false
        default: 10
        description: Number of results per page.
      - name: states
        in: query
        type: string
        required: false
        description: >
          Comma-separated list of US state abbreviations to filter results. 
          Example: `CA,TX,NY`. If not provided, all states will be considered.

    security:
      - BearerAuth: []

    responses:
      200:
        description: A list of states with lead type counts (completed/incomplete).
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  state:
                    type: string
                    description: US state abbreviation.
                  completed:
                    type: integer
                    description: Number of completed leads in the state.
                  incomplete:
                    type: integer
                    description: Number of incomplete leads in the state.
            pagination:
              type: object
              properties:
                total:
                  type: integer
                current_page:
                  type: integer
                length:
                  type: integer
                per_page:
                  type: integer
            message:
              type: string
              example: Succes
            status:
              type: integer
              example: 200
    """
    data = mailing_completed_incomplete_statewise_count_for_sale(
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10)),
        request.args.get('states', None)
    )
    return jsonify({'data': data[0], 'pagination': data[1], 'message': 'Succes', 'status': 200})


@marketplace_bp.route("/completed-incomplete-for-sale-month-wise/<state>", methods=["GET"])
@tokenAuth.login_required
def get_specific_state_available_all_months_leads(state):
    """
    Get state-wise available completed leads grouped by age buckets (month-wise)

    ---
    tags:
      - Marketplace
    summary: Get completed/incomplete lead counts in a state bucketed by age (in months)
    description: >
        Returns the number of completed leads available for sale in the specified US state,
        grouped by how old the lead is (based on call-in date), using month-like age buckets.

        Bucket definitions:
        - 0: ≤ 30 days
        - 1: 31–60 days
        - 2: 61–90 days
        - 3: 91–180 days
        - 6: 181–280 days
        - 9: 281–730 days

        Leads must:
        - Be in the specified state
        - Not be assigned to the agent
        - Not be recently purchased, disabled, or in checkout
        - Be marked as available for sale (`can_sale = True`)

    parameters:
      - name: state
        in: path
        type: string
        required: true
        description: US state abbreviation (e.g., `CA`, `TX`, `NY`)

    security:
      - BearerAuth: []

    responses:
      200:
        description: Success. Returns a list of age-bucketed cmopleted/incomplete lead counts.
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  month:
                    type: integer
                    description: Age bucket of the lead.
                  completed:
                    type: integer
                    description: Count of completed leads in this age group.
                  incomplete:
                    type: integer
                    description: Count of incomplete leads in this age group.
            message:
              type: string
              example: Succes
            status:
              type: integer
              example: 200

    """
    data = specific_state_available_leads(state)
    return jsonify({'data': data, 'message': 'Succes', 'status': 200})

@marketplace_bp.route("/orders/<user_id>/paginated", methods=["GET"])
@tokenAuth.login_required
def marketplace_orders(user_id):
    """
    Retrieve paginated list of marketplace orders for a specific user.

    ---
    tags:
      - Marketplace 
    summary: Get paginated marketplace orders
    description: >
      Returns a paginated list of marketplace orders for a given user.
      Only accessible by corporate admins or the user themselves.

    parameters:
      - name: user_id
        in: path
        type: string
        required: true
        description: ID of the user whose orders are being requested.

      - name: page
        in: query
        type: integer
        required: false
        default: 1
        description: Page number for pagination.

      - name: per_page
        in: query
        type: integer
        required: false
        default: 10
        description: Number of records per page.

      - name: timezone
        in: query
        type: string
        required: true
        description: Timezone (e.g., UTC, Asia/Kolkata) for formatting order dates.

      - name: payment_status
        in: query
        type: string
        required: false
        description: Filter orders by payment status (e.g., succeeded, failed, pending).

    security:
      - BearerAuth: []

    responses:
      200:
        description: Successful response with paginated order data.
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
                  stripe_payment_id:
                    type: string
                  discounted_price:
                    type: number
                  amount_received:
                    type: number
                  payment_status:
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
                length:
                  type: integer
                per_page:
                  type: integer
            message:
              type: string
            status:
              type: integer
    """
    if user_id != g.user['id'] and g.user['role_id'] != 1:
        raise Forbidden()
    print(request.args)
    result, pagination = listing_marketplace_orders(
        user_id,
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10)),
        request.args.get("timezone"), request.args.get('payment_status'), request.args.get('order_id')
    )
    return jsonify({'data': result, 'pagination': pagination, 'message': 'success', 'status': 200})

@marketplace_bp.route("/leads-orders/<user_id>", methods = ["GET"])
@tokenAuth.login_required
def get_leads_orders(user_id):
    """
    Retrieve paginated lead orders for a specific user.

    ---
    tags:
      - Marketplace
    summary: Get lead orders by user
    description: >
      Returns a paginated list of lead orders associated with the given user. 
      Users can filter by `cart_item_id` to retrieve only specific cart-related leads.
      Only the user or an admin (role_id = 1) can access this data.

    parameters:
      - name: user_id
        in: path
        type: string
        required: true
        description: ID of the user whose lead orders are being requested.

      - name: page
        in: query
        type: integer
        required: false
        default: 1
        description: Page number for pagination.

      - name: per_page
        in: query
        type: integer
        required: false
        default: 10
        description: Number of records per page.

      - name: cart_item_id
        in: query
        type: string
        required: false
        description: Filter results by a specific cart item ID.

    security:
      - BearerAuth: []

    responses:
      200:
        description: Successful response with paginated lead order data.
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  mortgage_id:
                    type: string
                  full_name:
                    type: string
                  state:
                    type: string
                  city:
                    type: string
                  address:
                    type: string
                  zip:
                    type: string
                  first_name:
                    type: string
                  last_name:
                    type: string
                  lender_name:
                    type: string
                  loan_amount:
                    type: number
                  loan_date:
                    type: string
                    format: date
                  purchased_date:
                    type: string
                    format: date-time
                  call_in_date_time:
                    type: string
                    format: date-time
                  completed:
                    type: boolean
                  ivr_response:
                    type: string
                  ivr_logs:
                    type: string
                  assignee_id:
                    type: string
                  agent_id:
                    type: string
                  notes:
                    type: string
                  lead_status:
                    type: string
                  suppression_rejection_msg:
                    type: string
                  campaign_name:
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
            status:
              type: integer
    """
    result, pagination = getting_leads_orders(
        user_id,
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10)),
        request.args.get('order_id'),
        request.args.get('cart_item_id')
    )
    return jsonify({'data': result,  "pagination": pagination, 'message': 'success', 'status': 200})