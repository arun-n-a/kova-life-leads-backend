"""API Endpoints related to purchases."""

from flask import request, jsonify, Blueprint

from app.services.auth import admin_authorizer
from app.api.auth import tokenAuth
from app.services.orders import (
    admin_listing_marketplace_invoices,
    admin_listing_subscription_invoices,
    download_admin_listing_marketplace_invoices,
    download_admin_listing_subscription_invoices
    )
order_bp = Blueprint("orders", __name__)

@order_bp.route("/admin/summary", methods=['GET'])
@tokenAuth.login_required
@admin_authorizer
def admin_list_subscription_and_mp_invoices():
    """
    Admin listing of subscription invoices and marketplace invoices
    ---
    tags:
      - Orders
    summary: Get admin subscription order summary and marketplace orders
    description: >
      Returns paginated subscriptions/marketplace invoice records for all users.  
      Filters available: payment status, date range, and user name.
    parameters:
      - name: is_marketplace
        in: query
        type: integer
        required: true
        default: 0
        description: "Zero indicates subscription and 1 indicates Marketplace orders"
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
    if request.args.get('is_marketplace') == "0":
        data = admin_listing_subscription_invoices(
            int(request.args.get('page', 1)), 
            int(request.args.get('per_page', 1)),
            request.args.get('payment_status'), 
            request.args.get('start_date'), 
            request.args.get('end_date'),
            request.args.get('name')
            )
    else:
        data = admin_listing_marketplace_invoices(
            int(request.args.get('page', 1)), 
            int(request.args.get('per_page', 1)),
            request.args.get('payment_status'), 
            request.args.get('start_date'), 
            request.args.get('end_date'),
            request.args.get('name')
            )
    return jsonify({'data': data[0], 'message': 'Success', 'status': 200, 'pagination': data[1]})


@order_bp.route('/download/admin/summary', methods = ['GET'])
@tokenAuth.login_required
@admin_authorizer
def download_admin_list_invoices():
    """
    Download Admin Order Summary
    ---
    tags:
      - Orders
    summary: Download subscription/marketplace order summary (Admin only)
    description: "Returns a list of all subscription/marketplace orders for admin users with optional filters"

    parameters:
      - name: is_marketplace
        in: query
        type: integer
        required: true
        default: 0
        description: "Zero indicates subscription and 1 indicates Marketplace orders"
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
              type: object
              properties:
                orders:
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
                new_file_name:
                  type: string
                  example: "download_2025_09_02.csv"
    """
    if request.args.get('is_marketplace') == '0':
        data = download_admin_listing_subscription_invoices(
            request.args.get('payment_status'), 
            request.args.get('start_date'), 
            request.args.get('end_date'), 
            request.args.get('name')
            )
    else:
        data = download_admin_listing_marketplace_invoices(
            request.args.get('payment_status'), 
            request.args.get('start_date'), 
            request.args.get('end_date'), 
            request.args.get('name')
        )
    return jsonify({'data': {"orders": data[0], "new_file_name": data[1]}, 'message': 'Success', 'status': 200})
