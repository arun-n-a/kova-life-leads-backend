"""Models for storing the shopping cart details."""
from uuid import uuid4

from app import db
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class ShoppingCart(BaseModel):
    __tablename__ = "shopping_cart"
    """Table for storing the shopping cart details"""
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    state = db.Column(db.String(30))
    quantity = db.Column(db.Integer, default=1)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"))
    pricing_id = db.Column(UUID(as_uuid=True), db.ForeignKey("pricing_detail.id", ondelete='SET NULL'), nullable=True, index=True)
    # payload = db.Column(db.JSON, default=[])
    completed = db.Column(db.Boolean, nullable=False)
    description = db.Column(db.String(230), nullable=True)
    month = db.Column(db.Integer, nullable=False)
    order_id = db.Column(UUID(as_uuid=True), db.ForeignKey("marketplace_order_summary.id", ondelete='SET NULL'), nullable=True, index=True)
    # user_info = db.relationship("User", viewonly=True, backref="user_info_shopping", uselist=False)
    # pricing_info = db.relationship("PricingDetail", viewonly=True, backref="shoppingcart_lead_type", uselist=False)


    # def to_dict(self):
    #     data = dict(
    #         id=self.id,
    #         state=self.state,
    #         quantity=self.quantity,
    #         month=self.month,
    #         type_=self.type_,
    #         pricing_info=self.pricing_info.to_dict()
    #     )
    #     return data
