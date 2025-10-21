from flask import Blueprint, request, jsonify
from app.api.auth import tokenAuth
from app.services.auth import admin_authorizer
from app.services.coupon_service import (
    PromotionService, list_promotion_assigned_members,
    list_users_for_promo_assign
    )

promotion_bp = Blueprint('promotion_bp', __name__)

@promotion_bp.route("", methods=["POST"])
@tokenAuth.login_required
@admin_authorizer
def create_promotion():
    """
    Create a new promotion code.

    This endpoint creates a promotion code in Stripe and stores it in the database.

    ---
    tags:
      - Promotions
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - coupon_code_id
            - coupon
            - code
            - expires_at
          properties:
            coupon_code_id:
              type: string
              description: The internal coupon code ID from the database.
              example: c8b029fb-44da-422c-8237-ff8c1d0effea
            coupon:
              type: string
              description: The Stripe coupon ID to attach to this promotion code.
              example: 8lrQvJ2k
            code:
              type: string
              description: The unique promotion code customers will use.
              example: vishnu_FOREVER_PRIVATE_50_OFF_2
            active:
              type: boolean
              description: Whether the promotion code is active.
              example: true
            max_redemptions:
              type: integer
              description: Maximum number of redemptions allowed.
              example: 10
            expires_at:
              type: string
              format: date-time
              description: Expiry date and time for the promotion in "%m-%d-%Y %H:%M:%S" format.
              example: 08-25-2025 13:10:20
            restrictions_first_time_transaction:
              type: boolean
              description: Restrict usage to first-time transactions only.
              example: true
            restrictions_minimum_amount:
              type: integer
              description: Minimum purchase amount (in cents) required for the promotion.
              example: 5000
            is_public:
              type: boolean
              description: |
                Whether the promotion is public.  
                - If true → promotion is available to everyone.  
                - If false → you must pass `assigned_users`.
              example: false
            assigned_users:
              type: array
              items:
                type: string
              description: List of user IDs allowed to use the promotion (required if `is_public` is false).
              example:
                - 992ea8be-1228-44ff-8e1a-9219e99f2db7
                - 77d355e0-bc11-4f2b-99a1-a3d7ac6b0a77
    responses:
      201:
        description: Successfully created promotion code
        schema:
          type: object
          properties:
            message:
              type: string
              example: Promotion code created successfully
            status:
              type: integer
              example: 201
    security:
      - BearerAuth: []
    """
    PromotionService.creating_stripe_promotion(request.json, request.args.get('time_zone'))
    return jsonify({"message": "Promotion code created successfully","status": 201})


# @promotion_bp.route("/<promo_id>", methods=["GET"])
# @tokenAuth.login_required
# @admin_authorizer
# def retrieve_promotion(promo_id):
#     """
#     Retrieve a promotion code by ID.

#     This endpoint retrieves the details of a specific promotion code using its unique ID.

#     ---
#     tags:
#       - Promotions
#     security:
#       - BearerAuth: []
#     parameters:
#       - name: promo_id
#         in: path
#         type: string
#         required: true
#         description: The ID of the promotion code to retrieve.
#     responses:
#       200:
#         description: Promotion code retrieved successfully.
#         schema:
#           type: object
#           properties:
#             message:
#               type: string
#               example: Promotion code retrieved successfully
#             status_code:
#               type: integer
#               example: 200
#             data:
#               type: object
#               properties:
#                 id:
#                   type: string
#                   example: promo_ABC123
#                 code:
#                   type: string
#                   example: NEWCOUPON123
#                 coupon:
#                   type: string
#                   example: NW9R8Nvi
#                 active:
#                   type: boolean
#                   example: true
#                 expires_at:
#                   type: integer
#                   example: 1735689600
#                 max_redemptions:
#                   type: integer
#                   example: 10
#       401:
#         description: Unauthorized - Invalid or missing token.
#       404:
#         description: Promotion code not found.
#     """
#     data = PromotionService.retrieving_promotion(promo_id)
#     return jsonify({"message": "Promotion code retrieved successfully", "status": 200, "data": data})

@promotion_bp.route("/<promo_id>", methods=["PATCH"])
@tokenAuth.login_required
@admin_authorizer
def activate_or_deactivate_promotion(promo_id):
    """
    Activate or deactivate a promotion code.

    This endpoint updates an existing promotion code using its unique ID. You can update fields like `active`.

    ---
    tags:
      - Promotions
    security:
      - BearerAuth: []
    parameters:
      - name: promo_id
        in: path
        type: string
        required: true
        description: The ID of the promotion code to update.
      - in: body
        schema:
          type: object
          properties:
            active:
              type: boolean
              description: Whether the promotion code is active.
              example: true
    responses:
      200:
        description: Successfully updated promotion code.
        schema:
          type: object
          properties:
            message:
              type: string
              example: Successfully updated promotion code
            status_code:
              type: integer
              example: 200
      400:
        description: Bad Request - Invalid input.
      401:
        description: Unauthorized - Invalid or missing token.
      404:
        description: Promotion code not found.
    """
    PromotionService.activating_deactivating_promotion(promo_id, request.json)
    return jsonify({"message": "Successfully updated promotion code", "status": 200})


@promotion_bp.route("/<promo_db_id>", methods=["DELETE"])
@tokenAuth.login_required
@admin_authorizer
def delete_promotion(promo_db_id):
    """
    Delete (deactivate) a promotion code by ID.

    This endpoint deactivates a promotion code by setting its active status to False.

    ---
    tags:
      - Promotions
    security:
      - BearerAuth: []
    parameters:
      - name: promo_id
        in: path
        type: string
        required: true
        description: The ID of the promotion code to delete.
    responses:
      200:
        description: Successfully deleted promotion code.
        schema:
          type: object
          properties:
            message:
              type: string
              example: Successfully deleted promotion
            status_code:
              type: integer
              example: 200
      401:
        description: Unauthorized - Invalid or missing token.
      404:
        description: Promotion code not found.
    """
    PromotionService.deleting_promotion(promo_db_id)
    return jsonify({"message": "Successfully deleted promotion", "status": 200})


@promotion_bp.route("/paginated", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def paginated_coupons():
    """
    Get a paginated list of promotions for a given coupon.

    This endpoint retrieves a paginated list of promotions associated with the specified
    `coupon_code_id`. Supports optional filters for active status and search by code.

    ---
    tags:
      - Promotions
    parameters:
      # - name: coupon_code_id
      #   in: path
      #   type: string
      #   required: true
      #   description: The ID of the coupon whose promotions should be listed.
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
      - name: time_zone
        in: query
        type: string
        required: false
        description: Time zone identifier to convert date fields (e.g., "UTC", "Asia/Kolkata").
      - name: is_active
        in: query
        type: boolean
        required: false
        description: Filter promotions by active status (true or false).
      - name: search
        in: query
        type: string
        required: false
        description: Search promotions by code (case-insensitive partial match).
    responses:
      200:
        description: Successfully retrieved paginated promotions.
        schema:
          type: object
          properties:
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
            pagination:
              type: object
              properties:
                total:
                  type: integer
                  example: 42
                current_page:
                  type: integer
                  example: 1
                length:
                  type: integer
                  example: 10
                per_page:
                  type: integer
                  example: 10
            data:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                    example: 5a08c1c1-23fa-4b99-b12c-b9c96c0a63d0
                  code:
                    type: string
                    example: SUMMER2025
                  stripe_promotion_id:
                    type: string
                    example: promo_1N2xYh2eZvKYlo2Cj0jM99dR
                  expires_at:
                    type: string
                    example: 2025-12-31T23:59:59Z
                  max_redemptions:
                    type: integer
                    example: 100
                  is_public:
                    type: boolean
                    example: false
                  restrictions_first_time_transaction:
                    type: boolean
                    example: true
                  restrictions_minimum_amount:
                    type: integer
                    example: 5000
                  created_by:
                    type: string
                    example: user_123
                  modified_at:
                    type: string
                    example: 2025-08-15T12:34:56Z
                  coupon_code_id:
                    type: string
                    example: c8b029fb-44da-422c-8237-ff8c1d0effea
    security:
      - BearerAuth: []
    """
    result, pagination = PromotionService.admin_listing_promotions(
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10)),
        request.args.get("time_zone"),
        request.args.get("is_active"),
        request.args.get("code"),
        request.args.get('coupon_name')
    )
    return jsonify({'data': result, 'pagination': pagination, 'message': 'success', 'status': 200})


# @promotion_bp.route("/my-promotions/<pricing_id>", methods=["POST"])
# @tokenAuth.login_required
# def get_active_promotions_for_user(pricing_id):
#     data = PromotionService.getting_active_promotions(
#         pricing_id,
#         request.args.get('time_zone')
#     )
#     return jsonify({'message': 'Successfully listed promotions', 'status': 200, 'data': data})


@promotion_bp.route("/my-promotion-code-for-subscription/<pricing_id>", methods=["POST"])
@tokenAuth.login_required
def get_active_promotion_codes_for_user(pricing_id):
    """
    Get Active Promotion Codes for a User
    ---
    tags:
      - Promotions
    parameters:
      - in: path
        name: pricing_id
        required: true
        schema:
          type: string
          format: uuid
        description: UUID of the pricing plan.
      - in: query
        name: time_zone
        required: false
        schema:
          type: string
        description: Time zone in which to display date/time values.
    responses:
      200:
        description: Successfully listed promotion codes.
        schema:
          type: object
          properties:
            message:
              type: string
              example: Successfully listed promotion codes
            status:
              type: integer
              example: 200
            data:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                    example: promo_ABC123
                  code:
                    type: string
                    example: NEWCOUPON123
                  coupon_code_id:
                    type: string
                    example: c8b029fb-44da-422c-8237-ff8c1d0effea
                  duration:
                    type: string
                    example: forever
                  is_active:
                    type: boolean
                    example: true
                  is_public:
                    type: boolean
                    example: true
                  percent_off:
                    type: integer
                    example: 50
                  amount_off:
                    type: number
                    example: null
                  max_redemptions:
                    type: integer
                    example: 10
                  redeem_by:
                    type: string
                    example: Sat, 30 Aug 2025 18:29:00 GMT
                  restrictions_first_time_transaction:
                    type: boolean
                    example: true
                  restrictions_minimum_amount:
                    type: integer
                    example: 5000
                  expires_at:
                    type: string
                    example: 08-25-2025 13:10:20
      401:
        description: Unauthorized - Invalid or missing token.
    """
    data = PromotionService.getting_active_promotion_codes(
        pricing_id,
        request.args.get('time_zone')
    )
    return jsonify({'message': 'Successfully listed promotions', 'status': 200, 'data': data})


@promotion_bp.route("/validate/<promo_db_id>", methods=["GET"])
@tokenAuth.login_required
def validate_user_promo_eligibility(promo_db_id):
    """
    Validate a Promotion Code for a User
    ---
    tags:
      - Promotions
    parameters:
      - in: path
        name: promo_db_id
        required: true
        schema:
          type: string
          format: uuid
        description: Database UUID of the promotion code.
    responses:
      200:
        description: Promotion code is valid and can be used.
        schema:
          type: object
          properties:
            message:
              type: string
              example: Promotion code is valid for use.
            status:
              type: integer
              example: 200
      400:
        description: Promotion code is invalid, expired, or already used.
        schema:
          type: object
          properties:
            message:
              type: string
              example: You have already used this promotion code.
            status:
              type: integer
              example: 400
      401:
        description: Unauthorized - Invalid or missing token.
    """
    PromotionService.validate_promo_code(promo_db_id)
    return jsonify({"message": "Promotion code is valid for use.", "status": 200})



@promotion_bp.route("/members/<promo_db_id>", methods=['GET'])
@tokenAuth.login_required
@admin_authorizer
def get_promotion_members(promo_db_id):
    """
    API endpoint to retrieve members assigned to a specific promotion.

    ---
    tags:
      - Promotions
    summary: Get promotion members
    description: Retrieves a paginated list of members assigned to a promotion, including their names and IDs.
    parameters:
      - name: promo_db_id
        in: path
        type: string
        required: true
        description: The unique ID of the promotion.
      - name: page
        in: query
        type: integer
        description: The page number for pagination. Defaults to 1.
        default: 1
      - name: per_page
        in: query
        type: integer
        description: The number of items per page. Defaults to 10.
        default: 10
      - name: timezone
        in: query
        type: string
        required: true
        description: The user's timezone for accurate time representation. (e.g., 'America/New_York')
      - name: name_search
        in: query
        type: string
        description: A string to filter users by name.
    security:
      - APIKeyAuth: []
    responses:
      200:
        description: A paginated list of promotion members.
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  member_id:
                    type: integer
                    description: The ID of the member.
                  name:
                    type: string
                    description: The name of the member.
            pagination:
              type: object
              properties:
                page:
                  type: integer
                per_page:
                  type: integer
                total_items:
                  type: integer
                total_pages:
                  type: integer
            message:
              type: string
            status:
              type: integer
    """
    data = list_promotion_assigned_members(
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10)),
        promo_db_id,
        request.args['timezone']
        )
    return jsonify({'data': data[0], 'pagination': data[1], 'message': 'Success', 'status': 200})


@promotion_bp.route("/unassigned-users", methods=['GET'])
@tokenAuth.login_required
@admin_authorizer
def listing_users_for_promo_assign():
    """
    API endpoint to list users not yet assigned to a promotion.

    ---
    tags:
      - Promotions
    summary: Get unassigned users for a promotion
    description: Retrieves a paginated and searchable list of users who are not yet assigned to the specified promotion. This is useful for assigning new members.
    parameters:
      - name: promo_db_id
        in: query
        type: string
        required: true
        description: The unique ID of the promotion to find unassigned users for.
      - name: page
        in: query
        type: integer
        description: The page number for pagination. Defaults to 1.
        default: 1
      - name: per_page
        in: query
        type: integer
        description: The number of items per page. Defaults to 10.
        default: 10
      - name: name_search
        in: query
        type: string
        description: A string to filter users by name.
    security:
      - APIKeyAuth: []
    responses:
      200:
        description: A paginated list of unassigned users.
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  user_id:
                    type: integer
                    description: The ID of the user.
                  name:
                    type: string
                    description: The name of the user.
            pagination:
              type: object
              properties:
                page:
                  type: integer
                per_page:
                  type: integer
                total_items:
                  type: integer
                total_pages:
                  type: integer
            message:
              type: string
            status:
              type: integer
    """
    data = list_users_for_promo_assign(
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10)),
        request.args.get('promo_db_id'),
        request.args.get('name_search')
        )
    return jsonify({'data': data[0], 'pagination': data[1], 'message': 'Success', 'status': 200})