# import ssl
import logging
from logging.handlers import RotatingFileHandler

from redis import StrictRedis
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from flask_compress import Compress
from flask_limiter import Limiter
from flasgger import Swagger
from flask_limiter.util import get_remote_address

# from sqlalchemy_continuum import make_versioned
from sqlalchemy.orm import configure_mappers

from config import Config_is
from app.services.custom_errors import *


# make_versioned()
db = SQLAlchemy()
migrate = Migrate()
try:
    redis_obj = StrictRedis.from_url(
        Config_is.REDIS_URL, decode_responses=True,
        ssl_cert_reqs=None, ssl_check_hostname=False
    )
except Exception as e:
    print(f"redis connection exception {e}")
    redis_obj = None

app = None
limiter = None

# from app import models

def create_app(config_class=Config_is):
    global app
    global limiter
    if app:
        return app
    app = Flask(__name__, template_folder='templates')
    
    swagger_template = {
        "swagger": "2.0",
    "info": {
        "title": "KovaLifeLeads Leads API",
        "description": "Enter token using the Authorize button above.",
        "version": "1.0"
    },
    "host": Config_is.BASE_URL.replace('https://', '') if 'localhost' not in Config_is.BASE_URL else "127.0.0.1:5000",
    "schemes": ["http", "https"],
    "securityDefinitions": {
        "BearerAuth": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Enter your JWT token with `Bearer` prefix. Example: `Bearer eyJhbGciOi...`"
        }
    },
    "definitions": {
        # Define schemas for your error responses
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "A descriptive error message."},
                "status": {"type": "integer", "format": "int32", "description": "The HTTP status code."}
            },
            "required": ["message", "status"]
        },
        "UnauthorizedErrorSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "example": Unauthorized().message},
                "status": {"type": "integer", "example": Unauthorized().status}
            }
        },
        "ForbiddenErrorSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "example": Forbidden().message},
                "status": {"type": "integer", "example": Forbidden().status}
            }
        },
        "BadRequestErrorSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "example": BadRequest().message},
                "status": {"type": "integer", "example": BadRequest().status}
            }
        },
        "InternalErrorSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "example": InternalError().message},
                "status": {"type": "integer", "example": InternalError().status}
            }
        },
        "UnProcessableErrorSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "example": UnProcessable().message},
                "status": {"type": "integer", "example": UnProcessable().status}
            }
        },
        "ConflictErrorSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "example": Conflict().message},
                "status": {"type": "integer", "example": Conflict().status}
            }
        }
    },
    "responses": {
        # Define reusable HTTP responses using the schemas defined above
        "UnauthorizedResponse": {
            "description": Unauthorized().message,
            "schema": {"$ref": "#/definitions/UnauthorizedErrorSchema"}
        },
        "ForbiddenResponse": {
            "description": Forbidden().message,
            "schema": {"$ref": "#/definitions/ForbiddenErrorSchema"}
        },
        "BadRequestResponse": {
            "description": BadRequest().message,
            "schema": {"$ref": "#/definitions/BadRequestErrorSchema"}
        },
        "InternalErrorResponse": {
            "description": InternalError().message,
            "schema": {"$ref": "#/definitions/InternalErrorSchema"}
        },
        "UnProcessableResponse": {
            "description": UnProcessable().message,
            "schema": {"$ref": "#/definitions/UnProcessableErrorSchema"}
        },
        "ConflictResponse": {
            "description": Conflict().message,
            "schema": {"$ref": "#/definitions/ConflictErrorSchema"}
        }
        # Note: 204 (No Content) doesn't typically have a body, so it doesn't need a schema
        # but you can define it as a response if you want specific description.
        # "NoContentResponse": {
        #     "description": NoContent().message
        # }
        }}
    Swagger(app, template=swagger_template)
    compress = Compress()
    cors = CORS()
    compress.init_app(app)
    cors.init_app(app)
    app.config.from_object(config_class)
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 30
    app.config['SQLALCHEMY_POOL_PRE_PING'] = True
    db.init_app(app)
    migrate.init_app(app, db)
    # limiter = Limiter(
    #     get_remote_address,
    #     app=app,
    #     default_limits=["10 per day", "10 per hour"],
    #     storage_uri=Config_is.REDIS_URL
    #     )
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = RotatingFileHandler(
        'log_data.log', maxBytes=10000, backupCount=5)
    file_handler.setFormatter(formatter)
    logging.basicConfig(handlers=[file_handler], level=logging.DEBUG)
    app.logger.addHandler(file_handler)

    @app.teardown_request
    def teardown_request(exception=None):
        if db is not None:
            db.session.remove()

    from app.api.auth import auth_bp
    from app.api.user import user_bp
    from app.api.agents import agents_bp
    from app.api.file_operations import files_bp
    from app.api.leads_operations import leads_bp
    from app.api.twilio_call_sms import twilio_bp
    from app.api.stripe_routes import stripe_bp
    from app.api.pricing_details import pricing_bp
    from app.api.orders import order_bp
    from app.api import bp as api_bp
    from app.api.shopping_cart import cart_bp
    from app.services.custom_errors import (
        CustomError, handle_invalid_usage)
    from app.api.coupon import coupon_bp
    from app.api.promotion import promotion_bp
    from app.api.stripe_subscriptions import stripe_subscriptions_bp
    from app.api.uploader_fields import uploader_template_bp
    from app.api.marketplace import marketplace_bp
    from app.api.revenue_view import revenue_bp
    from app.api.invoice import invoice_bp

    from app.api.smijith import smijith_bp  # TODO: have to delete
    from app.api.territory import territory_bp
    from app.api.dashboard import dashboard_bp
    from app.api.lead_management import lead_management_bp
    from app.api.report import report_bp
    from app.api.elevenlabs_twilio import elevenlabs_bp


    with app.app_context():
        configure_mappers()  #
    
    app.register_blueprint(api_bp, url_prefix='/')
    app.register_error_handler(CustomError, handle_invalid_usage)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(agents_bp, url_prefix='/agents')
    app.register_blueprint(files_bp, url_prefix='/files')
    app.register_blueprint(leads_bp, url_prefix='/leads')
    app.register_blueprint(twilio_bp, url_prefix='/twilio')
    app.register_blueprint(stripe_bp, url_prefix='/stripe')
    app.register_blueprint(pricing_bp, url_prefix='/pricing')
    app.register_blueprint(order_bp, url_prefix='/orders')
    app.register_blueprint(cart_bp, url_prefix='/shopping_cart')
    app.register_blueprint(coupon_bp, url_prefix='/coupon_code')
    app.register_blueprint(promotion_bp, url_prefix='/promotion_code')
    app.register_blueprint(stripe_subscriptions_bp, url_prefix='/stripe-subscriptions')
    app.register_blueprint(uploader_template_bp, url_prefix='/mortgage-file-templates')
    app.register_blueprint(marketplace_bp, url_prefix='/marketplace')
    app.register_blueprint(revenue_bp, url_prefix='/revenue')
    app.register_blueprint(smijith_bp, url_prefix='/canva')  # TODO: have to delete
    app.register_blueprint(invoice_bp, url_prefix='/invoice')
    app.register_blueprint(territory_bp, url_prefix='/territory')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(lead_management_bp, url_prefix='/lead-management')
    app.register_blueprint(report_bp, url_prefix='/report')
    app.register_blueprint(elevenlabs_bp, url_prefix='/elevenlabs')
    return app

