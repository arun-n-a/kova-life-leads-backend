from datetime import datetime
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID

from app import db
from app.models import BaseModel


class PricingDetail(BaseModel):
    """Stored pricing details"""
    __tablename__ = 'pricing_detail'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"))
    category = db.Column(db.Integer, nullable=False, index=True)  # LEAD_CATEGORY key
    is_fresh_leads = db.Column(db.Boolean , default=False, index=True) # True: Upload fresh leads
    completed = db.Column(db.Boolean, default=False, index=True) # for  is_fresh_leads this column is invalid
    source = db.Column(db.Integer, nullable=False)  # LEAD_CATEGORY value key sources
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    month = db.Column(db.Integer, nullable=True)
    unit_price = db.Column(db.Float, nullable=False)
    net_price = db.Column(db.Integer)
    quantity=db.Column(db.Integer, default=0)
    is_recurring = db.Column(db.Boolean, default=False)
    stripe_product_id = db.Column(db.String(40))
    stripe_price_id = db.Column(db.String(40))


class StripePriceId(BaseModel):
    """Store the strip pricing details"""
    __tablename__ = 'stripe_price_id'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    pricing_id = db.Column(UUID(as_uuid=True), db.ForeignKey("pricing_detail.id", ondelete="CASCADE"))
    stripe_price_id = db.Column(db.String(40))

