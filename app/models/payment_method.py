from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from app import db
from app.models import BaseModel

class PaymentMethod(BaseModel):
    """Stored payment methods"""
    __tablename__ = 'payment_method'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"))
    stripe_payment_method_id = db.Column(db.String(255), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref=db.backref('payment_method', lazy=True))
