from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID

from app import db
from .base import BaseModel



class FAQ(BaseModel):
    __tablename__ = 'faq'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    question = db.Column(db.String(220), unique=True, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    view_count = db.Column(db.Integer, default=None, nullable=True)
    category_id = db.Column(UUID(as_uuid=True), db.ForeignKey('ticket_category.id', ondelete="CASCADE"))
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('user.id', ondelete="SET NULL"), nullable=True)


class FAQVote(BaseModel):
    __tablename__ = "faq_vote"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    faq_id = db.Column(UUID(as_uuid=True), db.ForeignKey("faq.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), nullable=False)
    is_helpful = db.Column(db.Boolean, nullable=False)

# class FAQCategory(BaseModel):
#     __tablename__ = 'faq_category'
#     id = db.Column(db.Integer, primary_key=True, index=True)
#     name = db.Column(db.String(120), nullable=False, index=True)
#     is_crm = db.Column(db.Boolean, index=True)
#     created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"))

#     # relationship
#     creator_info = db.relationship("User", viewonly=True, backref="faq_category_creator", uselist=False)
#     faqs = db.relationship("FAQ", backref="faq_category_list", cascade="all,delete")


# class FAQ(BaseModel):
#     __tablename__ = 'faq'
#     id = db.Column(db.Integer, primary_key=True, index=True)
#     question = db.Column(db.Text, nullable=False)
#     answer = db.Column(db.Text, nullable=False)
#     files_uploaded = db.Column(db.Boolean, default=False)
#     category_id = db.Column(db.Integer, db.ForeignKey("faq_category.id", ondelete="CASCADE"), nullable=True, index=True)
#     created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"))

#     # relationship
#     category_info = db.relationship("FAQCategory", viewonly=True, backref="faq_assigned_category", uselist=False)
#     creator_info = db.relationship("User", viewonly=True, backref="faq_creator", uselist=False)

