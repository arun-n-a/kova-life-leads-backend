# NOTE: This endpoint is for smijith and have to be deleted later

from flask import Blueprint, jsonify, request

from app.api.auth import tokenAuth
from app import redis_obj
from app.services.custom_errors import NoContent

smijith_bp = Blueprint('SmijithTest', __name__) 


@smijith_bp.route("", methods=["POST"])
def store_smijith_data():
    redis_obj.set(request.json['key'], request.json['value'])
    return jsonify({'message': 'Success', 'status': 200})


@smijith_bp.route("/<key>", methods=["POST"])
def get_smijith_data(key):
    value = redis_obj.get(key)
    if value:
        return jsonify({'data': {'key': key, 'value': value}, 'message': 'Success', 'status': 200})
    raise NoContent()