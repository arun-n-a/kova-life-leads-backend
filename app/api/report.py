

from flask import (
    Blueprint, jsonify, request, g
    )

from app.api.auth import tokenAuth
from app.services.report import ReportAndAnalytics
from app.services.auth import admin_authorizer

report_bp = Blueprint('Report and Analtics', __name__)



@report_bp.route("/state-wise-sold-and-calls-count", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def getting_state_wise_call_sold_count():
    """
    Get state-wise sold leads and call count between given dates.

    ---
    tags:
      - Reports
    parameters:
      - name: start_date
        in: query
        type: string
        required: true
        description: Start date in format MM-DD-YYYY (e.g., 07-01-2025)
      - name: end_date
        in: query
        type: string
        required: true
        description: End date in format MM-DD-YYYY (e.g., 07-10-2025)
    security:
      - BearerAuth: []
    responses:
      200:
        description: Successfully retrieved state-wise data
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
                    example: CA
                  sold_count:
                    type: integer
                    example: 45
                  calls_count:
                    type: integer
                    example: 120
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    data = ReportAndAnalytics(
        request.args.get('start_date'), 
        request.args.get('end_date')
        ).get_state_wise_call_sold_count()
    return jsonify(
        {"data": data, "message": "success", "status": 200}
    )

@report_bp.route("/status-based-count", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def getting_status_based_count():
    """
    Get status-based lead count between given dates.

    ---
    tags:
      - Reports
    parameters:
      - name: start_date
        in: query
        type: string
        required: true
        description: Start date in format MM-DD-YYYY (e.g., 07-01-2025)
      - name: end_date
        in: query
        type: string
        required: true
        description: End date in format MM-DD-YYYY (e.g., 07-10-2025)
    security:
      - BearerAuth: []
    responses:
      200:
        description: Successfully retrieved status-based lead count
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  status:
                    type: string
                    example: contacted
                  count:
                    type: integer
                    example: 42
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    data = ReportAndAnalytics(
        request.args.get('start_date'), 
        request.args.get('end_date')
        ).get_lead_status_based_count()
    return jsonify({"data": data, "message": "success", "status": 200})

@report_bp.route("/leads-and-sold-count", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def get_total_leads_and_sold_count():
    """
    Get total leads and sold counts between given dates.

    ---
    tags:
      - Reports
    parameters:
      - name: start_date
        in: query
        description: Start date in format MM-DD-YYYY (e.g., 07-01-2025)
        required: true
        schema:
          type: string
          example: 07-01-2025
      - name: end_date
        in: query
        description: End date in format MM-DD-YYYY (e.g., 07-31-2025)
        required: true
        schema:
          type: string
          example: 07-31-2025
    security:
      - BearerAuth: []
    responses:
      200:
        description: Successfully retrieved leads and sold counts
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    total_leads:
                      type: integer
                      example: 120
                    sold_count:
                      type: integer
                      example: 45
                message:
                  type: string
                  example: success
                status:
                  type: integer
                  example: 200
    """
    data = ReportAndAnalytics(
        request.args.get('start_date'), 
        request.args.get('end_date')
        ).getting_total_leads_and_sold_count()
    return jsonify({"data": data, "message": "success", "status": 200})
