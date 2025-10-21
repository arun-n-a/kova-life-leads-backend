from uuid import uuid4
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from app import db
from app.models.base import BaseModel

class SendgridLog(BaseModel):
    __tablename__ = 'sendgrid_log'
    id = db.Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    event = db.Column(db.Integer, nullable=False) # 1: User Invitation, 2: Reset Password, 3: 
    sid = db.Column(db.String(50), nullable=True)
    error = db.Column(db.Text)
