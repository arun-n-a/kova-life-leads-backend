"""Models for storing the uploaded mailing file contents."""

from datetime import datetime
from sqlalchemy import Sequence
from sqlalchemy.dialects.postgresql import UUID

from app import db
from app.models.base import BaseModel

class MailingLead(BaseModel):
    __tablename__ = "mailing_lead"
    """Table for storing the Mailing Leads from the input CSV file"""
    mortgage_id = db.Column(db.String(30), primary_key=True, index=True)
    temp_mortgage_id = db.Column(db.String(14), nullable=True, index=True)
    uuid = db.Column(db.String(10), index=True)
    file_id = db.Column(db.Integer, db.ForeignKey(
        "uploaded_file.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = db.Column(db.Integer, db.ForeignKey(
        "agent.id", ondelete='SET NULL'), nullable=True, index=True)
    city = db.Column(db.String(100), index=True)
    state = db.Column(db.String(60), index=True)
    zip = db.Column(db.String(10))
    full_name = db.Column(db.String(120), index=True)
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))
    loan_date = db.Column(db.Date)
    loan_amount = db.Column(db.Float)
    lender_name = db.Column(db.String(200))
    loan_type = db.Column(db.String(100))
    csv_data = db.Column(db.JSON, default={})
    address = db.Column(db.String(230), index=True)
    # (1: 'not a duplicate', 2: old duplicate, 3: latest duplicate call received)
    duplicate_status = db.Column(db.Integer, default=0, index=True)
    created_date = db.Column(db.Date, index=True)  # Store US/Pacific date
    last_purchased_date = db.Column(db.Date, index=True)
    # marketplace
    source_id = db.Column(db.Integer, index=True)
    can_sale = db.Column(db.Boolean, default=True, index=True)
    disabled_in_marketplace = db.Column(db.Boolean, default=False, index=True) # as required we can disable specific leads from the marketplace
    is_in_checkout = db.Column(db.Boolean, default=False, index=True)
    shopping_cart_temp_id = db.Column(db.String(45), index=True) # temporary storage
    item_reserved_temp_by = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id"), index=True, nullable=True) # temporary storage of a

    # relationship
    file_info = db.relationship(
        "UploadedFile", viewonly=True, backref="mailing_lead_file_info", uselist=False)
    lead_assigned_members = db.relationship("MailingAssignee", backref="mailing_lead_owners", 
                                            order_by="desc(MailingAssignee.created_at)")
    agent_info = db.relationship(
        "Agent", viewonly=True, backref="mailing_lead_initial_owner", uselist=False)
    # mailing_response = db.relationship("MailingResponse", backref="mailing_response_fetch", cascade="all,delete", uselist=False)
    

class MailingResponse(BaseModel):
    __tablename__ = "mailing_response"

    id = db.Column('id', db.Integer, primary_key=True, index=True)
    completed = db.Column(db.Boolean, default=False, index=True)
    call_in_date_time = db.Column(db.DateTime, index=True)
    ivr_response = db.Column(db.JSON, default={})
    ivr_logs = db.Column(db.JSON, default=[])
    # caller = db.Column(db.String(60), index=True)
    temp_data = db.Column(db.JSON, default={})
    mortgage_id = db.Column(db.String(30), db.ForeignKey("mailing_lead.mortgage_id", ondelete="CASCADE"), nullable=True, index=True)
    call_sid = db.Column(db.String(60), index=True)
    lead_info = db.relationship(
        "MailingLead", viewonly=True, backref="mailing_response_lead_info", uselist=False)



class MailingAssignee(BaseModel):
    __tablename__ = "mailing_assignee"
    """Table for storing the mailing leads assigned to the agents"""

    id = db.Column('id', db.Integer, primary_key=True, index=True)
    agent_id = db.Column(db.Integer, db.ForeignKey(
        "agent.id", ondelete='SET NULL'), index=True)
    mortgage_id = db.Column(db.String(30), db.ForeignKey(
        "mailing_lead.mortgage_id", ondelete="CASCADE"), nullable=True, index=True)
    lead_status = db.Column(db.Integer, default=1, index=True)
    lead_status_changed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    notes = db.Column(db.Text)
    # Marketplace
    purchased_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"), index=True, nullable=True)
    purchased_date = db.Column(db.Date, index=True)
    campaign_name = db.Column(db.String(60))
    # Suppression
    sold_date = db.Column(db.Date)  # The day when the docs are uploaded
    suppression_rejection_msg = db.Column(db.Text)
    suppressed_by = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete='SET NULL'))
    # The admin user who accepts or reject suppression request
    suppression_approved_by = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete='SET NULL'))
    # Copy Leads
    copied = db.Column(db.Boolean, default=False)
    copied_from_agent_id = db.Column(db.Integer, db.ForeignKey(
        "agent.id", ondelete='SET NULL'), index=True)
    copied_by_user = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete='SET NULL'))
    copied_at = db.Column(db.DateTime, nullable=True)
    # Move leads
    moved = db.Column(db.Boolean, default=False)
    moved_from_agent_id = db.Column(db.Integer, db.ForeignKey(
        "agent.id", ondelete='SET NULL'), index=True)
    moved_by_user = db.Column(UUID(as_uuid=True))
    moved_history = db.Column(db.JSON, default=[])
    moved_at = db.Column(db.DateTime, nullable=True)

    # ghl_client_id = db.Column(db.String(40), index=True)
    # Shopping cart
    cart_item_id = db.Column(UUID(as_uuid=True), db.ForeignKey("shopping_cart.id", ondelete='SET NULL'), index=True)

    # relationship
    lead_info = db.relationship(
        "MailingLead", viewonly=True, backref="lm_lead_mem_lead_info", uselist=False)
    # agent_info = db.relationship(
    #     "Agent", viewonly=True, backref="lead_assigned_to", uselist=False)
    # user_info = db.relationship("User", viewonly=True, backref="lead_member_purchased_user_detail", uselist=False)
    # cart_info = db.relationship("ShoppingCart", viewonly=True, backref="lead_member_shopping_cart_info", uselist=False)


class MailingLeadMemberStatusLog(BaseModel):
    __tablename__ = "mailing_lead_member_status_log"
    """Table for storing the status history"""

    id = db.Column('id', db.Integer, primary_key=True, index=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"), index=True, nullable=True)
    mailing_assignee_id = db.Column(db.Integer, db.ForeignKey(
        "mailing_assignee.id", ondelete="CASCADE"), index=True)
    lead_status = db.Column(db.Integer, default=1, index=True)