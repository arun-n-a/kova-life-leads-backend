import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    ENVIRONMENT = os.environ['ENVIRONMENT']
    APP_NAME = os.environ['APP_NAME']
    BASE_URL = os.environ['BASE_URL']
    FRONT_END_URL = os.environ['FRONT_END_URL']
    FRONT_END_PASSWORD_RESET_URL = os.environ['FRONT_END_PASSWORD_RESET_URL']
    FRONT_END_REGISTRATION_URL = os.environ['FRONT_END_REGISTRATION_URL']
    FRONT_END_REGISTRATION_SHORT_URL = os.environ['FRONT_END_REGISTRATION_SHORT_URL']
    DEBUG = os.environ.get('DEBUG', False)
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL'].replace('postgres://', 'postgresql://')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ['SECRET_KEY']
    AUTH_TOKEN_EXPIRES = int(os.environ['AUTH_TOKEN_EXPIRES'])
    SENDGRID_EMAIL_ADDRESS = os.environ['SENDGRID_EMAIL_ADDRESS']
    SENDGRID_API_KEY = os.environ['SENDGRID_API_KEY']
    AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
    AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
    AWS_BUCKET_REGION = os.environ['AWS_BUCKET_REGION']
    S3_BUCKET_NAME = os.environ['S3_BUCKET_NAME']
    REDIS_URL = os.environ['REDIS_URL']
    TWILIO_SID = os.environ['TWILIO_SID']
    TWILIO_TOKEN = os.environ['TWILIO_TOKEN']
    CRYPTO_KEY = os.environ['CRYPTO_KEY']
    SUPPRESSION_LIST_ALERT_TO = [_.strip() for _ in os.environ.get('SUPPRESSION_LIST_ALERT_TO', '').split(',')]
    TIME_ZONE = os.environ.get('TIME_ZONE')
    SQLALCHEMY_MIGRATE_REPO = f"{os.environ['ENVIRONMENT']}_migrations"
    STRIPE_SECRET_KEY = os.environ['STRIPE_SECRET_KEY']
    INVITATION_EMAIL_TO = [email_address.strip() for email_address in os.environ['INVITATION_EMAIL_TO'].split(',')]
    ALERT_EMAIL_TO = [email_address.strip() for email_address in os.environ['INVITATION_EMAIL_TO'].split(',')]
    STRIPE_WEBHOOK_SECRET = os.environ['STRIPE_WEBHOOK_SECRET']
    DEVELOPERS_EMAIL_ADDRESS = [email_address.strip() for email_address in os.environ['DEVELOPERS_EMAIL_ADDRESS'].split(',')]
    OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
    RENEWAL_DAY_OF_WEEK = int(os.environ['RENEWAL_DAY_OF_WEEK'])
    ALERT_EMAIL = [_.strip() for _ in os.environ.get('ALERT_EMAIL', '').split(',')]
    TWILIO_SMS_NUMBERS = [phone.strip() for phone in os.environ['TWILIO_SMS_NUMBERS'].split(',')]
    TWILIO_SMS_NUMBER_FOR_INVITATION = os.environ['TWILIO_SMS_NUMBER_FOR_INVITATION']

Config_is = Config()