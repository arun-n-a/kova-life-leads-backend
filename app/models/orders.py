from uuid import uuid4

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Identity

from app import db
from app.models.base import BaseModel
from app.services.utils import convert_utc_to_timezone


class SubscriptionOrderSummary(BaseModel):
    __tablename__ = 'subscription_order_summary'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4,index=True )
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"))
    is_fresh_leads = db.Column(db.Boolean, default=False)

    stripe_payment_id = db.Column(db.String(100), nullable=True, index=True, unique=True)
    stripe_subscription_id = db.Column(db.String(60), nullable=True, index=True)
    # total_amount = db.Column(db.Float)
    subtotal_amount = db.Column(db.Float)
    invoice_id = db.Column(db.Integer, Identity(start=1000, cycle=False), unique=True, nullable=True) # Invoice Format=INV-{yyyy}{mm}{dd}-{invoice_id}
    
    
    stripe_invoice_id = db.Column(db.String(60), nullable=True)
    discounted_price = db.Column(db.Float, nullable=True)
    amount_received = db.Column(db.Float)
    subscription_db_id = db.Column(UUID(as_uuid=True), db.ForeignKey('stripe_customer_subscription.id', ondelete="CASCADE"), nullable=True)
    promo_code_db_id = db.Column(UUID(as_uuid=True), db.ForeignKey('promotion_code.id', ondelete="CASCADE"), nullable=True)
    # stripe_promotion_id = db.Column(db.String(40))
    stripe_product_id = db.Column(db.String(40))
    stripe_price_id = db.Column(db.String(40))
    description = db.Column(db.String(230), nullable=True)
    invoice_data = db.Column(db.JSON, default={})
    states_chosen = db.Column(db.JSON, default=[])
    # card_brand = db.Column(db.String(40)) # payload['data']['object']['charges']['data'][0]['payment_method_details']['card']['brand']
    # card_expiry_month = payload['data']['object']['charges']['data'][0]['payment_method_details']['card']['exp_year']
    # payload['data']['object']['charges']['data'][0]['payment_method_details']['card']['exp_month']
    # ['data']['object']['charges']['data'][0]['payment_method_details']['card']['last4']
    payment_status = db.Column(db.String(30), index=True)
    alert_sent = db.Column(db.Boolean, default=False)
    
    # discount_code = db.Column(UUID(as_uuid=True), db.ForeignKey("discount_code.id", ondelete="CASCADE"),nullable=True, index=True)
    user_info = db.relationship("User", viewonly=True, backref="user_subscription_order_summary", uselist=False)


class MarketplaceOrderSummary(BaseModel):
    __tablename__ = 'marketplace_order_summary'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4,index=True )
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"))
    stripe_payment_id = db.Column(db.String(100), nullable=True, unique=True)
    # total_amount = db.Column(db.Float)
    # subtotal_amount = db.Column(db.Float)
    local_purchase_date = db.Column(db.Date)
    campaign_name = db.Column(db.String(30), nullable=True)
    stripe_invoice_id = db.Column(db.String(60), nullable=True, unique=True)
    invoice_id = db.Column(db.Integer, Identity(start=1000, cycle=False), unique=True, nullable=True)  # Invoice Format=INV-{yyyy}{mm}{dd}-{invoice_id}
    subtotal = db.Column(db.Float)
    discounted_price = db.Column(db.Float, nullable=True)
    total_amount = db.Column(db.Float)
    amount_received = db.Column(db.Float) # amount received from stripe to account #TODO confitm
    promo_code_db_id = db.Column(UUID(as_uuid=True), db.ForeignKey('promotion_code.id', ondelete="CASCADE"), nullable=True)
    # stripe_promotion_id = db.Column(db.String(40))
    payment_status = db.Column(db.String(30), index=True)
    invoice_data = db.Column(db.JSON, default={})
    # discount_code = db.Column(UUID(as_uuid=True), db.ForeignKey("discount_code.id", ondelete="CASCADE"),nullable=True, index=True)
    user_info = db.relationship("User", viewonly=True, backref="mp_user_order_summary", uselist=False)

