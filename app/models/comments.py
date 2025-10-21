from uuid import uuid4

from sqlalchemy.dialects.postgresql import UUID

from app import db
from .base import BaseModel


class Comments(BaseModel):
    __tablename__ = "comments"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticket_id = db.Column(db.Integer, db.ForeignKey("support_ticket.id"), nullable=False)
    attachment = db.Column(db.String, nullable=True)
    message = db.Column(db.Text, nullable=True)
    send_notification =db.Column(db.Boolean, nullable=True)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)