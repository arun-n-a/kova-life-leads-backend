from datetime import timedelta
from uuid import uuid4
from typing import Optional, Dict
from sqlalchemy.dialects.postgresql import UUID
from flask_httpauth import HTTPBasicAuth
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import (
    generate_password_hash, check_password_hash
    )

from app import db, redis_obj
from app.models.base import BaseModel
from app.services.utils import convert_utc_to_timezone
from config import Config_is


auth = HTTPBasicAuth()

class User(BaseModel):
    __tablename__ = 'user'
    """
    User Model
    """
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Credential
    email = db.Column(db.String(75), unique=True, nullable=False)
    hashed_password = db.Column(db.Text)

    # User information
    name = db.Column(db.String(60), index=True)
    phone = db.Column(db.String(15))
    role_id = db.Column(db.Integer, default=2, nullable=False) # USER_ROLE

    agency_name = db.Column(db.String(200))
    is_invited = db.Column(db.Boolean, default=False)
    registered = db.Column(db.Boolean, default=False, index=True)
    invited_at = db.Column(db.DateTime, nullable=True)
    registered_at = db.Column(db.DateTime, nullable=True)
    deactivated_at = db.Column(db.DateTime, nullable=True, index=True)
    avatar = db.Column(db.String(75), default=None)
    user_intents = db.Column(db.Boolean, default=False)

    states_chosen = db.Column(db.JSON, default=[])  # Active territories
    
    # SMS and Email Subscription
    # False if the user unsubscribe SMS
    sms_subscribed = db.Column(db.Boolean, default=True)
    # False if the user unsubscribe email
    email_subscribed = db.Column(db.Boolean, default=True)

    stripe_customer_id = db.Column(db.String(40), unique=True, nullable=True)
    # Relationships
    files_uploaded = db.relationship(
        "UploadedFile", backref="user_uploaded_files", lazy=True)
    agents = db.relationship("Agent", backref="user_agents", lazy=True)

    def login_to_dict(self):
        """
        Logged-in user info from object to dict
        """
        data = dict(
            id=self.id,
            name=self.name,
            email=self.email,
            role_id=self.role_id,
            phone=self.phone,
            avatar= f"https://{Config_is.S3_BUCKET_NAME}.s3.us-east-1.amazonaws.com/{Config_is.ENVIRONMENT}/avatar/{self.avatar}" if self.avatar else None,
            # operating_states=self.operating_states,
            agents=[a.to_dict() for a in self.agents],
            agency_name=self.agency_name,
            stripe_customer_id = self.stripe_customer_id
        )
        return data

    def to_dict(self):
        """Convert model object to dictionary."""
        data = dict(
            id=self.id,
            name=self.name,
            email=self.email,
            phone=self.phone,
            avatar= f"https://{Config_is.S3_BUCKET_NAME}.s3.us-east-1.amazonaws.com/{Config_is.ENVIRONMENT}/avatar/{self.avatar}" if self.avatar else None,
            is_active=self.is_active,
            is_invited=self.is_invited,
            registered=self.registered,
            agency_name=self.agency_name,
            role_id=self.role_id,
            # operating_states=self.operating_states,
            modified_at=convert_utc_to_timezone(self.modified_at),
            created_at=convert_utc_to_timezone(self.created_at),
            agents=[a.to_dict() for a in self.agents]
        )
        return data

    def basic_to_dict(self):
        """
        Basic user details
        """
        data = dict(
            id=self.id,
            name=self.name
        )
        return data

    @staticmethod
    def get_hashed_password(password: str):
        """
        Hash the password
        """
        return generate_password_hash(password)

    def hash_password(self, password: str):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password: str):
        """
        Check password with the hashed password
        """
        return check_password_hash(self.hashed_password, password)

    def generate_auth_token(self, key_ends_with: str, expiration: int, 
                            data: Optional[Dict] = {}) -> str:
        payload = {
            'id': str(self.id), 'name': self.name, 'role_id': self.role_id, 'email': self.email, 
            'agency_name': self.agency_name, 'agents': [i.id for i in self.agents], 
            'agents_source': {1: {}, 2: {}}, 'digital_agent_ids': [], 'phone': self.phone,
            'mailing_agent_ids': [], "stripe_customer_id": self.stripe_customer_id}
            
        if data:
            payload |= data
        for i in self.agents:
            payload['agents_source'][i.source][i.category] = i.id
            if i.category == 1:
                payload['mailing_agent_ids'].append(i.id)
            elif i.category == 2:
                payload['digital_agent_ids'].append(i.id)
        serializer = URLSafeTimedSerializer(Config_is.SECRET_KEY)
        token = serializer.dumps(payload)
        add_user_token_in_cache(f"{self.id}_{key_ends_with}", expiration, token)
        return token

    @staticmethod
    def verify_auth_token(key_ends_with: str, token: str, expires_in: int = Config_is.AUTH_TOKEN_EXPIRES):
        """
        Verifying the user token valid or not
        """
        serializer = URLSafeTimedSerializer(Config_is.SECRET_KEY)
        try:
            data = serializer.loads(token)
            data = serializer.loads(token, max_age=expires_in)
            if verify_user_token_in_cache(f"{data['id']}_{key_ends_with}", token):
                return data
            return data
        except Exception as e:
            print(str(e))
        return False


def add_user_token_in_cache(key: int, expiry_at: int, user_auth_token: str) -> bool:
    redis_obj.setex(key, timedelta(seconds=expiry_at), user_auth_token)
    return True


def verify_user_token_in_cache(key: str, user_auth_token: str) -> bool:
    if redis_obj.get(key) == user_auth_token:
        return True
    return False


def remove_user_token(key: str, user_auth_token: Optional[str] = None):
    """
    Remove user token from redis
    """
    print(key)
    if user_auth_token:
        if redis_obj.get(key) == user_auth_token:
            redis_obj.delete(key)
    else:
        redis_obj.delete(key)
    return True


def logout_user_from_all_devices(user_id: str) -> bool:
    """
    Remove user all tokens from redis
    """
    keys = redis_obj.keys(f"{user_id}_*")
    for key in keys:
        redis_obj.delete(key)
    return True
