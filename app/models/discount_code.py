"""Models for storing the PromoCode details."""
from uuid import uuid4

from sqlalchemy.dialects.postgresql import UUID

from app import db
from app.models.base import BaseModel


class CouponCode(BaseModel):
    """
    Store stripe CouponCode details
    """
    __tablename__ = "coupon_code"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    stripe_coupon_id = db.Column(db.String(40), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.String(10), nullable=False)  # forever, once, or repeating
    percent_off = db.Column(db.Integer, nullable=True)
    is_used_in_marketplace = db.Column(db.Boolean, default=False) # this will flag whether this code is used in the marketplace or stripe subscription
    amount_off = db.Column(db.Integer, nullable=True)
    max_redemptions = db.Column(db.Integer) # Maximum number of times this coupon can be redeemed, in total, across all customers, before it is no longer valid.
    redeem_by = db.Column(db.DateTime)  # Date after which the coupon can no longer be redeemed.
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"))
    is_deleted = db.Column(db.Boolean, default=False, index=True)

class CouponAssignedProduct(BaseModel):
    """
    Specify coupon codes to specific products only
    """
    __tablename__ = "coupon_assigned_product"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    pricing_id = db.Column(UUID(as_uuid=True), db.ForeignKey("pricing_detail.id", ondelete="CASCADE"))
    coupon_code_id = db.Column(UUID(as_uuid=True), db.ForeignKey("coupon_code.id", ondelete="CASCADE"), index=True)


class PromotionCode(BaseModel):
    """
    Store stripe promotion code
    """
    __tablename__ = "promotion_code"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    stripe_promotion_id = db.Column(db.String(40), nullable=True)
    code = db.Column(db.String(50), nullable=False)
    coupon_code_id = db.Column(UUID(as_uuid=True), db.ForeignKey("coupon_code.id", ondelete="CASCADE"), index=True)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"), index=True)
    expires_at = db.Column(db.DateTime)
    max_redemptions = db.Column(db.Integer)
    is_public = db.Column(db.Boolean, default=False)
    restrictions_first_time_transaction = db.Column(db.Boolean, default=False)
    restrictions_minimum_amount = db.Column(db.Integer)
    is_deleted = db.Column(db.Boolean, default=False, index=True)

class UserPromotionCodeAssignment(BaseModel):
    """
    Represents the assignment of a promotion code to a user.
    """
    __tablename__ = "user_promotion_code"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    promotion_id = db.Column(UUID(as_uuid=True), db.ForeignKey("promotion_code.id", ondelete="CASCADE"), index=True)
    coupon_code_id = db.Column(UUID(as_uuid=True), db.ForeignKey("coupon_code.id", ondelete="CASCADE"), index=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"), index=True)


class UserPromotionCodeHistory(BaseModel):
    """
    Stores the history of promotions assigned to users.
    """
    __tablename__ = "user_promotion_code_history"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    promotion_id = db.Column(UUID(as_uuid=True), db.ForeignKey("promotion_code.id", ondelete="CASCADE"), index=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"), index=True)
    pricing_id = db.Column(UUID(as_uuid=True), db.ForeignKey("pricing_detail.id", ondelete="CASCADE"), index=True)
    subscription_order_id = db.Column(UUID(as_uuid=True), db.ForeignKey("subscription_order_summary.id", ondelete="CASCADE"), nullable=True, index=True)
    marketplace_order_id = db.Column(UUID(as_uuid=True), db.ForeignKey("marketplace_order_summary.id", ondelete="CASCADE"), nullable=True, index=True)

# id
# user_id
# subscription_order_id
# marketplace_order_id

# class UserPromotionCode(BaseModel):
#     """
#     Promotion code assigned to the customers
#     """
#     __tablename__ = "user_promotion_code"
#     id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
#     promotion_id = db.Column(UUID(as_uuid=True), db.ForeignKey("promotion_code.id", ondelete="CASCADE"), index=True)
    

# class UserPromoRedemptionHistory(BaseModel):
#     """
#     Keep the purchase history to track the discount code 
#     """
# class PromoCodeBeneficiary(BaseModel):
#     __tablename__ = "promo_code_beneficiary"
#     id = db.Column(db.Integer, primary_key=True, index=True)
#     user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"))
#     promo_code_id = db.Column(UUID(as_uuid=True), db.ForeignKey("promo_code.id", ondelete="CASCADE"),
#                                 index=True)
#     used_count = db.Column(db.Integer, default=0)
#     # Relationship
#     user_info = db.relationship("User", viewonly=True, backref="promo_assigned_for", uselist=False)
#     promo_code_info = db.relationship("PromoCode", viewonly=True, backref="assigned_promo_code_info", uselist=False)
