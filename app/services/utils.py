import re
import string
import json
from datetime import (
    timedelta, datetime
    )
from random import choice
from zoneinfo import ZoneInfo
from typing import (Union, Dict, List, Optional)

from flask import request
from cryptography.fernet import Fernet
from app.services.custom_errors import *
from app import redis_obj
from config import Config_is


def generate_short_code(length: int = 7) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(choice(characters) for _ in range(length))

def encrypt(message: str) -> str:
    return Fernet(Config_is.CRYPTO_KEY).encrypt(
        message.encode("ascii")).decode("ascii")


def decrypt(encrypted_message: str) -> Union[str, None]:
    try:
        return (
            Fernet(Config_is.CRYPTO_KEY).decrypt(
                encrypted_message.encode("ascii")).decode("ascii")
        )
    except:
        # Invalid encrypted message
        return None


def convert_utc_to_timezone(dt: datetime, time_zone: str = Config_is.TIME_ZONE) -> str:
    try:
        return datetime.strftime(
            dt.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(time_zone)), 
            "%m-%d-%Y %H:%M:%S")
    except (TypeError, AttributeError):
        return

def date_object_to_string(dt: datetime.date) -> str:
    try:
        return datetime.strftime(dt, '%m-%d-%Y')
    except (TypeError, AttributeError):
        return

def convert_datetime_to_timezone_date(utc_now: datetime, time_zone: str = Config_is.TIME_ZONE) -> datetime.date:
    return utc_now.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(time_zone)).date()

def get_current_date_time(utc_now: datetime, time_zone: str = Config_is.TIME_ZONE) -> datetime.date:
    return utc_now.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(time_zone))


def convert_timezone_to_utc(dt_object: datetime, time_zone: str = Config_is.TIME_ZONE) -> datetime:
    """
    Converts a datetime object from a specific timezone to UTC.

    Args:
        dt_object (datetime.datetime): The datetime object to convert.
                                       It should be naive (without timezone information).
        time_zone (str): The string representation of the source timezone
                                   (e.g., 'America/New_York', 'Asia/Kolkata').

    Returns:
        datetime.datetime: The datetime object converted to UTC.
    """
    try:
        return dt_object.replace(tzinfo=ZoneInfo(time_zone)).astimezone(ZoneInfo('UTC'))
    except:
        return
def email_format_validation(email: str) -> str:
    """
    Checks whether the email addresses are in the proper format or not.
    """
    match = re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", email, re.I)
    if match:
        return email.lower()
    raise BadRequest("Please give a valid email address.")


def add_redis_ttl_data(key: str, hours: float, 
                       data: Union[Dict, int, str]) -> bool:
    try:
        if isinstance(data, Dict):
            data = json.dumps(data)
        redis_obj.setex(key, timedelta(hours=hours), data)
        return True
    except Exception as e:
        print(f"add_redis_ttl_data {key} {data} {e}")
    return False


def discard_crucial_user_data(discarded_inputs: Dict, data: Dict) -> Dict:
    if any(data.get(k) for k in discarded_inputs):
        for k in discarded_inputs:
            data.pop(k, None)
    return data


def date_time_obj_to_str(dt: Optional[datetime]) -> str:
    try:
        return datetime.strftime(dt, "%m-%d-%Y %H:%M:%S")
    except TypeError:
        return
    
def utc_to_timezone_conversion(dt: datetime, timezone: str = Config_is.TIME_ZONE) -> datetime:
    try:
        return dt.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(timezone))
    except TypeError:
        return

def fetch_login_user_data(current_history: List) -> Dict:
    """
    Gets the client's IP address and browser details from the request headers.
    """
    if 'X-Forwarded-For' in request.headers:
        data = {
            "ip_address": request.headers['X-Forwarded-For'].split(',')[0]
            }
    else:
        data = {"ip_address": request.remote_addr}
    data['user_agent'] = request.headers.get('User-Agent')
    current_history.append(data)
    return current_history[-5:]
