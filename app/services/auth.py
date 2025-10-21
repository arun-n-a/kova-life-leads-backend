from functools import wraps
from typing import Dict, Tuple
from datetime import datetime

from flask import g
from sqlalchemy.orm import Query

from app.services.custom_errors import *
from app.services.crud import CRUD
from app.services.utils import discard_crucial_user_data
from app.models import (
    User, remove_user_token, 
    logout_user_from_all_devices
    )
from app.services.stripe_service import StripeService


class AuthService:
    @staticmethod
    def user_obj_state_validation(user_obj: Query) -> bool:
        if not user_obj:
            raise NoContent("Please enter a valid email address.")
        if not user_obj.registered:
            raise Forbidden("Please complete the registration process")
        if not user_obj.is_active:
            raise Forbidden('Your account has been suspended. Please contact the admin')
        return True

    @staticmethod
    def forgot_password(email: str, expires_in=3600) -> str:
        g.user = User.query.filter_by(email=email).first()
        AuthService.user_obj_state_validation(g.user)
        token = g.user.generate_auth_token('forgot_pwd', expires_in)
        return token

    @staticmethod
    def new_invitee(data: Dict) -> bool:
        """
        User registration from email invitation
        """
        print(g.user)
        user_obj = User.query.filter_by(id=g.user["id"]).first()
        print(user_obj)
        user_obj.hash_password(data.pop("password"))
        data = discard_crucial_user_data(['role_id', 'email'], data)
        if not user_obj.stripe_customer_id:
            user_obj.stripe_customer_id = StripeService().create_customer(user_obj)
        elif data.get('name') and data.get('name') != user_obj.name:
            StripeService().update_customer(user_obj.stripe_customer_id, data.get('name', user_obj.name))
        CRUD.update(
            User, {"id": user_obj.id}, {"registered": True, "registered_at": datetime.utcnow(), "is_active": True, **data}
        )
        remove_user_token(f"{user_obj.id}_invitation")
        return True

    @staticmethod
    def new_password(user_id: str, password: str) -> bool:
        user_obj = User.query.get(user_id)
        user_obj.hash_password(password)
        CRUD.db_commit()
        logout_user_from_all_devices(user_id)
        return True


def admin_authorizer(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if g.user["role_id"] == 1:
            return func(*args, **kwargs)
        raise Forbidden()

    return inner
