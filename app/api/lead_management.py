

from flask import (
    Blueprint, jsonify, request, g
    )

from app.api.auth import tokenAuth
from app.services.lead_management import (
    get_agents_leads_count
    )


lead_management_bp = Blueprint('LeadManagement', __name__)



@lead_management_bp.route("/count/<int:category>", methods=["GET"])
@tokenAuth.login_required
def getting_agent_mailer_leads_count_view(category):
    """
    Get Agent Leads Count by Category

    Retrieves the count of different types of leads (completed, incomplete, sold) based on the provided category ID.

    ---
    tags:
      - Lead Management
    parameters:
      - name: category
        in: path
        type: integer
        required: true
        description: Category ID to filter lead counts.
        example: 1
      - name: agent_id
        in: query
        type: integer
        required: false
        description: ID of the agent (only for admin use).
        example: 123
      - name: purchased_user_id
        in: query
        type: string
        required: false
        format: uuid
        description: UUID of the user who purchased this lead.
        example: "e6f8c7d0-1234-5678-9abc-def012345678"
    responses:
      200:
        description: Lead count retrieved successfully
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                completed:
                  type: integer
                  example: 2
                incomplete:
                  type: integer
                  example: 2
                sold:
                  type: integer
                  example: 0
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    security:
      - BearerAuth: []
    """
    if category == 1:
       result = get_agents_leads_count(
           request.args.get('agent_id'), 
           request.args.get('purchased_user_id')
           )
    return jsonify(
        {"data": result, "message": "success", "status": 200}
    )
