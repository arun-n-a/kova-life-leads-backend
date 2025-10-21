"""
There is no signup option but interested users can submit their details and admin will be the decison maker
"""
from uuid import uuid4

from sqlalchemy.dialects.postgresql import UUID

from app import db
from app.models.base import BaseModel


class InterestedUser(BaseModel):
    __tablename__ = 'interested_user'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4,index=True )
    email = db.Column(db.String(75), unique=True, nullable=False)
    payload = db.Column(db.JSON, default={})
    rejection_message = db.Column(db.Text, nullable=True)
