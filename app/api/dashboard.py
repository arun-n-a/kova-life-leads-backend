
from flask import (
    Blueprint, jsonify, request, g
    )

from app.api.auth import tokenAuth
from app.services.dashboard import (
    get_leads_sold_complete_incomplete_count,
    get_dashboard_recent_leads, 
    get_dashboard_count, get_dashboard_lead_flow
    )


dashboard_bp = Blueprint('dashboard', __name__)



@dashboard_bp.route("/recent-leads", methods=["GET"])
@tokenAuth.login_required
def view_dashboard_recent_leads():
    """
    Get Recent Leads for Dashboard
    ---
    tags:
      - Dashboard
    summary: Get recently added leads
    description: |
      Returns a flat list of the most recent leads accessible by the logged‑in user.
      Each lead object includes full name, status, location (`state`, `city`), and call time.

      This endpoint powers the **recent leads** section on the dashboard.

    parameters:
      - name: limit
        in: query
        required: false
        schema:
          type: integer
          minimum: 1
        description: Maximum number of recent leads to return (defaults to 100).
        example: 250

    security:
      - BearerAuth: []

    responses:
      200:
        description: Recent leads list retrieved successfully. # Slightly more descriptive
        content:
          application/json:
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
                        example: "TEST12345"
                        description: Unique identifier for the mortgage lead.
                      full_name:
                        type: string
                        example: "Test User"
                        description: Full name of the lead.
                      state:
                        type: string
                        example: "TX"
                        description: Two-letter state code of the lead's location.
                      city:
                        type: string
                        example: "Dallas"
                        description: City of the lead's location.
                      call_in_date_time:
                        type: string
                        format: date-time # Keep if backend can provide RFC3339, otherwise consider removing or adding custom format description.
                        example: "2025-06-30T04:46:39Z" # Updated example for RFC3339 compliance
                        description: The date and time the lead was called in.
                      lead_status:
                        type: string
                        example: "NEW"
                        description: Current status of the lead (e.g., NEW, CONTACTED, etc.).
                      completed:
                        type: boolean
                        example: true
                        description: Indicates if the lead processing is completed.
                message:
                  type: string
                  example: "Success" # Consistent capitalization
                status:
                  type: integer
                  example: 200
      401:
        description: Unauthorized - Bearer token is missing or invalid.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Authentication required."
                status:
                  type: integer
                  example: 401
      500:
        description: Internal Server Error.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "An unexpected error occurred."
                status:
                  type: integer
                  example: 500
    """
    result = get_dashboard_recent_leads(int(request.args.get("limit", 100)))
    return jsonify(
        {"data": result, "message": "Success", "status": 200} # Consistent capitalization
    )


@dashboard_bp.route("/count/<int:category>", methods=["GET"])
@tokenAuth.login_required
def dashboard_lead_count(category):
    """
    Get count for dashboard
    ---
    tags:
      - Dashboard
    summary: Retrieve dashboard lead counts
    description: |
      This endpoint provides various lead counts for the dashboard based on a specific category,
      including completed, incomplete, and sold leads.

    parameters:
      - name: category
        in: path
        type: integer
        required: true
        description: The lead category to filter counts by (currently only 1 is supported).

      # IMPORTANT: Removed 'limit' parameter as the Python function does not use it.
      # If your function *should* use it, add 'limit' to the get_leads_sold_complete_incomplete_count call.

    security:
      - BearerAuth: []

    responses:
      200:
        description: Successfully retrieved dashboard counts.
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    completed:
                        type: integer
                        example: 100
                        description: Total number of completed leads.
                    incomplete:
                        type: integer
                        example: 100
                        description: Total number of incomplete leads.
                    sold:
                        type: integer
                        example: 5
                        description: Total number of sold leads.
                message:
                  type: string
                  example: "Success"
                status:
                  type: integer
                  example: 200
      401:
        description: Unauthorized - Bearer token is missing or invalid.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Authentication required."
                status:
                  type: integer
                  example: 401
      500:
        description: Internal Server Error.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "An unexpected error occurred."
                status:
                  type: integer
                  example: 500
    """
    result = get_leads_sold_complete_incomplete_count(category)
    return jsonify({"data": result, "message": "Success", "status": 200})


@dashboard_bp.route("/total-count", methods =['GET'])
@tokenAuth.login_required
def dashboard_count_status():
    """
    ---
    tags:
      - Dashboard
    summary: Get total count data
    description: Returns total count data for the dashboard based on the provided time zone.
    security:
      - BearerAuth: []
    parameters:
      - name: time_zone
        in: query
        required: true
        description: Time zone string (e.g., Asia/Kolkata, UTC, etc.)
        schema:
          type: string
    responses:
      200:
        description: Successful response with total count data
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: object
                  description: The actual dashboard count data
                message:
                  type: string
                  example: Success
                status:
                  type: integer
                  example: 200
    """
    data = get_dashboard_count(request.args.get('time_zone'))
    return jsonify({"data": data, "message": "Success", "status": 200})


@dashboard_bp.route("/lead-flow-trends", methods = ['GET'])
@tokenAuth.login_required
def dashboard_lead_flow():
    data = get_dashboard_lead_flow(request.args.get('time_zone'))
    return jsonify({"data": data, "message": "Success", "status": 200})