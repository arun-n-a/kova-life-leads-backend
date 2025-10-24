"""API Endpoints related to user authentication."""
from flask import request, g, render_template, Blueprint
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth

from app.services.custom_errors import *
from app.services.sendgrid_email import SendgridEmailSending
from app.services.auth import AuthService
from app.models import (
    User, remove_user_token
    )
from config import Config_is

basic_auth = HTTPBasicAuth()
tokenAuth = HTTPTokenAuth(scheme="Bearer")

auth_bp = Blueprint("auth", __name__)


@basic_auth.verify_password
def verify_password(email: str, password: str) -> bool:
    """
    Verify user email and password in login.
    param email: email address string entered by user in login
    param password: String password entered by user during login
    return: True matched email and password
    """
    user_obj = User.query.filter_by(email=email).first()
    if not (user_obj and user_obj.hashed_password):
        raise BadRequest("Incorrect Email or password")
    AuthService.user_obj_state_validation(user_obj)
    if user_obj.check_password(password):
        g.user = user_obj
        return True
    raise BadRequest("Please enter correct password")


@tokenAuth.verify_token
def verify_token(token: str) -> bool:
    if not token:
        token = str(request.headers.get('Authorization', ''))
    if token:
        user_is = User.verify_auth_token(request.headers.get('X-Platform'), token.split('Bearer ')[-1])
        if user_is:
            g.user = user_is
            return True
    print(f'login an try**** {token}')
    raise Unauthorized('Please login and try again')


@auth_bp.route("/login", methods=["POST"])
def login_user():
    """
    User Login
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              example: denz@abacies.com
            password:
              type: string
              example: Denz@2000
          required:
            - email
            - password
    responses:
      200:
        description: Successful login
        schema:
          type: object
          properties:
            data:
              type: object
            auth_token:
              type: string
              example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
            status:
              type: integer
              example: 200
      400:
        description: Invalid email or password
      500:
        description: Server error
    """
    verify_password(
        request.json.get("email", " ").lower().strip(),
        request.json.get("password", " ").strip()
        )
    token = g.user.generate_auth_token(request.headers.get('X-Platform'), Config_is.AUTH_TOKEN_EXPIRES)
    return jsonify({"data": g.user.login_to_dict(), "auth_token": token, "status": 200})


@auth_bp.route("/forgot_password", methods=["POST"])
def forgot_password_req():
    """
    Request Password Reset
    ---
    tags:
      - Authentication
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
              example: user@example.com
    responses:
      200:
        description: Password reset email sent
        schema:
          type: object
          properties:
            message:
              type: string
              example: Please check your inbox
            status:
              type: integer
              example: 200
    """
    token = AuthService().forgot_password(
        request.json.get("email", "").strip().lower()
    )
    password_reset_form = render_template(
        "reset_template.html",
        name=g.user.name,
        reset_url=f"{Config_is.FRONT_END_PASSWORD_RESET_URL}/{token.replace('.', '$$$$$')}",
    )
    sent = SendgridEmailSending(
        [{'user_id': str(g.user.id), 'email': g.user.email}], 
        f"Reset Password: {Config_is.APP_NAME} Application", 
        password_reset_form, 2
        ).send_email()
    if sent:
        return jsonify({"message": "Please check your inbox", "status": 200})
    raise InternalError()


@auth_bp.route("/reset_password", methods=["PATCH"])
def reset_password_req():
    """
    Reset user password using a valid reset token.

    ---
    tags:
      - Authentication
    summary: Reset Password
    description: Reset a user's password using a valid reset (forgot password) token. This requires a Bearer token in the header and a matching `new_password` and `confirm_password` in the body.
    security:
      - BearerAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: header
        name: Authorization
        required: true
        description: Bearer token for password reset (e.g., 'Bearer eyJhb...').
        type: string
      - in: body
        name: body
        description: Password reset input
        required: true
        schema:
          type: object
          required:
            - new_password
            - confirm_password
          properties:
            new_password:
              type: string
              description: The new password to set (min 5 characters).
              example: MyNewPass123
            confirm_password:
              type: string
              description: Confirm the new password (must match `new_password`).
              example: MyNewPass123
    responses:
      200:
        description: Password changed successfully.
        schema:
          type: object
          properties:
            message:
              type: string
              example: Password has been changed successfully
            status:
              type: integer
              example: 200
    """
    g.user = User.verify_auth_token(
        "forgot_pwd", 
        str(request.headers.get('Authorization', '')).split('Bearer ')[-1], 
        3600
        )
    if not g.user:
      raise BadRequest("This linked has expired")
    if len(request.json.get("new_password", "").strip()) < 5:
        raise BadRequest("Password length is short. Please try another password")
    if User.query.get(g.user["id"]).check_password(request.json.get("new_password")):
        raise BadRequest(
            "Please choose a new password that is different from your current one."
        )
    if request.json.get("new_password") != request.json.pop("confirm_password", None):
        raise BadRequest("Enter the password correctly.")
    if AuthService().new_password(g.user["id"], request.json["new_password"]):
        return jsonify(
            {"message": "Password has been changed successfully", "status": 200}
        )
    return InternalError()

@auth_bp.route('/logout', methods=['DELETE'])
@tokenAuth.login_required
def logout_session():
    """
    Logout user session
    ---
    tags:
      - Authentication
    summary: Logout user and remove authentication token
    description: |
      Removes the user's authentication token from Redis cache, effectively logging out the user.
      The token is identified by the platform key and authorization token provided in headers.
    parameters:
      - name: X-Platform
        in: header
        type: string
        required: true
        description: Platform identifier used as Redis key
        example: "Desktop"
      - name: Authorization
        in: header
        type: string
        required: true
        description: Bearer token for authentication
        example: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    responses:
      200:
        description: Successfully logged out
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Success"
            status:
              type: integer
              example: 200
        examples:
          application/json:
            message: "Success"
            status: 200
    """
    print(request.headers.get('Authorization').split('Bearer ')[1])
    remove_user_token(
        f"{g.user['id']}_{request.headers.get('X-Platform')}", 
        request.headers.get('Authorization').split('Bearer ')[1]
        )
    return jsonify({'message': 'Success', 'status': 200})
