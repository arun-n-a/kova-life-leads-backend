from uuid import uuid4

from sqlalchemy import Sequence
from sqlalchemy.dialects.postgresql import UUID

from app import db
from .base import BaseModel


class SupportTicket(BaseModel):
    __tablename__ = "support_ticket"

    seq = Sequence('support_ticket_id', start=1001)
    id = db.Column(db.Integer, seq, primary_key=True, index=True)
    name= db.Column(db.String(60))
    email= db.Column(db.String(50), index=True, nullable=True)
    phone = db.Column(db.BigInteger, index=True, nullable=True)
    alternate_email= db.Column(db.JSON, default=[])
    is_assigned = db.Column(db.Boolean, default=False)
    ticket_owner = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id"), nullable=True)
    transferred_by = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id"), nullable=True)
    priority = db.Column(db.Integer) # 1: high, 2: Medium, 3: low
    status = db.Column(db.Integer)   # 1.new, 2.open, 3.pending, 4.resolved, 5. closed
    ticket_category = db.Column(UUID(as_uuid=True), db.ForeignKey('ticket_category.id', ondelete="CASCADE"), nullable=True)
    subject = db.Column(db.Text)
    description = db.Column(db.Text)
    flag_evidence = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Integer, nullable=True, default=None)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('user.id', ondelete="CASCADE"), nullable=True)


class SupportHistory(BaseModel):
    __tablename__ = 'support_history'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    support_id = db.Column(db.Integer, db.ForeignKey("support_ticket.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_owner = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id"), nullable=True)
    new_owner = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id"), nullable=True)
    transferred_by = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id"), nullable=True)
    is_transferred = db.Column(db.Boolean, default=False)
    status = db.Column(db.Integer)   # 1.new, 2.open, 3.pending, 4.resolved, 5. closed
    

class TicketCategory(BaseModel):
    __tablename__ = 'ticket_category'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = db.Column(db.String(60))
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('user.id', ondelete="CASCADE"), nullable=True)