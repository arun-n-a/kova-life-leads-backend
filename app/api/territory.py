from flask import (
    Blueprint, jsonify, request, g
    )

from app.api.auth import tokenAuth
from app.services.territory import (
    get_statewise_territory_leads_count,
    getting_total_and_sold_count,
    listing_assigned_leads_states,
    get_states_chosen_for_active_subscription
)


territory_bp = Blueprint('territory', __name__)



@territory_bp.route("/statewise/count/<int:category>", methods=["POST"])
@tokenAuth.login_required
def view_statewise_territory_leads_count_route(category):
    """
    ---
    tags:
      - Territory
    summary: Get Paginated State-wise Leads Count by Category
    description: >
      Returns a paginated list of lead counts for each state,
      including total, completed, incomplete, suppressed, and sold leads.
      This endpoint is currently supported only for lead `category` 1 (mailing).

    produces:
      - application/json

    security:
      - BearerAuth: []

    parameters:
      - name: category
        in: path
        type: integer
        required: true
        description: Lead category (only 1 is currently supported).
        example: 1
      - name: page
        in: query
        type: integer
        required: false
        default: 1
        minimum: 1
        description: The page number for pagination.
        example: 1
      - name: per_page
        in: query
        type: integer
        required: false
        default: 10
        minimum: 1
        description: The number of items to return per page.
        example: 10
      - in: body
        name: body
        required: true
        description: Request body containing the list of states to filter by.
        schema:
          type: object
          required:
            - states # Explicitly mark 'states' as required in the body
          properties:
            states:
              type: array
              items:
                type: string
                description: Two-letter state code (e.g., "AZ", "CA").
              example: ["AZ", "CA"]
              description: A list of state codes for which to retrieve data.
    responses:
      200:
        description: Successfully retrieved paginated state-wise lead counts.
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
                      state:
                        type: string
                        example: "CA"
                        description: Two-letter state code.
                      total: # Added 'total' as per description
                        type: integer
                        example: 100
                        description: Total leads in this state.
                      completed:
                        type: integer
                        example: 45
                        description: Number of completed leads in this state.
                      incomplete:
                        type: integer
                        example: 50
                        description: Number of incomplete leads in this state.
                      sold:
                        type: integer
                        example: 15
                        description: Number of sold leads in this state.
                      suppressed: # Added 'suppressed' as per description
                        type: integer
                        example: 5
                        description: Number of suppressed leads in this state.
                meta:
                  type: object
                  properties:
                    total_items: # Renamed 'total' to 'total_items' for clarity
                      type: integer
                      example: 100
                      description: Total number of items across all pages.
                    current_page:
                      type: integer
                      example: 1
                      description: The current page number being returned.
                    page_size: # Renamed 'length' to 'page_size' for clarity
                      type: integer
                      example: 10
                      description: Number of items on the current page.
                    per_page:
                      type: integer
                      example: 10
                      description: Maximum items configured per page.
                    total_pages: # Added 'total_pages' for complete pagination info
                      type: integer
                      example: 10
                      description: Total number of available pages.
                message:
                  type: string
                  example: "Success" # Consistent capitalization
                status:
                  type: integer
                  example: 200
    """
    result, pagination = get_statewise_territory_leads_count(
        int(category),
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10)),
        request.json.get('states'))
    return jsonify({
        "data": result,
        "pagination": pagination, # Assuming 'pagination' object matches the 'meta' schema
        "message": "Success", # Consistent capitalization
        "status": 200
    })

@territory_bp.route("/leads-states/list/<int:category>", methods=["GET"])
@tokenAuth.login_required
def list_leads_states(category):
    """
    Get all states in which the agent is having leads

    ---
    tags:
      - Territory
    summary: Get all states in which the agent is having leads
    description: >
      Returns the distinct states in which the agent is having leads.

    produces:
      - application/json

    security:
      - BearerAuth: []

    parameters:
      - name: category
        in: path
        type: integer
        required: true
        description: Lead category (only 1 is supported)
    responses:
      200:
        description: states as list if items in data key
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
    data = listing_assigned_leads_states(category)
    return jsonify({
        "data": data,
        "message": "success",
        "status": 200
    })

@territory_bp.route("/total-and-sold-count/<int:category>", methods=["POST"])
@tokenAuth.login_required
def get_total_and_sold_count(category):
    """
    Get total and sold lead counts by states
    ---
    tags:
      - Territory
    summary: Get total and sold lead counts by states
    description: Returns the total number of leads and the number of sold leads for the given category and list of states.
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: category
        in: path
        required: true
        schema:
          type: integer
        description: Lead category (only 1 is supported)
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              states:
                type: array
                items:
                  type: string
                example: ["AZ", "CA"]
    responses:
      200:
        description: Sold and total lead counts
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    total:
                      type: integer
                      example: 100
                    sold:
                      type: integer
                      example: 45
                message:
                  type: string
                  example: success
                status:
                  type: integer
                  example: 200
    """
    states = request.json.get("states", [])
    data = getting_total_and_sold_count(category, states)
    return jsonify({
        "data": data,
        "message": "success",
        "status": 200
    })



@territory_bp.route('/active/<int:category>', methods=['GET'])
@tokenAuth.login_required
def get_active_territories(category):
    """
    Get active territories for the current user filtered by category
    ---
    tags:
      - Territory
    summary: Get active states_chosen by category
    description: Returns the `states_chosen` field from the most recently modified active subscription for the logged-in user, filtered by the given category.
    parameters:
      - in: path
        name: category
        required: true
        schema:
          type: integer
        description: Category ID
    security:
      - BearerAuth: []
    responses:
      200:
        description: List of active states
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    type: string
                  example: ["CA", "TX"]
                message:
                  type: string
                  example: success
                status:
                  type: integer
                  example: 200
    """
    data = get_states_chosen_for_active_subscription(category)
    return jsonify({
        "data": data,
        "message": "success",
        "status": 200
    })

