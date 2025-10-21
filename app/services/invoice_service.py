from datetime import (datetime, timedelta)
from typing import Dict
import json

from sqlalchemy import func
from flask import g

from app import db
from app.models import (
    MarketplaceOrderSummary as MOS,
    PricingDetail as PD,
    ShoppingCart as SC,
    StripeWebhook,
    SubscriptionOrderSummary as SOS,
    User,
)
from constants import (
    STRIPE_COMMISSION_FEE,
    COMPANY_INVOICE_ADDRESS
    )
from config import Config_is


# def get_subscription_invoice_data(stripe_subscription_id: str) -> Dict:
#     sub_obj = (
#         SOS.query
#         .join(User, SOS.user_id == User.id)
#         .with_entities(
#             SOS.invoice_id,SOS.created_at, SOS.amount_received, 
#             SOS.original_price, SOS.discounted_price, 
#             SOS.description, User.name, User.agency_name,
#             User.phone, User.email
#             )
#         .filter(
#             SOS.stripe_subscription_id == stripe_subscription_id
#             )
#         ).first()
#     period_str = f"{sub_obj.created_at.strftime('%b %d, %Y')} - {(sub_obj.created_at + timedelta(days=((Config_is.RENEWAL_DAY_OF_WEEK - sub_obj.created_at.weekday()) % 7 or 7))).strftime('%b %d, %Y')}"     
#     discount = (sub_obj.original_price - sub_obj.discounted_price) if sub_obj.discounted_price  else 0
#     commission_fee = round((sub_obj.discounted_price or sub_obj.original_price) * STRIPE_COMMISSION_FEE, 2)
#     # total_due = sub_obj.amount_received + commission_fee
#     invoice_data = {
#         "invoice_number": f"INV-{sub_obj.created_at.strftime('%Y%m%d')}-{sub_obj.invoice_id}",
#         "invoice_date": sub_obj.created_at.strftime("%B %d, %Y"),
#         "date": sub_obj.created_at.strftime("%B %d, %Y"),
#         "due_date": (sub_obj.created_at + timedelta(days=15)).strftime("%B %d, %Y"),
#         "from": COMPANY_INVOICE_ADDRESS,
#         "bill_to": {
#             "name": sub_obj.name,
#             "agency": sub_obj.agency_name,
#             "phone": sub_obj.phone,
#             "email": sub_obj.email
#         },
#         "payment_details": {
#             "payment_terms": "Net 7 Days",
#             "method": "Bank Transfer",
#             "bank_name": "First National Bank"
#         },
#         "item": {
#             "title": sub_obj.description.split(' (at')[0 ].split(' × ')[0],
#             # "description": sub_obj.description ,
#             "period": period_str,
#             "rate": sub_obj.original_price,
#             "amount_received": sub_obj.amount_received,
#             "discounted_price": sub_obj.discounted_price
#         },
#         "commission_fee": commission_fee,
#         "discount_amount": discount
#     }
#     return invoice_data



def get_invoice_data(order_id: str, is_marketplace: str) -> Dict:
    user_filter = []
    if g.user['role_id'] != 1:
        if is_marketplace == "1":
            user_filter = [MOS.user_id == g.user['id']]
        else:
            user_filter = [SOS.user_id == g.user['id']]
    if is_marketplace == "1":
        result = (
            MOS.query
            .with_entities(
                MOS.id, MOS.user_id, MOS.stripe_payment_id,
                MOS.local_purchase_date, MOS.invoice_id,
                MOS.total_amount, MOS.discounted_price,
                MOS.amount_received, MOS.payment_status,
                MOS.invoice_data
            )
            .filter(MOS.id == order_id, *user_filter)
            .first()
        )
    else:
        result = (
            SOS.query
            .with_entities(
                SOS.id, SOS.user_id, SOS.stripe_subscription_id,
                SOS.invoice_id, SOS.discounted_price, 
                SOS.discounted_price, SOS.amount_received, 
                SOS.subtotal_amount.label('subtotal'),
                SOS.payment_status, SOS.invoice_data
            )
            .filter(SOS.id == order_id, *user_filter)
            .first()
        )
    return result._asdict()
    

