from flask import (
    request, jsonify, Blueprint
    )
from app.api import bp
from app.api.auth import tokenAuth
from app.services.auth import admin_authorizer
from app.services.file_template import (
    add_new_file_template,
    update_file_template,
    list_file_templates,
)

uploader_template_bp = Blueprint('Mortgage file upload fields', __name__)


@uploader_template_bp.route("<int:category>/<int:source>", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def get_templates(category, source):
    data = list_file_templates(category, source)
    return jsonify({"data": data, "message": "success", "status": 200})
# [{'FIRST_NAME': 'First Name'}, {'LAST_NAME': 'Last Name'}, 
#  {'ADDRESS': 'Address'}, {'CITY': 'City'}, {'STATE': 'st'}, {'ZIP': 'Zip'}, 
#  {'LOAN_DATE': 'Loan Date'}, {'LENDER_NAME': 'Lender Name'}, {'LOAN_AMOUNT': 'Loan Amount'}, 
#  {'LOAN_TYPE': 'Loan Type'}, {'AGENT_ID': 'agent_id'}, {'mortgage_id': 'PIN'}, {'FULL_NAME': 'Full Name'}]


@uploader_template_bp.route("", methods=["POST"])
@tokenAuth.login_required
@admin_authorizer
def add_template_data():
    new = add_new_file_template(request.json)
    return jsonify({"data": new, "message": "success", "status": 200})


@uploader_template_bp.route("/<int:id_>", methods=["PUT"])
@tokenAuth.login_required
@admin_authorizer
def update_template_data(id_):
    new = update_file_template(id_, request.json)
    return jsonify({"data": new, "message": "success", "status": 200})
