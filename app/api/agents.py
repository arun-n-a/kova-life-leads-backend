"""API Endpoints related to Users."""

from flask import request, jsonify, Blueprint

from app.api.auth import tokenAuth
from app.services.custom_errors import *
from app.services.auth import admin_authorizer
from app.services.user import (
    admin_getting_total_leads_and_sold_count,
    list_agents_of_category_source,
    list_agents_for_assignment,
    list_agents_with_filter,
    getting_agents_count
)


agents_bp = Blueprint("agents", __name__)


@agents_bp.route("/filter", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def listing_agents_filter():
    """
    Filter Agents Listing

    Allows admin users to filter agents based on category and optionally by agent ID or name.

    ---
    tags:
      - Agents
    summary: Filter agents by category and name or ID
    description: >
      Returns a paginated list of agents filtered by `category_id` and optionally by `search`. 
      Requires admin authorization and JWT token (Bearer).

    security:
      - BearerAuth: []

    parameters:
      - name: category_id
        in: query
        type: integer
        required: false
        description: Category ID to filter agents by.

      - name: search
        in: query
        type: string
        required: false
        description: Agent ID (numeric) or partial/full name to filter.

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
        description: Number of items per page.

    responses:
      200:
        description: Success
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
                    example: 101
                  category:
                    type: string
                    example: Sales
                  source:
                    type: string
                    example: Online
                  user_id:
                    type: integer
                    example: 50
                  email:
                    type: string
                    example: agent@example.com
                  name:
                    type: string
                    example: Arun Kumar
                  phone:
                    type: string
                    example: "+91-9876543210"
            pagination:
              type: object
              properties:
                total:
                  type: integer
                  example: 25
                current_page:
                  type: integer
                  example: 1
                per_page:
                  type: integer
                  example: 10
                length:
                  type: integer
                  example: 10
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
    """
    data = list_agents_with_filter(
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10)),
        request.args.get("category_id"),
        request.args.get("search"),
        request.args.get("status")
        )
    return (
        jsonify(
            {
                "data": data[0],
                "pagination": data[1],
                "message": "Success",
                "status": 200,
            }
        ),
        200,
    )


@agents_bp.route("/<int:category>/source/<int:source_id>", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def listing_agents_of_category_source(category, source_id):
    """
    List Agents by Category and Source

    Returns a paginated list of agents filtered by category and source.

    ---
    tags:
      - Agents
    summary: List agents using category and source filter
    description: >
      Fetch agents based on a specific `category` and `source_id`.
      Requires admin authorization and a valid Bearer token.

    security:
      - BearerAuth: []

    parameters:
      - name: category
        in: path
        required: true
        type: integer
        description: ID of the category to filter agents.

      - name: source_id
        in: path
        required: true
        type: integer
        description: ID of the source to filter agents.

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
        description: Number of agents per page.

    responses:
      200:
        description: Success
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
                  name:
                    type: string
                    example: John Doe
            pagination:
              type: object
              properties:
                total:
                  type: integer
                  example: 25
                current_page:
                  type: integer
                  example: 1
                per_page:
                  type: integer
                  example: 10
                length:
                  type: integer
                  example: 10
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
    """
    data = list_agents_of_category_source(
        category,
        source_id,
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10)),
    )
    return jsonify({
                "data": data[0],
                "pagination": data[1],
                "message": "Success",
                "status": 200,
            }
            )


@agents_bp.route("/for_assignment", methods=["POST"])
@tokenAuth.login_required
def listing_agents_for_assignment():
    """
    List Agents for Assignment

    Returns a paginated list of agents filtered by category and optionally by name, agent ID, or source.

    ---
    tags:
      - Agents
    summary: List agents for assignment
    description: >
      Returns agents engaged in the specified category. Can optionally filter by `source_id`, `agent_id`, or agent `name`.
      Requires authentication via Bearer token.

    security:
      - BearerAuth: []

    parameters:
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number for pagination.
      - in: query
        name: per_page
        type: integer
        required: false
        default: 10
        description: Number of records per page.
      - in: query
        name: category_id
        type: integer
        required: true
        description: ID of the category to filter agents.
      - in: query
        name: source_id
        type: integer
        required: false
        description: Optional source ID to further filter agents.
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: "KovaLifeLeads"
            agent_id:
              type: integer
              example: 1212

    responses:
      200:
        description: Success
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  agent_id:
                    type: integer
                    example: 123
                  category:
                    type: integer
                    example: 2
                  source:
                    type: integer
                    example: 1
                  name:
                    type: string
                    example: John Doe
                  user_id:
                    type: integer
                    example: 45
            pagination:
              type: object
              properties:
                total:
                  type: integer
                  example: 50
                current_page:
                  type: integer
                  example: 1
                per_page:
                  type: integer
                  example: 10
                length:
                  type: integer
                  example: 10
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
    """
    data = list_agents_for_assignment(
        request.json,
        request.args.get("category_id"),
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10)),
        request.args.get("source_id")
    )
    return (
        jsonify(
            {
                "data": data[0],
                "pagination": data[1],
                "message": "Success",
                "status": 200,
            }
        ),
        200,
    )



@agents_bp.route("/active-inactive-count", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def agents_active_inactive_count():
    """
    ---
    tags:
      - Agents
    summary: Get Active and Inactive Agents Count
    description: >
      This endpoint retrieves the total count of both active and inactive agents.
      Authentication via a Bearer token is required.

    security:
      - BearerAuth: []

    responses:
      200:
        description: Successfully retrieved agent counts.
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    active:
                      type: integer
                      example: 123
                      description: The total number of active agents.
                    inactive:
                      type: integer
                      example: 2
                      description: The total number of inactive agents.
                message:
                  type: string
                  example: Success
                status:
                  type: integer
                  example: 200
    """
    data = getting_agents_count()
    return {'data': data, 'message': 'Success', 'status': 200}



@agents_bp.route("/total-leads-and-sold", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def get_total_leads_and_sold():
    """
    ---
    tags:
      - Agents
    summary: In agent management page show total sold leads and total completed and incompleted including sold
    description: >
      In agent management page show total sold leads and total completed and incompleted including sold
      Authentication via a Bearer token is required.

    security:
      - BearerAuth: []

    responses:
      200:
        description: Success
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
                      example: 123
                      description: The total completed and incompleted leads without any status filters.
                    sold:
                      type: integer
                      example: 2
                      description: Total sold lead count
                message:
                  type: string
                  example: Success
                status:
                  type: integer
                  example: 200
     """
    data = admin_getting_total_leads_and_sold_count()
    return {'data': data, 'message': 'Success', 'status': 200}


