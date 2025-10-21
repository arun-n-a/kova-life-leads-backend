from datetime import datetime
from uuid import uuid4

from sqlalchemy import UUID

from app import db
from app.models import BaseModel


class Notification(BaseModel):
    __tablename__ = "notification"    
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    message = db.Column(db.Text, nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey("support_ticket.id"), nullable=False, index=True)
    event = db.Column(db.Integer, nullable=True)

class NotifyMember(BaseModel):
    __tablename__ = 'notify_member'    
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_id = db.Column(UUID(as_uuid=True), db.ForeignKey("notification.id", ondelete="CASCADE"), nullable=False, index=True)
    viewed = db.Column(db.Boolean, default=False)