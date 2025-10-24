"""API Endpoints related to lead data ."""

from flask import request, jsonify, g, Blueprint

from app.api.auth import tokenAuth
from app.services.leads_operations import (
    single_mortgage_public,
    get_mailing_single_mortgage_details,
    # mailing_bird_view,
    change_lead_status,
    notes_add_update,
    delete_sales_docs,
    upload_sales_docs,
    list_mailing_suppression_requests,
    get_mailing_leads_search,
    admin_mailing_suppression_decide,
    list_sold_documents,
    CopyMoveMailingLead,
    get_agents_mailing_leads,
    get_multiple_agents_stats_campaign_state_view,
    get_multiple_agents_stats_campaign_view,
    # get_leads_count_for_territory,
    get_campaign_leads_view,
    get_my_leads_status_count,
    single_mailing_lead_status_log
)
from app.services.auth import admin_authorizer
from app.services.custom_errors import *

from constants import CSV_DOWNLOAD_MORTGAGE_FIELDS
    


leads_bp = Blueprint("leads", __name__)


@leads_bp.route("/details/<int:category>", methods=["POST"])
@tokenAuth.login_required
def view_leads(category):
    """
    View Leads by Category

    Retrieves a filtered list of leads based on the provided category ID and filters in the body. Supports pagination using query parameters.

    ---
    tags:
      - Leads
    consumes:
      - application/json
    parameters:
      - name: category
        in: path
        type: integer
        required: true
        description: Category ID to filter leads.
      - name: page
        in: query
        type: integer
        required: false
        description: Page number for pagination (default is 1).
        example: 1
      - name: per_page
        in: query
        type: integer
        required: false
        description: Number of results per page (default is 10).
        example: 10
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            lead_status:
              type: integer
              example: 1
            campaign:
              type: string
              example: "dummyOne"
            name:
              type: string
              example: "Luke Skywalker"
            state:
              type: string
              example: "CA"
            city:
              type: string
              example: "Los Angeles"
            zip:
              type: string
              example: "90212"
            is_mailed:
              type: boolean
              example: false
            completed:
              type: boolean
              example: true
            purchased_user_id:
              type: string
              format: uuid
              description: UUID of the user who purchased this lead.
              example: "e6f8c7d0-1234-5678-9abc-def012345678"
        agent_id:
              type: integer
              example: 1002
    responses:
      200:
        description: Leads list retrieved successfully
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
            pagination:
              type: object
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    security:
      - BearerAuth: []
    """
    print(request.json)
    if category == 1:
        result, pagination = get_agents_mailing_leads(
            request.json,
            int(request.args.get("page", 1)),
            int(request.args.get("per_page", 10)),
        )
        # elif category == 2:
        #     result, pagination = get_agent_digital_leads_excluding_suppressed(
        #         int(request.args.get('agent_id')), int(request.args.get('source_id')),  request.json, int(request.args.get('page', 1)),
        #         int(request.args.get('per_page', 10)))
    return jsonify(
        {"data": result, "pagination": pagination, "message": "success", "status": 200}
    )




@leads_bp.route(
    "/single_mortgage/<int:category_id>/<int:agent_id>/<mortgage_id>",
    methods=["GET"],
)
@tokenAuth.login_required
def getting_single_mortgage_details(category_id, agent_id, mortgage_id):
    """
    Get Single Mortgage Details

    Retrieves detailed information of a single mortgage lead, based on the category and agent.

    ---
    tags:
      - Leads
    summary: Get Single Mortgage Details
    description: >
      Returns details of a single mortgage lead based on category.  
      Currently only category 1 (mailed leads) is supported.  
      Access is restricted to admins or agents assigned to the lead.
    
    security:
      - BearerAuth: []

    parameters:
      - name: category_id
        in: path
        required: true
        type: integer
        description: Lead category ID (1 = mailed leads).
      - name: agent_id
        in: path
        required: true
        type: integer
        description: Agent ID requesting the mortgage lead.
      - name: mortgage_id
        in: path
        required: true
        type: string
        description: ID of the mortgage lead.

    responses:
      200:
        description: Mortgage details retrieved successfully.
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                agent_id:
                  type: integer
                  example: 101
                notes:
                  type: string
                  example: "Client interested in refinancing"
                # Add more fields here as returned by mailer_single_lead_serializer
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    if g.user["role_id"] != 1 and agent_id not in g.user["agents"]:
        raise Forbidden()
    if category_id == 1:
        data = get_mailing_single_mortgage_details(mortgage_id, agent_id)
    # else:
    #     lead_is = LeadMember.query.join(DigitalLeads, DigitalLeads.id == LeadMember.digital_lead_id).with_entities(
    #         DigitalLeads, LeadMember.lead_status, LeadMember.notes, LeadMember.agent_id, LeadMember.campaign_name).filter(
    #             LeadMember.digital_lead_id == mortgage_id, LeadMember.agent_id == agent_id).first()
    #     if lead_is:
    #         result = get_digital_single_mortgage_details(mortgage_id, lead_is)
    return jsonify({"data": data, "message": "success", "status": 200})


@leads_bp.route("/single_mortgage_public/<mortgage_id>/<uuid>", methods=["GET"])
def getting_single_mortgage_public(mortgage_id, uuid):
    """
    Get Single Public Mortgage Lead

    Publicly retrieves a single mortgage lead using mortgage ID and UUID.

    ---
    tags:
      - Leads
    summary: Get Single Public Mortgage Lead
    description: >
      Retrieves the details of a single mortgage lead without requiring authentication.  
      This is a public endpoint intended for shared access using the unique UUID and mortgage ID.
    
    security:
      - BearerAuth: []

    parameters:
      - name: mortgage_id
        in: path
        required: true
        type: string
        description: ID of the mortgage lead.
      - name: uuid
        in: path
        required: true
        type: string
        description: Unique identifier associated with the mortgage lead.

    responses:
      200:
        description: Mortgage details retrieved successfully.
        schema:
          type: object
          properties:
            data:
              type: object
              # Include expected fields returned from mailer_single_lead_serializer
              example:
                full_name: John Doe
                state: CA
                loan_amount: 250000
                notes: Interested in refinancing
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    result = single_mortgage_public(mortgage_id, uuid)
    return jsonify({"data": result, "message": "success", "status": 200})


# TODO: delete this stats
# @leads_bp.route("/stats/campaign/<int:file_id>", methods=["GET"])
# @tokenAuth.login_required
# @admin_authorizer
# def getting_stats_for_all_agents_campaign(file_id):
#     """
#     Get campaign statistics for all agents associated with a specific file.

#     This endpoint retrieves aggregated statistics for agents linked to the given campaign file ID.
#     It returns the total number of entries per agent and how many of those are marked as completed (`completed = True`).

#     ---
#     tags:
#       - Campaign Stats
#     security:
#       - BearerAuth: []
#     parameters:
#       - name: file_id
#         in: path
#         type: integer
#         required: true
#         description: The ID of the file (campaign) to retrieve statistics for.
#     responses:
#       200:
#         description: Successfully retrieved campaign statistics for agents.
#         schema:
#           type: object
#           properties:
#             status:
#               type: integer
#               example: 200
#             message:
#               type: string
#               example: success
#             data:
#               type: array
#               items:
#                 type: object
#                 properties:
#                   agent_id:
#                     type: integer
#                     example: 1002
#                   name:
#                     type: string
#                     example: denzz
#                   total:
#                     type: integer
#                     example: 25
#                   True:
#                     type: integer
#                     description: Count of completed leads (completed = True).
#                     example: 12
#     """
#     data = get_multiple_agents_stats_campaign_view(file_id)
#     return jsonify({"data": data, "message": "success", "status": 200})



# @leads_bp.route("/stats/weeks", methods=["GET"])
# @tokenAuth.login_required
# @admin_authorizer
# def getting_weeks_stats_for_all_agents():
#     data = mailing_bird_view(int(request.args.get("page", 1)))
#     return jsonify(
#         {
#             "data": data,
#             "current_page": int(request.args.get("page", 1)),
#             "message": "success",
#             "status": 200,
#         }
#     )

# TODO: delete this stats
# @leads_bp.route("/stats/campaign_state/<int:file_id>", methods=["GET"])
# @tokenAuth.login_required
# @admin_authorizer
# def getting_stats_for_all_agents_campaign_state(file_id):
#     """
#     Get Campaign Stats for All Agents

#     Returns campaign performance statistics for all agents related to a specific file.

#     ---
#     tags:
#       - Campaign Stats
#     summary: Get Campaign Stats for All Agents
#     description: >
#       Provides a summary of lead stats per agent based on a campaign file.  
#       Only accessible by admin users.  
#       The stats include agent ID, agent name, total leads, and completed leads (`completed=True`).
    
#     security:
#       - BearerAuth: []

#     parameters:
#       - name: file_id
#         in: path
#         required: true
#         type: integer
#         description: File ID associated with the campaign.

#     responses:
#       200:
#         description: Successfully retrieved campaign statistics.
#         schema:
#           type: object
#           properties:
#             data:
#               type: array
#               items:
#                 type: object
#                 properties:
#                   agent_id:
#                     type: integer
#                     example: 123
#                   name:
#                     type: string
#                     example: John Doe
#                   total:
#                     type: integer
#                     example: 50
#                     description: Total number of leads assigned to the agent.
#                   True:
#                     type: integer
#                     example: 30
#                     description: Number of `completed=True` leads.
#             message:
#               type: string
#               example: success
#             status:
#               type: integer
#               example: 200
#     """
#     data = get_multiple_agents_stats_campaign_state_view(file_id)
#     return jsonify({"data": data, "message": "success", "status": 200})


@leads_bp.route("/status/<int:category>", methods=["POST"])
@tokenAuth.login_required
def status_changing(category):
    """
    Change Lead Status

    Updates the status of one or more leads based on the category and user role.

    ---
    tags:
      - Leads
    summary: Change Lead Status
    description: >
      Allows users to update the status of leads.  
      - **Category 1** is for mailing leads and expects `mortgage_ids`.  
      - Admins can update leads for specific agents using `agent_id`.
    
    security:
      - BearerAuth: []

    parameters:
      - name: category
        in: path
        type: integer
        required: true
        description: Lead category (1 = mailing leads)

      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            mortgage_ids:
              type: array
              items:
                type: integer
              example: [1, 2, 3]
              description: Required for mailing leads (category 1)
            lead_status:
              type: integer
              example: 1
              description: New status to apply to the leads
            agent_id:
              type: integer
              example: 101
              description: Required for admins to update a specific agent’s leads

    responses:
      200:
        description: Lead status updated successfully
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
    change_lead_status(category, request.json)
    return jsonify({"message": "success", "status": 200})


@leads_bp.route("/status/decide/<int:category>", methods=["POST"])
@tokenAuth.login_required
@admin_authorizer
def lead_status_decide(category):
    """
    Approve or Reject Lead Suppression Requests

    Allows admin users to approve or reject suppression requests for mailing leads.

    ---
    tags:
      - Leads
    summary: Decide Lead Suppression Status (Admin Only)
    description: >
      Used by admins to approve (`lead_status` = 12) or reject (`lead_status` = 13) lead suppression requests.  
      Currently supports **Mailing Leads (category 1)** only.  
      For rejection, `suppression_rejection_msg` must be provided.
    
    security:
      - BearerAuth: []

    parameters:
      - name: category
        in: path
        type: integer
        required: true
        description: Lead category (1 = mailing leads)

      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - lead_status
            - agent_mortgage
          properties:
            lead_status:
              type: integer
              enum: [12, 13]
              description: 12 = Approve, 13 = Reject
              example: 12
            suppression_rejection_msg:
              type: string
              example: Upload new document
              description: Required when rejecting the suppression request (lead_status = 12)
            mortgage_ids:
              type: array
              description: List of mailing assignee id + agent ID pairs to process
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 11212
                  agent_id:
                    type: integer
                    example: 2131

    responses:
      200:
        description: Suppression status updated successfully
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
    if category == 1:
        admin_mailing_suppression_decide(
            request.json.pop("agent_mortgage", []), request.json
        )
    # elif category == 2:
    #     admin_digital_suppression_decide(request.json.pop('ids', []), request.json)
    return jsonify({"message": "success", "status": 200})


@leads_bp.route("/notes/<int:category>", methods=["POST"])
@tokenAuth.login_required
def adding_notes(category):
    """
    Add or Update Lead Notes

    Adds or updates notes for a specific lead based on category.  
    Currently supports **Mailing Campaigns (category 1)**.

    ---
    tags:
      - Leads
    summary: Add or Update Notes
    description: >
      Allows agents to add or update notes for a lead.  
      Non-admin users can only update notes for leads assigned to them.  
      Admins must provide the `agent_id` explicitly.
    
    security:
      - BearerAuth: []

    parameters:
      - name: category
        in: path
        type: integer
        required: true
        description: Lead category (1 = Mailing leads)

      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - mortgage_id
            - notes
            - agent_id
          properties:
            mortgage_id:
              type: str
              example: 3
              description: ID of the mortgage lead (required for mailing leads)
            agent_id:
              type: integer
              example: 111
              description: Agent ID assigned to the lead
            notes:
              type: string
              example: Hi Smijith
              description: Note to add or update for the lead

    responses:
      200:
        description: Notes updated successfully
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
    notes_add_update(category, request.json)
    return jsonify({"message": "success", "status": 200})


@leads_bp.route("/copy/<int:category>", methods=["POST"])
@tokenAuth.login_required
def copying_leads(category):
    """
    Copies leads from one agent to another and both can handle it.
    ---
    tags:
      - Leads
    summary: Copy Leads (Mailing)
    description: >
      Used to copy one or more leads from source agents to a new agent (`to_agent_id`).  
      Only allowed if the lead is not already assigned to the target agent.
    
    security:
      - BearerAuth: []

    parameters:
      - name: category
        in: path
        required: true
        type: integer
        description: Campaign category (1 = Mailing)

      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - mortgage_ids
            - to_user_id
            - to_agent_id
          properties:
            mortgage_ids:
              type: object
              description: A mapping of mortgage IDs to their current agent IDs
              example: { "1121": 101, "244334": 102 }
            to_user_id:
              type: integer
              example: 10
              description: User ID to whom the new agent belongs
            to_agent_id:
              type: integer
              example: 1121
              description: Agent ID to which leads should be copied

    responses:
      200:
        description: Leads copied successfully
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
    if category == 1:
        # mortgage_ids = list(request.json.get('mortgage_ids').keys())
        CopyMoveMailingLead(request.json).copy_leads()
    # elif category == 2:
    #     ids = list(request.json.get('ids').keys())
    #     CopyMoveDigitalLeads(request.json).copy_leads()
    #     for i in range(0, len(ids), 100):
    #         tasks.move_copy_digital_leads_to_ghl.delay(ids[i:i + 100], request.json.get('to_agent_id'))
    return jsonify({"message": "success", "status": 200})


@leads_bp.route("/move/<int:category>", methods=["POST"])
@tokenAuth.login_required
def moving_leads(category):
    """
    Move Leads to Another Agent

    Moves leads from one agent to another within the same organization.  
    Currently supports **Mailing Campaigns (category 1)** only.

    ---
    tags:
      - Leads
    summary: Move Leads (Mailing)
    description: >
      Transfers ownership of one or more leads from their current agents to a new agent.  
      Records movement history and resets lead status to `1` for the moved leads.
    
    security:
      - BearerAuth: []

    parameters:
      - name: category
        in: path
        required: true
        type: integer
        description: Campaign category (1 = Mailing)

      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - mortgage_ids
            - to_user_id
            - to_agent_id
          properties:
            mortgage_ids:
              type: object
              description: A mapping of mortgage IDs to their current agent IDs
              example: { "1121": 101, "244334": 102 }
            to_user_id:
              type: integer
              example: 10
              description: User ID that owns the target agent
            to_agent_id:
              type: integer
              example: 1121
              description: Agent ID to whom the leads will be moved

    responses:
      200:
        description: Leads moved successfully
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
    if category == 1:
        # mortgage_ids = list(request.json.get('mortgage_ids').keys())
        CopyMoveMailingLead(request.json).move_leads()
    # elif category == 2:
    #     ids = list(request.json.get('ids').keys())
    #     CopyMoveDigitalLeads(request.json).move_leads()
    #     for i in range(0, len(ids), 100):
    #         tasks.move_copy_digital_leads_to_ghl.delay(ids[i:i + 100], request.json.get('to_agent_id'))
    return jsonify({"message": "success", "status": 200})


@leads_bp.route("/docs/<int:category>/<mortgage_id>/<agent_id>", methods=["DELETE"])
@tokenAuth.login_required
def deleting_sold_lead_docs(category, mortgage_id, agent_id):
    """
    Delete Sales Documents

    Delete one or more documents associated with a lead from the S3 bucket.

    ---
    tags:
      - Leads
    summary: Delete Lead Documents (Mailing)
    description: >
      Removes specified documents stored in AWS S3 for a particular lead in a mailing campaign.
      Only the owner agent or an admin can delete the documents.

    security:
      - BearerAuth: []

    parameters:
      - name: category
        in: path
        required: true
        type: integer
        description: Campaign category (1 = Mailing)
      - name: mortgage_id
        in: path
        required: true
        type: string
        description: Mortgage ID of the lead
      - name: agent_id
        in: path
        required: true
        type: integer
        description: Agent id

      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - file_names
          properties:
            file_names:
              type: array
              items:
                type: string
              description: List of filenames to delete from the lead's document folder
              example: ["sale.jpg", "consent.pdf"]

    responses:
      200:
        description: Documents deleted successfully
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
    print(type(category))
    delete_sales_docs(category, mortgage_id, agent_id, request.json["file_names"])
    return jsonify({"message": "success", "status": 200})


@leads_bp.route("/docs/<int:category>/<mortgage_id>/<int:agent_id>", methods=["POST"])
@tokenAuth.login_required
def uploading_multi_docs(category, mortgage_id, agent_id):
    """
Upload Multiple Sales Documents for a Lead

Uploads one or more files to AWS S3 for a specific lead in a mailing campaign. 
Only authorized agents can upload documents.

---
tags:
  - Leads
summary: Upload Lead Documents (Mailing)
description: >
  Upload multiple sales-related documents for a lead. Files are uploaded
  to AWS S3 under the mailing campaign folder. User must be authorized to upload.

consumes:
  - multipart/form-data

parameters:
  - name: category
    in: path
    required: true
    type: integer
    description: Campaign category (e.g., 1 = Mailing)
  - name: mortgage_id
    in: path
    required: true
    type: string
    description: Mortgage ID of the lead
  - name: agent_id
    in: path
    required: true
    type: integer
    description: Agent ID of the lead
  - name: files
    in: formData
    required: true
    type: array
    items:
      type: file
    description: List of files to upload for the lead

security:
  - BearerAuth: []

responses:
  200:
    description: Files uploaded successfully
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

    upload_sales_docs(category, mortgage_id, agent_id, request.files)
    return jsonify({"message": "success", "status": 200})


@leads_bp.route("/docs/<int:category>/<mortgage_id>/<int:agent_id>", methods=["GET"])
@tokenAuth.login_required
def listing_docs(category, mortgage_id, agent_id):
    """
    List Sales Documents for a Lead

    Retrieves a list of documents stored in AWS S3 for a given lead, returning presigned URLs
    for temporary access. Only authorized users can access documents.

    ---
    tags:
      - Leads
    summary: List Lead Documents (Mailing)
    description: >
      Lists all sales documents available for a lead in the mailing campaign category.
      Returns presigned URLs valid for 12 hours (43200 seconds).

    security:
      - BearerAuth: []

    parameters:
      - name: category
        in: path
        required: true
        type: integer
        description: Campaign category (1 = Mailing)
      - name: mortgage_id
        in: path
        required: true
        type: string
        description: Mortgage ID of the lead
      - name: agent_id
        in: path
        required: true
        type: integer
        description: corresponding agent id


    responses:
      200:
        description: List of documents with presigned URLs
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
                    description: File name
                    example: consent.pdf
                  url:
                    type: string
                    format: uri
                    description: Presigned URL for temporary access to the file
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    result = list_sold_documents(category, mortgage_id, agent_id)
    return jsonify({"data": result, "message": "success", "status": 200})


@leads_bp.route("/suppression-requests/<int:category>", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def getting_suppression_requests_list(category):
    """
    Get Suppression Requests List

    Retrieves a paginated list of suppression requests for the specified category.
    Only accessible to admin users.

    ---
    tags:
      - Leads
    summary: Get Suppression Requests
    description: >
      Returns a paginated list of suppression requests for mailing campaigns (category=1).
      Pagination parameters are optional query parameters.
    
    security:
      - BearerAuth: []

    parameters:
      - name: category
        in: path
        required: true
        type: integer
        description: Suppression request category (1 = Mailing)

      - name: page
        in: query
        required: false
        type: integer
        default: 1
        description: Page number for pagination

      - name: per_page
        in: query
        required: false
        type: integer
        default: 10
        description: Number of items per page

    responses:
      200:
        description: Paginated list of suppression requests
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  mortgage_id:
                    type: integer
                    example: 1234
                  source_id:
                    type: integer
                    example: 1
                  full_name:
                    type: string
                    example: John Doe
                  state:
                    type: string
                    example: CA
                  id:
                    type: integer
                    example: 5678
                  agent_id:
                    type: integer
                    example: 101
                  notes:
                    type: string
                    example: "Note about the lead"
                  lead_status:
                    type: integer
                    example: 7
                  suppression_rejection_msg:
                    type: string
                    example: "Rejection reason"
                  campaign_name:
                    type: string
                    example: "Campaign A"
                  call_in_date_time:
                    type: string
                    format: date-time
                    example: "2025-06-09T15:30:00Z"
                  completed:
                    type: boolean
                    example: true
                  ivr_response:
                    type: string
                    example: "Some response"
                  ivr_logs:
                    type: string
                    example: "Logs here"
                  sold_date:
                    type: string
                    example: "06-09-2025"
                  agent_name:
                    type: string
                    example: "Agent Smith"
                  zip:
                    type: string
                    example: "90210"
            pagination:
              type: object
              properties:
                total:
                  type: integer
                  example: 100
                current_page:
                  type: integer
                  example: 1
                length:
                  type: integer
                  example: 10
                per_page:
                  type: integer
                  example: 10
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    if category == 1:
        data, pagination = list_mailing_suppression_requests(
            int(request.args.get("page", 1)), int(request.args.get("per_page", 10))
        )
    # elif category == 2:
    #     data, pagination = list_digital_suppression_requests(int(request.args.get('source_id')),
    #                                                          int(request.args.get('page', 1)),
    #                                                          int(request.args.get('per_page', 10)))
    return jsonify(
        {"data": data, "pagination": pagination, "message": "success", "status": 200}
    )


@leads_bp.route("/mortgage/global-search/<int:category>", methods=["POST"])
@tokenAuth.login_required
def searching_mortgage_id(category):
    """
    Search Mortgage Leads by Mortgage ID

    Allows users to search mailing leads by mortgage ID.

    ---
    tags:
      - Leads
    summary: Search Leads by Mortgage ID
    description: >
      Performs a search within mailing leads based on the provided mortgage ID.
      Only mailing category (category=1) is supported.

    consumes:
      - application/json
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

      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - search
          properties:
            search:
              type: string
              example: "71000016"

    responses:
      200:
        description: Successful search result
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                mortgage_id:
                  type: string
                  example: "71000016"
                source_id:
                  type: integer
                  example: 1
                full_name:
                  type: string
                  example: John Doe
                state:
                  type: string
                  example: CA
                agent_id:
                  type: integer
                  example: 123
                notes:
                  type: string
                  example: Important lead
                lead_status:
                  type: integer
                  example: 7
                suppression_rejection_msg:
                  type: string
                  example: "Incomplete data"
                campaign_name:
                  type: string
                  example: XYZ Campaign
                call_in_date_time:
                  type: string
                  format: date-time
                  example: "2025-06-09T10:00:00Z"
                completed:
                  type: boolean
                  example: false
                ivr_response:
                  type: string
                  example: "Positive"
                ivr_logs:
                  type: string
                  example: "Call logs..."
                zip:
                  type: string
                  example: "90210"
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    if category == 1:
        result = get_mailing_leads_search(request.json.get("search"))
    # elif category == 2:
    #     result, pagination = get_digital_leads_search_mortgage_name_id(request.json)
    return jsonify(
        {"data": result, "message": "success", "status": 200}
    )

# @leads_bp.route("/territory/count/<int:category>", methods=["GET"])
# @tokenAuth.login_required
# def get_mailing_leads_count_for_territory(category):
#     """
#     Get Mailing Leads Count by Territory

#     Retrieves lead counts grouped by state/territory, based on category.

#     ---
#     tags:
#       - Leads
#     summary: Get Leads Count by Territory
#     description: >
#       Returns a breakdown of total, completed, incompleted, suppressed, and sold leads
#       grouped by state for mailing category (only category=1 is supported).

#     produces:
#       - application/json

#     security:
#       - BearerAuth: []

#     parameters:
#       - name: category
#         in: path
#         type: integer
#         required: true
#         description: Lead category (only 1 is supported)

#     responses:
#       200:
#         description: Territory-wise lead count
#         schema:
#           type: object
#           properties:
#             data:
#               type: array
#               items:
#                 type: object
#                 properties:
#                   state:
#                     type: string
#                     example: "CA"
#                   total_leads:
#                     type: integer
#                     example: 125
#                   completed:
#                     type: integer
#                     example: 45
#                   incomplete:
#                     type: integer
#                     example: 50
#                   suppressed_leads:
#                     type: integer
#                     example: 15
#                   sold_leads:
#                     type: integer
#                     example: 10
#             message:
#               type: string
#               example: success
#             status:
#               type: integer
#               example: 200
#     """
#     result = get_leads_count_for_territory(category)
#     return jsonify(
#         {"data": result, "message": "success", "status": 200}
#     )

# @leads_bp.route("/territory/statewise/count/<int:category>", methods=["GET"])
# @tokenAuth.login_required
# def view_statewise_territory_leads_count_route(category):
#     """
#     Get State-wise Mailing Leads Count by Territory (Paginated)

#     Retrieves a paginated breakdown of leads grouped by state/territory for the given category.

#     ---
#     tags:
#       - Leads
#     summary: Get State-wise Leads Count by Territory
#     description: >
#       Returns a paginated list of total, completed, incomplete, suppressed, and sold leads
#       grouped by state for mailing category (only category=1 is supported).

#     produces:
#       - application/json

#     security:
#       - BearerAuth: []

#     parameters:
#       - name: category
#         in: path
#         type: integer
#         required: true
#         description: Lead category (only 1 is supported)
#       - name: page
#         in: query
#         type: integer
#         required: false
#         default: 1
#         description: Page number for pagination
#       - name: per_page
#         in: query
#         type: integer
#         required: false
#         default: 10
#         description: Number of items per page

#     responses:
#       200:
#         description: Paginated state-wise lead count
#         schema:
#           type: object
#           properties:
#             data:
#               type: array
#               items:
#                 type: object
#                 properties:
#                   state:
#                     type: string
#                     example: "CA"
#                   total_leads:
#                     type: integer
#                     example: 125
#                   completed:
#                     type: integer
#                     example: 45
#                   incomplete:
#                     type: integer
#                     example: 50
#                   suppressed_leads:
#                     type: integer
#                     example: 15
#                   sold_leads:
#                     type: integer
#                     example: 10
#             meta:
#               type: object
#               properties:
#                 total:
#                   type: integer
#                   example: 100
#                 current_page:
#                   type: integer
#                   example: 1
#                 length:
#                   type: integer
#                   example: 10
#                 per_page:
#                   type: integer
#                   example: 10
#             message:
#               type: string
#               example: success
#             status:
#               type: integer
#               example: 200
#     """
#     result, pagination = get_statewise_territory_leads_count(int(category),int(request.args.get("page", 1)), int(request.args.get("per_page", 10)))
#     return jsonify({
#         "data": result,
#         "pagination": pagination,
#         "message": "success",
#         "status": 200
#     })


@leads_bp.route('/campaign-leads', methods=['GET'])
@tokenAuth.login_required
def get_campaign_leads():
    """
    Get Campaign Leads Summary
    Returns summarized campaign leads data grouped by campaign name. Supports filtering by marketplace.
    ---
    tags:
      - Leads
    summary: Get Campaign Leads
    description: >
      Provides a summarized view of campaign leads, including total leads, completed leads, incomplete leads,
      suppressed leads, and sold leads per campaign. Supports pagination and optional filtering by marketplace.
    produces:
      - application/json
    security:
      - BearerAuth: []
    parameters:
      - name: page
        in: query
        type: integer
        required: false
        default: 1
        description: Page number for pagination
      - name: per_page
        in: query
        type: integer
        required: false
        default: 10
        description: Number of records per page
      - name: marketplace
        in: query
        type: string
        required: false
        default: ""
        description: Filter based on marketplace (e.g., '1' for user-purchased campaigns)
    responses:
      200:
        description: A list of campaign leads with pagination info
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  campaign_name:
                    type: string
                    example: "XYZ Campaign"
                  total_leads:
                    type: integer
                    example: 25
                  Rich_leads:
                    type: integer
                    example: 10
                  Partial_leads:
                    type: integer
                    example: 12
                  suppressed_leads:
                    type: integer
                    example: 2
                  sold_leads:
                    type: integer
                    example: 1
            pagination:
              type: object
              properties:
                total:
                  type: integer
                  example: 120
                current_page:
                  type: integer
                  example: 1
                length:
                  type: integer
                  example: 10
                per_page:
                  type: integer
                  example: 10
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
   """
    data, pagination = get_campaign_leads_view(int(request.args.get('page', 1)), int(request.args.get('per_page', 10)), request.args.get('marketplace', ''))
    return jsonify(
        {"data": data, "pagination": pagination, "message": "success", "status": 200}
    )


@leads_bp.route('/status-summary-count', methods=['GET'])
def get_leads_status_counts():
    """
    Get Lead Status Summary
    Returns a summary of leads grouped by lead status (First Call, Second Call, etc.) for the logged-in user's leads.
    ---
    tags:
      - Leads
    summary: Get Lead Status Summary
    description: >
      Provides total counts of leads in various statuses such as First Call, Second Call, Third Call, Appointments, and Sold
      across all territories for the logged-in user. This API is used for the dashboard summary display.
    produces:
      - application/json
    responses:
      200:
        description: Lead status summary counts
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                total_leads:
                  type: integer
                  example: 43
                first_call:
                  type: integer
                  example: 12
                second_call:
                  type: integer
                  example: 8
                third_call:
                  type: integer
                  example: 5
                appointments:
                  type: integer
                  example: 7
                sold:
                  type: integer
                  example: 11
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    data = get_my_leads_status_count()
    return jsonify(
        {"data": data,  "message": "success", "status": 200}
    )

@leads_bp.route('/single/status-log/<int:mailing_assignee_id>/<int:agent_id>', methods = ['GET'])
@tokenAuth.login_required
def get_single_mailing_lead_status_log(mailing_assignee_id, agent_id):
    """
    Get mailing lead status log for a single mailing assignee.

    ---
    tags:
      - Mailing Leads
    parameters:
      - name: mailing_assignee_id
        in: path
        type: integer
        required: true
        description: ID of the mailing assignee
      - name: agent_id
        in: path
        type: integer
        required: true
        description: ID of the agent
      - name: Authorization
        in: header
        type: string
        required: true
        description: Bearer token for authentication
    responses:
      200:
        description: Mailing lead status log fetched successfully
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 200
            message:
              type: string
              example: success
            data:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 101
                  lead_status:
                    type: string
                    example: Contacted
                  created_at:
                    type: string
                    example: "2025-07-01 14:35:00"
    """
    result = single_mailing_lead_status_log(mailing_assignee_id, agent_id)
    return jsonify(
        {"data": result, "message": "success", "status": 200}
    )


@leads_bp.route("/stats/campaign_state", methods=['POST'])
@tokenAuth.login_required
@admin_authorizer
def getting_stats_for_all_agents_campaign_state():
    """
    Get Campaign State Stats

    Retrieves lead statistics grouped by state for a specific campaign.

    ---
    tags:
      - Leads
    summary: Retrieve state-wise lead statistics for a campaign
    description: |
      This endpoint provides aggregated statistics of leads per state for the given campaign. Requires authentication.
    security:
      - BearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: Campaign identifier payload
        schema:
          type: object
          required:
            - campaign
          properties:
            campaign:
              type: string
              example: "L6302025N"
              description: The unique identifier for the campaign.
    responses:
      200:
        description: Successfully retrieved campaign state statistics
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
                    example: "TX"
                    description: The state code
                  count:
                    type: integer
                    example: 45
                    description: Number of leads in the state
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    data = get_multiple_agents_stats_campaign_state_view(request.json['campaign'])
    return jsonify({'data': data, 'message': 'success', 'status': 200})
    
@leads_bp.route("/stats/campaign", methods=['POST'])
@tokenAuth.login_required
@admin_authorizer
def getting_stats_for_all_agents_campaign():
    """
    Get Campaign Stats

    Retrieves overall lead statistics for a specific campaign.

    ---
    tags:
      - Leads
    summary: Fetch lead statistics for a campaign
    description: |
      This endpoint returns aggregated statistics (such as total leads, lead statuses, or other metrics depending on your implementation) for the given campaign. Authentication is required.
    security:
      - BearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: Payload containing the campaign identifier
        schema:
          type: object
          required:
            - campaign
          properties:
            campaign:
              type: string
              example: "L6302025N"
              description: The unique campaign identifier.
    responses:
      200:
        description: Successfully retrieved campaign statistics
        schema:
          type: object
          properties:
            data:
              type: object
              description: Campaign statistics
              example:
                total_leads: 100
                contacted: 60
                not_contacted: 40
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    data = get_multiple_agents_stats_campaign_view(request.json['campaign'])
    return jsonify({'data': data, 'message': 'success', 'status': 200})
