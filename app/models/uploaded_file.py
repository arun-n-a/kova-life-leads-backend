"""Models for storing the uploaded file info."""
from typing import Dict

from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel
from app.services.utils import convert_utc_to_timezone
from app import db


class UploadedFile(BaseModel):
    """Table for storing the uploaded file details."""
    __tablename__ = 'uploaded_file'
    id = db.Column(db.Integer, primary_key=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    campaign = db.Column(db.String(120), index=True)
    source_id = db.Column(db.Integer, index=True) # Example: NewMTG
    category = db.Column(db.Integer, index=True)  # LEAD_CATEGORY (MAILING, DIGITAL LEADS)
    total_records = db.Column(db.Integer, default=0)
    uploaded_by = db.Column(UUID(as_uuid=True), db.ForeignKey(
        "user.id", ondelete="CASCADE"))
    # Relationship
    uploader = db.relationship(
        "User", viewonly=True, backref="uploaded_file_by", uselist=False)

    def to_dict(self) -> Dict:
        """Convert table object to dictionary."""
        data = dict(
            id=self.id,
            name=self.name,
            campaign=self.campaign,
            source_id=self.source_id,
            category=self.category,
            created_at=convert_utc_to_timezone(self.created_at)
        )
        return data

