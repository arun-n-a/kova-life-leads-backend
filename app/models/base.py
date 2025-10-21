from datetime import datetime

from app import db


class BaseModel(db.Model):
    __abstract__ = True
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    modified_at = db.Column(db.DateTime, default=db.func.now(),
                           onupdate=datetime.utcnow, index=True)
