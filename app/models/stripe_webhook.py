from uuid import uuid4

from sqlalchemy.dialects.postgresql import UUID

from app import db
from app.models.base import BaseModel


class StripeWebhook(BaseModel):
    __tablename__ = 'stripe_webhook'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    payment_id = db.Column(db.String(60), nullable=True)
    subscription_id = db.Column(db.String(60), nullable=True)
    payload = db.Column(db.JSON, default={})
    event = db.Column(db.String(100))