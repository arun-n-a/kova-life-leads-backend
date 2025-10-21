from flask import Blueprint, jsonify, request

from app.api.auth import tokenAuth
from app.services.auth import admin_authorizer
from app.services.revenue_view import get_revenue_by_plan

revenue_bp = Blueprint('Revenue View', __name__) 


@revenue_bp.route('/revenue-by-plan', methods=['GET'])
@tokenAuth.login_required
@admin_authorizer
def revenue_by_plan():
    """
    Get Revenue by Plan

    Retrieves total orders count and revenue grouped by plan for the specified date range.

    ---
    tags:
      - Revenue
    summary: Get Revenue by Plan
    description: >
      Returns total number of orders and revenue amount per subscription plan 
      between the specified start and end dates. Requires admin authorization.

    security:
      - BearerAuth: []

    parameters:
      - name: start_date
        in: query
        required: false
        type: string
        format: date
        example: "2025-07-01"
        description: Start date in YYYY-MM-DD format

      - name: end_date
        in: query
        required: false
        type: string
        format: date
        example: "2025-07-03"
        description: End date in YYYY-MM-DD format

    responses:
      200:
        description: Revenue grouped by plan
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  plan:
                    type: string
                    example: "5000 MAILERS WEEKLY"
                  orders_count:
                    type: integer
                    example: 1
                  total_revenue:
                    type: number
                    format: float
                    example: 750.0
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    result = get_revenue_by_plan(request.args.get('start_date'), request.args.get('end_date'))
    return jsonify({"data": result, "message": "success", "status": 200})


