"""Models for storing the Stripe customer Subscription details."""
from uuid import uuid4

from app import db
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel

class StripeCustomerSubscription(BaseModel):
    """Table for storing the Stripe customer Subscription details"""
    __tablename__ = "stripe_customer_subscription"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    stripe_subscription_id = db.Column(db.String(40), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    unit_price = db.Column(db.Float, nullable=True)
    net_price = db.Column(db.Float, nullable=True)
    total_amount = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(120))
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"))
    pricing_id = db.Column(UUID(as_uuid=True), db.ForeignKey("pricing_detail.id", ondelete="CASCADE"), nullable=True, index=True)
    stripe_price_id = db.Column(db.String(40), nullable=True)
    stripe_product_id = db.Column(db.String(40), nullable=True)
    started_at = db.Column(db.DateTime) 
    cancel_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    cancelation_reason = db.Column(db.Text)
    acknowledgment_id = db.Column(UUID) # TODO: delete
    accepted_terms_and_conditions = db.Column(db.Boolean, default=False)
    states_chosen = db.Column(db.JSON, default=[])
    # discount
    # selected_states = db.Columnd(db.JSON, default=[])
    # user_info = db.relationship("User", viewonly=True, backref="user_info_shopping", uselist=False)
    # pricing_info = db.relationship("PricingDetail", viewonly=True, backref="shoppingcart_lead_type", uselist=False)
