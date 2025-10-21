"""API Endpoints related to Users."""

from datetime import datetime

from flask import (
    request, jsonify, g, Blueprint, 
    redirect)

from app.api.auth import tokenAuth
from app.services.custom_errors import *
from app.services.auth import (
    AuthService, 
    admin_authorizer
    )
from app.services.user import (
    adding_new_user,
    edit_user_details,
    change_user_active_inactive_status,
    sent_email_invitation,
    list_users_with_filter,
    interested_user_invitation,
    paginated_intered_users,
    handle_user_intent_request,
    getting_user_active_inactive_count,
    verify_registration_short_url)
from app.models import (
    User
    )
from app import limiter
from config import Config_is

user_bp = Blueprint("users", __name__)
auth_service = AuthService()


@user_bp.route("", methods=["POST"])
@tokenAuth.login_required
@admin_authorizer
def add_new_users():
    """
    Add new user to the application and send email invitation.

    ---
    tags:
      - Users
    summary: Add new user
    description: Creates a new user and sends an email invitation. Requires admin privileges.
    consumes:
      - application/json
    security:
      - BearerAuth: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - email
            - name
          properties:
            email:
              type: string
              format: email
              example: user@kovalifeleads.com
            name:
              type: string
              example: John Doe
            phone:
              type: string
              example: 9876543210
            role_id:
              type: integer
              example: 2
              description: |
                Role ID of the user.
                - 1: Admin
                - 2: Agent
            agency_name:
              type: string
              example: KovaLifeLeads Agency
            agents:
              type: object
              properties:
                human:
                  type: array
                  items:
                    type: object
                    required:
                      - source
                      - category
                    properties:
                      id:
                        type: integer
                        example: 1012
                      source:
                        type: integer
                        example: 1
                      category:
                        type: integer
                        example: 2
                auto:
                  type: array
                  items:
                    type: object
                    required:
                      - source
                      - category
                    properties:
                      id:
                        type: integer
                        nullable: true
                        example: null
                      source:
                        type: integer
                        example: 1
                      category:
                        type: integer
                        example: 1
    responses:
      200:
        description: User created successfully
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
    adding_new_user(request.json, request.json.pop("agents", []))
    return jsonify({"message": "Success", "status": 200})



@user_bp.route("/register_from_invitation", methods=["PUT"])
def user_registration_invitee():
    """
    Register invited user

    Registers a user using the invitation token sent via email.

    ---
    tags:
      - Users
    summary: Register invited user
    description: >
      Registers a user using the invitation token sent via email.  
      You must provide the token in the 'Authorization' header using the format: `Bearer <token>`.

    security:
      - BearerAuth: []

    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
            - email
            - phone
            - agency_name
            - password
            - confirm_password
          properties:
            name:
              type: string
              example: John Shi
            email:
              type: string
              format: email
              example: john@Kovalifeleads.com
            phone:
              type: string
              example: 9876543210
            agency_name:
              type: string
              example: KovaLifeLeads Agency
            password:
              type: string
              format: password
              example: StrongPass123
            confirm_password:
              type: string
              format: password
              example: StrongPass123

    responses:
      200:
        description: Registration successful
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
    g.user = User.verify_auth_token(
        "invitation", str(request.headers.get('Authorization', '')).split('Bearer ')[-1], 
        3600)
    if not g.user:
        raise BadRequest("This linked has expired")
    if len(request.json.get("password", "")) < 5:
        raise BadRequest("Password length is short. Please try another password")
    if request.json.get("password") != request.json.pop("confirm_password", None):
        raise BadRequest("Password Mismatch.")
    auth_service.new_invitee(request.json)
    return jsonify({"message": "Success", "status": 200})


@user_bp.route("/edit_info/<user_id>", methods=["PUT"])
@tokenAuth.login_required
def edit_user_info(user_id):
    """
    Edit user profile and manage associated agents

    ---
    tags:
      - Users
    summary: Update user information and agent relationships
    description: >
      This endpoint updates user profile data and manages their associated agents.
      - Regular users can edit their own name and phone only.
      - Admin users can edit any user's email, role, and manage agents.

      If the user is already registered, this will log them out from all devices.

    consumes:
      - application/json

    security:
      - BearerAuth: []

    parameters:
      - name: user_id
        in: path
        required: true
        type: string
        description: ID of the user to edit

      - in: body
        name: body
        required: true
        description: JSON body with updated fields and agent operations
        schema:
          type: object
          properties:
            name:
              type: string
              description: Updated user name
            phone:
              type: string
              description: Updated user phone number
            email:
              type: string
              description: Updated email (admin-only)
            role_id:
              type: integer
              description: Updated role ID (admin-only)
            agents:
              type: object
              description: New agents to add (by type)
              properties:
                human:
                  type: array
                  description: List of human agents
                  items:
                    type: object
                    properties:
                      name:
                        type: string
                      category:
                        type: string
                      source:
                        type: string
                auto:
                  type: array
                  description: List of auto agents
                  items:
                    type: object
                    properties:
                      source:
                        type: string
                      category:
                        type: string
            remove_agents:
              type: array
              description: List of agent IDs to remove (admin-only)
              items:
                type: integer
            edit_agents:
              type: array
              description: List of agents to update (admin-only, must include ID)
              items:
                type: object
                properties:
                  id:
                    type: integer
                    required: true
                  name:
                    type: string
                  source:
                    type: string
                  category:
                    type: string

    responses:
      200:
        description: Successfully updated user information
        schema:
          type: object
          properties:
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
      400:
        description: Invalid input data or agent conflict
      401:
        description: Unauthorized — Bearer token missing or invalid
      403:
        description: Forbidden — insufficient permissions
    """
    print(request.json)
    edit_user_details(
        user_id,
        request.json.pop("agents", {}),
        request.json.pop("remove_agents", []),
        request.json.pop("edit_agents", {}),
        request.json,
    )
    return jsonify({"message": "Success", "status": 200})


@user_bp.route("/make_user_active_inactive/<user_id>", methods=["PATCH"])
@tokenAuth.login_required
@admin_authorizer
def active_inactivate_user(user_id):
    """
    Activate or deactivate a user

    Changes the active status of a user. Requires admin privileges.

    ---
    tags:
      - Users
    summary: Activate or deactivate a user
    description: >
      Changes the active status of a user.  
      Requires admin privileges.

    security:
      - BearerAuth: []

    parameters:
      - name: user_id
        in: path
        required: true
        type: string
        description: ID of the user to activate or deactivate

      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - is_active
          properties:
            is_active:
              type: boolean
              description: Set to `true` to activate the user, `false` to deactivate
              example: true

    responses:
      200:
        description: Status updated successfully
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
    change_user_active_inactive_status(user_id, request.json["is_active"])
    return jsonify({"message": "success", "status": 200})


@user_bp.route("/paginated_list", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def list_paginated_users():
    """
    Get paginated list of users

    Returns a paginated list of users with optional filtering. Requires admin privileges.

    ---
    tags:
      - Users
    summary: Get paginated list of users
    description: >
      Returns a paginated list of users with optional filtering.  
      Requires admin privileges.

    security:
      - BearerAuth: []

    parameters:
      - name: page
        in: query
        type: integer
        required: false
        default: 1
        example: 1
        description: Page number (e.g., ?page=1)

      - name: per_page
        in: query
        type: integer
        required: false
        default: 10
        example: 10
        description: Number of items per page (e.g., ?per_page=10)

      - name: name
        in: query
        type: string
        required: false
        description: Filter by user name (partial match allowed)

    responses:
      200:
        description: List of users
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
                    example: "123"
                  name:
                    type: string
                    example: "John Shi"
                  email:
                    type: string
                    format: email
                    example: "john@Kovalifeleads.com"
                  phone:
                    type: string
                    example: "9876543210"
                  agency_name:
                    type: string
                    example: "KovaLifeLeads Agency"
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
    args = request.args.to_dict()
    data, pagination = list_users_with_filter(
        int(args.pop('page', 1)),
        int(args.pop('per_page', 10)),
        args
    )
    return jsonify({"data": data, "pagination": pagination, "message": "Success", "status": 200})



@user_bp.route("/resend_invitation_email/<user_id>", methods=["POST"])
@tokenAuth.login_required
@admin_authorizer
def resend_invitation_email(user_id):
    """
    Resend invitation email

    Resends the invitation email to a user who hasn't registered yet. Requires admin privileges.

    ---
    tags:
      - Users
    summary: Resend invitation email
    description: >
      Resends the invitation email to a user who hasn't registered yet.  
      Requires admin privileges.

    security:
      - BearerAuth: []

    parameters:
      - name: user_id
        in: path
        required: true
        type: string
        description: ID of the user to resend invitation

    responses:
      200:
        description: Email resent successfully
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
    user_obj = User.query.filter_by(id=user_id, registered=False).first()
    if not user_obj:
        raise BadRequest("Registration already complete.")
    token = user_obj.generate_auth_token('invitation', Config_is.AUTH_TOKEN_EXPIRES)  # token expires after 12 hours
    user_obj.invited_at = datetime.utcnow()
    user_obj.is_invited = True
    sent_email_invitation(user_obj.id, user_obj.name, user_obj.phone, user_obj.agency_name, token.replace(".", "$$$$$"), {'user_id': user_obj.id, 'email': user_obj.email})
    return jsonify({"message": "Success", "status": 200})


@user_bp.route("/verify-registration-short-link/<id_>")
def verify_sms_registration_url(id_):
    """
    ---
    tags:
      - Registration
    summary: Validates an SMS registration link and redirects the user.
    description: >
      This endpoint is designed to be the target of a shortened URL sent via SMS.
      It validates the unique identifier provided in the path parameter. If the ID is
      valid, it performs a redirection to the full, canonical registration page on
      the front-end. This is a crucial step for the registration flow, ensuring
      that users from mobile devices are seamlessly directed to the correct page
      for completion.

    parameters:
      - name: id_
        in: path
        required: true
        description: The unique ID from the short registration URL.
        schema:
          type: string
          example: "aBcD1eFgH2iJkL3"
          
    responses:
      302:
        description: Redirects to the actual registration page URL.
        headers:
          Location:
            description: The URL to redirect to.
            schema:
              type: string
              example: "https://your-frontend.com/register?token=xyz123"
      400:
        description: Registration link not found, invalid, or expired.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "The registration link is invalid, expired, or has already been used."
            status:
              type: integer
              example: 400
    """
    url = verify_registration_short_url(id_)
    return jsonify({"data": url, "message": "Success", "status": 200})


@user_bp.route("/me", methods=["GET"])
@tokenAuth.login_required
def get_my_own_user_data():
    """
    Get current user details

    Returns details of the currently authenticated user.

    ---
    tags:
      - Users
    summary: Get current user details
    description: Returns details of the currently authenticated user.

    security:
      - BearerAuth: []

    responses:
      200:
        description: User details
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                id:
                  type: string
                  example: "123"
                name:
                  type: string
                  example: "John Shi"
                email:
                  type: string
                  format: email
                  example: "john@Kovalifeleads.com"
                phone:
                  type: string
                  example: "9876543210"
                agency_name:
                  type: string
                  example: "KovaLifeLeads Agency"
                role_id:
                  type: integer
                  example: 2
                is_active:
                  type: boolean
                  example: true
                stripe_customer_id:
                  type: string
                  example: "cus_Jx9Yh1234ABC"
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
    """
    user_obj = User.query.filter_by(id=g.user["id"]).first()
    if not user_obj:
        raise NoContent()
    return jsonify({"data": user_obj.to_dict(), "message": "Success", "status": 200})


@user_bp.route("/interested/request", methods=["POST"])
# @limiter.limit("10 per day")
def interested_person_email():
    """
    Submit interest request

    Allows potential users to submit their information when signup is not available.

    ---
    tags:
      - Interested Users
    summary: Submit interest request
    description: Allows potential users to submit their information when signup is not available.

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: "John Shi"
            email:
              type: string
              format: email
              example: "john@Kovalifeleads.com"
            phone:
              type: string
              example: "19999"
            address:
              type: string
              example: "123 KovaLifeLeads St."
            hierarchy:
              type: string
              example: "Level 1"
            hierarchy_email:
              type: string
              format: email
              example: "manager@Kovalifeleads.com"
            hierarchy_phone:
              type: string
              example: "199999"
          required:
            - name
            - email

    responses:
      200:
        description: Request submitted successfully
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
    interested_user_invitation(request.json)
    return jsonify({"message": "success", "status": 200})


@user_bp.route("/interested/requests/paginated", methods=["POST"])
@tokenAuth.login_required
@admin_authorizer
def paginated_interested_requests():
    """
    Get paginated list of interested user requests.

    ---
    tags:
      - Interested Users
    summary: Get Paginated Interested User Requests
    description: >
      Retrieves a paginated list of interested user requests sorted by creation time (most recent first).
      Requires Bearer token authentication and admin privileges.

    parameters:
      - name: page
        in: query
        type: integer
        required: false
        default: 1
        description: Page number to retrieve.
      - name: per_page
        in: query
        type: integer
        required: false
        default: 10
        description: Number of results per page.

    security:
      - BearerAuth: []

    responses:
      200:
        description: A paginated list of interested users.
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
                  # Add additional dynamic payload fields here
            pagination:
              type: object
              properties:
                total:
                  type: integer
                  description: Total number of items.
                current_page:
                  type: integer
                  description: Current page number.
                per_page:
                  type: integer
                  description: Items per page.
                length:
                  type: integer
                  description: Number of items in this page.
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
      204:
        description: No content found for the given page.
      401:
        description: Unauthorized Bearer token missing or invalid.
      403:
        description: Forbidden user is not authorized as an admin.
    """
    data = paginated_intered_users(
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10))
        )
    return jsonify({'data': data[0], 'pagination': data[1], 'message': 'Success', 'status': 200})



@user_bp.route("/interested/decision_making/<id_>", methods=["POST"])
@tokenAuth.login_required
@admin_authorizer
def handle_users_requests(id_):
    """
    Process interest request

    ---
    tags:
      - Interested Users
    summary: Approve or reject an interest request
    description: >
      Admin-only endpoint to approve or reject a user interest request.

      Requires a valid Bearer token with admin privileges.

    consumes:
      - application/json

    security:
      - BearerAuth: []

    parameters:
      - name: id_
        in: path
        required: true
        type: string
        description: ID of the interested user request

      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - action
          properties:
            action:
              type: string
              enum: [approve, reject]
              description: Action to take
            rejection_message:
              type: string
              description: Optional message if rejecting the request

    responses:
      200:
        description: Request processed successfully
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
    request_data = request.json
    if not request_data.get("action"):
        raise BadRequest("action is required")
    handle_user_intent_request(
        id_,
        request_data["action"],
        request_data.get("rejection_message")
    )
    return jsonify({"message": "Success", "status": 200})

@user_bp.route("/active-inactive/count", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def get_users_grouped_by_active():
   """
    Get counts of active and inactive users

    ---
    tags:
      - Users
    summary: Retrieve active / inactive user counts
    description: >
      Returns the total number of users whose **is_active** flag is
      **True** (“active”) and **False** (“inactive”).  
      Requires a valid Bearer token.

    consumes:
      - application/json

    security:
      - BearerAuth: []

    responses:
      200:
        description: Counts retrieved successfully
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                active:
                  type: integer
                  example: 28
                inactive:
                  type: integer
                  example: 1
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
   """
   data = getting_user_active_inactive_count() 
   return jsonify({'data': data, 'message': 'Success', 'status': 200})


