from flask import (
    jsonify, g, Blueprint, request
)
from app.services.shopping_cart import (
    remove_from_cart, 
    get_cart_items, add_to_cart,
    verify_stock_in_cart, reserve_the_leads,
    update_quatity_of_item_in_cart,
    checkout_final_verifier
    )
from app.api.auth import tokenAuth
from app.services.custom_errors import *


cart_bp = Blueprint('cart', __name__)

@cart_bp.route("", methods=['GET'])
@tokenAuth.login_required
def view_cart():
    """
    Retrieve all active cart items for the authenticated user.
---
tags:
  - Cart
security:
  - BearerAuth: []
responses:
  200:
    description: A list of cart items was successfully retrieved.
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
                example: "80ca89da-0ed4-434b-9e78-349ea06d07e9"
              state:
                type: string
                example: "CA"
              quantity:
                type: integer
                example: 3
        status_code:
          type: integer
          example: 200
    """
    data = get_cart_items()
    return jsonify({'data': data, 'status': 200})


@cart_bp.route("/item/<cart_id>", methods=['DELETE'])
@tokenAuth.login_required
def delete_cart_item(cart_id):
    """
    Remove an item from the shopping cart.

    This endpoint deletes a specific item from the authenticated user's cart based on the provided cart item ID.

    ---
    tags:
      - Cart
    security:
      - BearerAuth: []
    parameters:
      - name: id_
        in: path
        required: true
        type: string
        description: UUID of the cart item to delete
        example: "80ca89da-0ed4-434b-9e78-349ea06d07e9"
    responses:
      200:
        description: Item successfully removed from the cart
        schema:
          type: object
          properties:
            message:
              type: string
              example: Item removed successfully
            status_code:
              type: integer
              example: 200
    """
    remove_from_cart(cart_id)
    return jsonify({'message': 'Item removed successfully', 'status': 200})


@cart_bp.route("/add", methods=["POST"])
@tokenAuth.login_required
def adding_to_shopping_cart():
    """
    Add an item to the shopping cart.

    This endpoint allows an authenticated user to add a product to their shopping cart.
    The product is identified by the `pricing_id`, which must be a record from the PD table
    where `is_fresh_leads=False`.

    ---
    tags:
      - Cart
    security:
      - BearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - state
            - pricing_id
            - quantity
          properties:
            state:
              type: string
              example: "NY"
              description: Two-letter state code where the product is targeted.
            pricing_id:
              type: string
              format: uuid
              example: "ea18c947-cc21-4f55-9b16-5464c72b816f"
              description: ID from the PD table where is_fresh_leads is False.
            quantity:
              type: integer
              minimum: 1
              example: 3
              description: Number of items to add to the cart.
    responses:
      201:
        description: Item added to cart successfully.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "success"
            status:
              type: integer
              example: 201
    """
    add_to_cart(request.json)
    return jsonify({"message": "success", "status": 201})


@cart_bp.route('/stock/verifier', methods=['POST'])
@tokenAuth.login_required
def cart_stock_verification():
    """
    Verify stock availability for mailing leads in the cart.

    ---
    tags:
      - Cart
    security:
      - BearerAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: cart_items
        description: List of cart items to verify stock for. Only items with category_id = 1 are checked.
        required: true
        schema:
          type: array
          items:
            type: object
            required:
              - id
              - category_id
              - month
              - state
              - completed
              - quantity
              - pricing_id
            properties:
              id:
                type: string
                example: "80ca89da-0ed4-434b-9e78-349ea06d07e9"
                description: Cart item unique UUID
              category_id:
                type: integer
                example: 1
                description: Category ID of the item (1 = mailing lead)
              month:
                type: string
                example: 1
                description: Month used to calculate stock availability (1,2,3,6,9)
              state:
                type: string
                example: "CA"
                description: State filter for leads
              completed:
                type: boolean
                example: True
                description: For completed leads it is True and False for incomplete leads
              quantity:
                type: integer
                example: 10
                description: Number of items to be added to the cart
              pricing_id:
                type: string
                format: uuid
                example: "ea18c947-cc21-4f55-9b16-5464c72b816f"
                description: ID from the PD table where is_fresh_leads is False.
    responses:
      200:
        description: Stock verification results successfully retrieved
        schema:
          type: object
          properties:
            data:
              type: object
              additionalProperties:
                type: object
                properties:
                  stock:
                    type: integer
                    example: 15
                    description: Available stock count for the cart item
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    data = verify_stock_in_cart(request.json)
    return jsonify({'data': data, 'message': 'success', 'status': 200})


@cart_bp.route('/checkout/reserve_leads', methods=['POST'])
@tokenAuth.login_required
def checkout_reservation():
    """
    Reserve leads from the cart for checkout.

    ---
    tags:
      - Cart
    summary: Reserve leads for checkout
    description: Authenticated users can reserve one or more leads for purchase. Each item includes metadata such as lead source, category, quantity, and other filters.
    security:
      - BearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: A JSON object containing a list of cart IDs.
        schema:
          type: object
          properties:
            cart_ids:
              type: array
              items:
                type: string
                format: uuid
              example:
                - "80ca89da-0ed4-434b-9e78-349ea06d07e9"
    responses:
      200:
        description: Leads successfully reserved
        schema:
          type: object
          properties:
            data:
              type: array
              description: List of reserved leads
              items:
                type: object
            message:
              type: string
              example: "success"
            status:
              type: integer
              example: 200
    """
    data = reserve_the_leads(request.json.get('cart_ids'))
    return jsonify({'data': data, 'message': 'success', 'status': 200})



@cart_bp.route('/update-quantity/<cart_id>', methods=['PATCH'])
@tokenAuth.login_required
def update_quatity_of_item(cart_id):
    """
    Update the quantity of a cart item.

    This endpoint updates the quantity of a specific cart item.
    If the resulting quantity is less than or equal to zero, the item will be removed.

    ---
    tags:
      - Cart
    parameters:
      - name: cart_id
        in: path
        required: true
        type: string
        format: uuid
        description: UUID of the cart item to update.
        example: 7f7a1cd7-86cf-44d0-8cb1-7a14871deb83
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            quantity:
              type: integer
              description: Quantity to add (positive) or subtract (negative)
              example: 1
    security:
      - BearerAuth: []
    responses:
      200:
        description: Quantity successfully updated or item removed.
        schema:
          type: object
          properties:
            message:
              type: string
              example: Success
            status_code:
              type: integer
              example: 200
    """
    update_quatity_of_item_in_cart(cart_id, request.json['quantity'])
    return jsonify({'message': 'Success', 'status': 200})



@cart_bp.route('/checkout/verifier/<int:category_id>/<shopping_cart_temp_id>/<int:quantity>', methods=['GET'])
@tokenAuth.login_required
def checkout_verifier_with_quantity(category_id, shopping_cart_temp_id, quantity):
    """
    Verify cart checkout details with quantity.

    ---
    tags:
      - Cart
    summary: Verify checkout with specified category, cart item, and quantity
    description: Verifies whether the requested quantity of a cart item in a specific category can be checked out.
    security:
      - BearerAuth: []
    parameters:
      - name: category_id
        in: path
        required: true
        type: integer
        description: The ID of the category.
      - name: shopping_cart_temp_id
        in: path
        required: true
        type: string
        description: The temporary cart item ID.
      - name: quantity
        in: path
        required: true
        type: integer
        description: The quantity to verify.
    responses:
      200:
        description: Verification successful
        schema:
          type: object
          properties:
            message:
              type: string
              example: "success"
            status:
              type: integer
              example: 200
    """
    checkout_final_verifier(category_id, shopping_cart_temp_id, quantity)
    return jsonify({'message': 'success', 'status': 200})    

