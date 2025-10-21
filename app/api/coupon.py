from flask import Blueprint, jsonify, request

from app.api.auth import tokenAuth
from app.services.auth import admin_authorizer
from app.services.coupon_service import CouponService

coupon_bp = Blueprint('coupon_bp', __name__) 


@coupon_bp.route("", methods=["POST"])
@tokenAuth.login_required
@admin_authorizer
def create_coupon():
    """
    Create a new Coupon

    ---
    tags:
      - Coupons
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            duration:
              type: string
              enum: [once, repeating, forever]
              description: >
                Duration of coupon: "once", "repeating", or "forever".
                If "repeating", 'duration_in_months' is required.
              example: once
            percent_off:
              type: number
              format: float
              description: >
                Percentage discount. Cannot be used with 'amount_off'.
              example: 25
            amount_off:
              type: integer
              description: >
                Fixed discount amount in cents. Cannot be used with 'percent_off'.
              example: 500
            duration_in_months:
              type: integer
              description: >
                Required if duration is "repeating".
              example: 3
            id:
              type: string
              description: Optional custom coupon ID.
              example: nRO9bq9Z
            max_redemptions:
              type: integer
              description: Max times this coupon can be redeemed.
              example: 100
            redeem_by:
              type: string
              format: date-time
              description: Expiration date and time in "%m-%d-%Y %H:%M:%S" format.
              example: 06-13-2025 13:10:20
            name:
              type: string
              description: Coupon name.
              example: 20% Off for June
            assigned_pricing_ids:
              type: array
              items:
                type: string
              description: >
                List of pricing IDs to assign this coupon to.  
                If provided, the coupon will be linked to the specified pricing plans.
              example:
                - price_123
                - price_456
          required:
            - duration
            - name
    responses:
      201:
        description: Successfully created coupon
        schema:
          type: object
          properties:
            message:
              type: string
              example: Successfully created coupon
            status:
              type: integer
              example: 201
    security:
      - BearerAuth: []
    """
    CouponService.creating_coupon(request.json)
    return jsonify({"message": "Successfully created coupon", "status": 201})



# @coupon_bp.route("/paginated", methods=["GET"])
# @tokenAuth.login_required
# @admin_authorizer
# def paginated_coupons():
#     """
#     List items in coupon managment UI
#     ___
#     tags:
#       - Coupons
#     parameters:
#       - name: page
#         in: query
#         type: integer
#         required: true
#         default: 1
#         description: Page number for pagination.

#       - name: per_page
#         in: query
#         type: integer
#         required: true
#         default: 10
#         description: Number of items per page.
      
#       - name: name
#         in: query
#         type: string
#         required: false
#         description: Coupon code for search filter
#     responses:
#       200:
#         description: Success
#         schema:
#           type: object
#           properties:
#             data:
#               type: array
#               items:
#                 type: object
#                 properties:
#                   name:
#                     type: String
#                     example: Summer Sale
#                   stripe_coupon_id: 
#                     type: String
#                     example: 98nhWsIm
#                   duration:
#                     type: String
#                     example: forever, once, or repeating
#                   percent_off:
#                     type: integer
#                     example: 25
#                   amount_off:
#                     type: integer
#                     example: 2500
#                   source:
#                     type: integer
#                     example: 1
#                   max_redemptions:
#                     type: integer
#                     example: 2
#                   redeem_by:
#                     type: String
#                     example: 06-13-2025 13:10:20
#             pagination:
#               type: object
#               properties:
#                 total:
#                   type: integer
#                   example: 50
#                 current_page:
#                   type: integer
#                   example: 1
#                 per_page:
#                   type: integer
#                   example: 10
#                 length:
#                   type: integer
#                   example: 10
#             message:
#               type: string
#               example: Success
#             status:
#               type: integer
#               example: 200
#     """

@coupon_bp.route("/<stripe_coupon_id>", methods=["PUT"])
@tokenAuth.login_required
@admin_authorizer
def update_coupon(stripe_coupon_id):
    """
    Update an existing coupon
    ---
    tags:
      - Coupons
    parameters:
      - in: path
        name: stripe_coupon_id
        required: true
        schema:
          type: string
        description: The ID of the Stripe coupon to update.
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: The new name for the coupon.
              example: Summer Promo Coupon
    responses:
      200:
        description: Coupon successfully updated.
        schema:
          type: object
          properties:
            message:
              type: string
              example: Successfully updated coupon
            status:
              type: integer
              example: 200
    security:
      - BearerAuth: []
    """
    CouponService.updating_coupon(stripe_coupon_id, request.json['name']) 
    return jsonify({"message": "Successfully updated coupon", "status": 200})


@coupon_bp.route("/<coupon_id>", methods=["DELETE"])
@tokenAuth.login_required
@admin_authorizer
def delete_coupon(coupon_id):
    """
    Delete a coupon by ID.
    ---
    tags:
      - Coupons
    security:
      - BearerAuth: []
    parameters:
      - name: coupon_id
        in: path
        type: string
        required: true
        description: The ID of the coupon to delete.
    responses:
      200:
        description: Successfully deleted coupon.
        schema:
          type: object
          properties:
            message:
              type: string
              example: Successfully deleted coupon
            status:
              type: integer
              example: 200
    """
    CouponService.deleting_coupon(coupon_id)
    return jsonify({"message": "Successfully deleted coupon", "status": 200})


# @coupon_bp.route("/active-deactivate-coupon/<coupon_id>", methods=["PATCH"])
# @tokenAuth.login_required
# @admin_authorizer
# def update_coupon_status(coupon_id):
#     """
#     Activate or deactivate a coupon by ID.
#     ---
#     tags:
#       - Coupons
#     security:
#       - BearerAuth: []
#     parameters:
#       - name: coupon_id
#         in: path
#         type: string
#         required: true
#         description: The ID of the coupon to update.
#       - in: body
#         name: body
#         required: true
#         schema:
#           type: object
#           properties:
#             is_active:
#               type: boolean
#               description: Set to `true` to activate or `false` to deactivate the coupon.
#               example: true
#     responses:
#       200:
#         description: Coupon status updated successfully.
#         schema:
#           type: object
#           properties:
#             message:
#               type: string
#               example: Coupon status updated successfully
#             status:
#               type: integer
#               example: 200
#     """
#     CouponService.updating_coupon_status(coupon_id, request.json["is_active"])
#     return jsonify({"message": "Coupon status updated successfully", "status": 200})


@coupon_bp.route("/paginated", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def paginated_coupons():
    """
    Get a paginated list of coupons.
    ---
    tags:
      - Coupons
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: page
        type: integer
        required: false
        description: Page number (defaults to 1).
        example: 1
      - in: query
        name: per_page
        type: integer
        required: false
        description: Number of results per page (defaults to 10).
        example: 10
      - in: query
        name: time_zone
        type: string
        required: false
        description: Time zone for formatting date fields.
        example: Asia/Dubai
    responses:
      200:
        description: Successfully retrieved paginated coupons.
        schema:
          type: object
          properties:
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
            data:
              type: array
              items:
                type: object
                properties:
                  amount_off:
                    type: integer
                    example: 500
                  duration:
                    type: string
                    example: once
                  percent_off:
                    type: integer
                    example: 25
                  name:
                    type: string
                    example: Summer Promo
                  max_redemptions:
                    type: integer
                    example: 100
                  stripe_coupon_id:
                    type: string
                    example: nRO9bq9Z
                  redeem_by:
                    type: string
                    example: 06-13-2025 13:10:20
                  is_active:
                    type: boolean
                    example: true
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
    """
    result, pagination = CouponService.admin_listing_coupons(
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10)),
        request.args.get('time_zone')
    )
    return jsonify({'data': result, 'pagination': pagination, 'message': 'success', 'status': 200})
