from flask import Blueprint, request, jsonify

from app.services.invoice_service import get_invoice_data
from app.api.auth import tokenAuth 

invoice_bp = Blueprint("invoice_bp", __name__)


# @invoice_bp.route("/subscription/<stripe_subscription_id>", methods=["GET"])
# @tokenAuth.login_required
# def get_subscription_invoice(stripe_subscription_id):
#     """
# Retrieve detailed invoice information for a specific Stripe subscription.

# ---
# tags:
#   - Invoices
# security:
#   - BearerAuth: []
# parameters:
#   - name: stripe_subscription_id
#     in: path
#     required: true
#     schema:
#       type: string
#     description: Stripe subscription ID to fetch invoice data for
# responses:
#   200:
#     description: Successfully retrieved the invoice
#     content:
#       application/json:
#         schema:
#           type: object
#           properties:
#             data:
#               type: object
#               properties:
#                 invoice_number:
#                   type: string
#                   example: "INV-20250703-2"
#                 invoice_date:
#                   type: string
#                   example: "July 03, 2025"
#                 due_date:
#                   type: string
#                   example: "July 18, 2025"
#                 from:
#                   type: object
#                   properties:
#                     name:
#                       type: string
#                       example: "KovaLifeLeads Insurance Company"
#                     address:
#                       type: string
#                       example: "123 Main St, City, Country"
#                     phone:
#                       type: string
#                       example: "123-456-7890"
#                     email:
#                       type: string
#                       example: "abc@gmail.com"
#                 bill_to:
#                   type: object
#                   properties:
#                     name:
#                       type: string
#                       example: "Avanthika P U"
#                     agency:
#                       type: string
#                       nullable: true
#                     phone:
#                       type: string
#                       example: "123456789"
#                     email:
#                       type: string
#                       example: "avanthika@abacies.com"
#                 payment_details:
#                   type: object
#                   properties:
#                     bank_name:
#                       type: string
#                       example: "First National Bank"
#                     method:
#                       type: string
#                       example: "Bank Transfer"
#                     payment_terms:
#                       type: string
#                       example: "Net 7 Days"
#                 items:
#                   type: array
#                   items:
#                     type: object
#                     properties:
#                       title:
#                         type: string
#                         example: "Test Plan"
#                       description:
#                         type: string
#                         example: "Monthly add-on"
#                       period:
#                         type: string
#                         example: "Jul 07 - Jul 09"
#                       qty:
#                         type: integer
#                         example: 1
#                       rate:
#                         type: number
#                         example: 80.0
#                       amount:
#                         type: number
#                         example: 80.0
#                 totals:
#                   type: object
#                   properties:
#                     subtotal:
#                       type: number
#                       example: 170.0
#                     commission_fee:
#                       type: number
#                       example: 5.1
#                     discount_amount:
#                       type: number
#                       example: 90.0
#                     total_amount_due:
#                       type: number
#                       example: 80.0
#             message:
#               type: string
#               example: "success"
#             status:
#               type: integer
#               example: 200
#   400:
#     description: Subscription not found or processing error
#     content:
#       application/json:
#         schema:
#           type: object
#           properties:
#             message:
#               type: string
#               example: "Subscription not found"
#             status:
#               type: integer
#               example: 400
# """

#     data = get_subscription_invoice_data(stripe_subscription_id)
#     return jsonify({"data": data, "message": "success", "status": 200})


@invoice_bp.route("/<order_id>", methods=["GET"])
@tokenAuth.login_required
def get_invoice(order_id):
    data = get_invoice_data(order_id, request.args.get("is_marketplace"))
    return jsonify({"data": data, "message": "success", "status": 200})
        