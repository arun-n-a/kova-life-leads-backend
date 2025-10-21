"""API Endpoints related to File uploader and download."""

from flask import request, jsonify, Blueprint

from app.api.auth import tokenAuth
from app.services.pricing_details import (
    list_subscription_pricing_plans, 
    update_pricing_detail,
    admin_list_pricing_packages,
    list_pricing_plans_in_mp,
    creating_product_pricing,
    deactivating_product_pricing
    )
from app.services.auth import admin_authorizer
from constants import USA_STATES


pricing_bp = Blueprint("leads_pricing", __name__)


@pricing_bp.route("/usa_states", methods=["GET"])
@tokenAuth.login_required
def list_usa_states():
    """
    List USA States

    Returns a list of USA states.

    ---
    tags:
      - Pricing
    summary: List USA States
    description: Returns a list of USA states.

    security:
      - BearerAuth: []

    responses:
      200:
        description: Successful response with the list of USA states
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
                type: string
              example: ["Alabama", "Alaska", "Arizona"]
    """
    return jsonify({"data": USA_STATES, "message": "success", "status": 200})

@pricing_bp.route("/subscriptions", methods=["GET"])
@tokenAuth.login_required
def subscription_plans_details():
    """
    Get Pricing Details

    Retrieves pricing plans for mailer leads.

    ---
    tags:
      - Pricing
    summary: Get Pricing Details
    description: >
      Fetch all subscription pricing plans

    security:
      - BearerAuth: []

    responses:
      200:
        description: Successful response with pricing data
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
                  category:
                    type: string
                  source:
                    type: string
                  is_fresh_leads:
                    type: boolean
                  description:
                    type: string
                  month:
                    type: integer
                  unit_price:
                    type: number
                  title:
                    type: string
                  quantity:
                    type: integer
                  stripe_product_id:
                    type: string
                  stripe_price_id:
                    type: string
                  net_price:
                    type: number
    """
    data, pagination = list_subscription_pricing_plans(
            int(request.args.get("page", 1)), int(request.args.get("per_page", 10))
        )
    return jsonify({"data": data, "pagination": pagination, "message": "success", "status": 200})


@pricing_bp.route("/marketplace", methods=["GET"])
@tokenAuth.login_required
def marketplace_plans_details():
    """
    Get Pricing Details

    Retrieves all the pricing plans available in the marketplace

    ---
    tags:
      - Pricing
    summary: Get Pricing Details
    description: >
      Fetch all marketplace pricing plans

    security:
      - BearerAuth: []

    responses:
      200:
        description: Successful response with pricing data
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
                  category:
                    type: string
                  source:
                    type: string
                  description:
                    type: string
                  month:
                    type: integer
                  unit_price:
                    type: number
                  title:
                    type: string
                  quantity:
                    type: integer
                  stripe_product_id:
                    type: string
                  stripe_price_id:
                    type: string
                  net_price:
                    type: number
    """
    result = list_pricing_plans_in_mp()
    return jsonify({"data": result, "message": "success", "status": 200})



@pricing_bp.route('/<pricing_id>', methods=['PUT'])
def update_pricing(pricing_id):
    """
    Update Pricing Detail

    Updates the pricing information for a specific pricing ID, including Stripe updates for product and pricing.

    ---
    tags:
      - Pricing
    summary: Update Pricing Detail
    description: >
      Updates pricing details in the database. Also updates the corresponding Stripe product or price
      if title, description, or unit_price is modified.

    parameters:
      - name: pricing_id
        in: path
        type: string
        required: true
        description: The ID of the pricing entry to update
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            title:
              type: string
              example: Fresh Leads Standard
            description:
              type: string
              example: Updated description for pricing
            unit_price:
              type: number
              format: float
              example: 49.99
            currency:
              type: string
              example: usd
            quantity:
              type: integer
              example: 100
            month:
              type: integer
              example: 1
            category:
              type: string
              example: Leads
            source:
              type: string
              example: LinkedIn
    responses:
      200:
        description: Pricing detail updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Pricing detail updated successfully
            status:
              type: integer
              example: 200
    """
    update_pricing_detail(pricing_id, request.json)
    return jsonify({"message": "Pricing detail updated successfully", "status": 200})


@pricing_bp.route("/admin", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def pricing_details_admin_view():
    """
    Get all pricing packages for admin view with active subscription counts.

    This endpoint returns a list of pricing details with the number of active subscriptions
    associated with each pricing plan. Only accessible by admin users.

    ---
    tags:
      - Pricing
    security:
      - BearerAuth: []
    responses:
      200:
        description: A list of pricing packages with subscription details
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
                    format: uuid
                    example: "a317d744-1193-46d5-9c8d-218e992d1e9b"
                  category:
                    type: integer
                    example: 1
                  source:
                    type: integer
                    example: 1
                  is_fresh_leads:
                    type: boolean
                    example: true
                  description:
                    type: string
                    example: "New details"
                  month:
                    type: integer
                    example: 3
                  unit_price:
                    type: number
                    format: float
                    example: 30.5
                  title:
                    type: string
                    example: "Updated Plan"
                  quantity:
                    type: integer
                    example: 10
                  stripe_product_id:
                    type: string
                    example: "prod_SZNiLWPtR2cyJh"
                  stripe_price_id:
                    type: string
                    example: "price_1ReTSKHFuUbT6ZjVHPvltL5T"
                  active_subscriptions_count:
                    type: integer
                    example: 0
                  net_price:
                    type: number
                    format: float
                    example: 31
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    result = admin_list_pricing_packages()
    return jsonify({"data": result, "message": "success", "status": 200})

@pricing_bp.route("/create-product-pricing", methods=["POST"])
@tokenAuth.login_required
@admin_authorizer
def create_price_stripe():
    """
    Create a new product and its pricing in Stripe and store in the database.

    This endpoint allows admin users to create a new pricing product. It creates the product in Stripe,
    stores the pricing information in the internal database, and optionally generates a Stripe price object
    if `unit_price` and `is_fresh_leads` are provided.

    ---
    tags:
      - Pricing
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - title
            - quantity
            - category
            - source
            - unit_price
            - is_fresh_leads
          properties:
            title:
              type: string
              example: "Updated Plan"
            description:
              type: string
              example: "New details"
            quantity:
              type: integer
              example: 10
            # month:
            #   type: integer
            #   description: "This is required only for marketplace"
            #   example: 3
            category:
              type: integer
              example: 1
            source:
              type: integer
              example: 1
            unit_price:
              type: number
              format: float
              example: 30.5
            is_fresh_leads:
              type: boolean
              example: true
            currency:
              type: string
              example: "usd"
              default: "usd"
    responses:
      200:
        description: Product and pricing created successfully
        schema:
          type: object
          properties:
            data:
              type: boolean
              example: true
            message:
              type: string
              example: "Success"
            status:
              type: integer
              example: 200
    """
    result = creating_product_pricing(request.json)
    return jsonify({"data": result, "message": "Success", "status": 200})

@pricing_bp.route("/deactivate-product-pricing/<pricing_id>", methods=["PATCH"])
@tokenAuth.login_required
@admin_authorizer
def deactivate_product_pricing(pricing_id):
    """
    Deactivate a pricing product and its associated Stripe pricing/product.

    This endpoint deactivates the pricing product in the internal database and also deactivates
    the corresponding product and pricing in Stripe. Only accessible by admin users.

    ---
    tags:
      - Pricing
    security:
      - BearerAuth: []
    parameters:
      - name: pricing_id
        in: path
        required: true
        description: UUID of the pricing product to deactivate
        type: string
        format: uuid
        example: "a317d744-1193-46d5-9c8d-218e992d1e9b"
    responses:
      201:
        description: Successfully deactivated the product and pricing
        schema:
          type: object
          properties:
            data:
              type: boolean
              example: true
            message:
              type: string
              example: "Success"
            status:
              type: integer
              example: 201
    """
    result = deactivating_product_pricing(pricing_id)
    return jsonify({"data": result, "message": "Success", "status": 201})