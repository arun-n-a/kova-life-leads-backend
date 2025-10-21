from uuid import uuid4
from typing import List, Dict

import requests

from app.models import SendgridLog
from app.services.crud import CRUD
from app.services.custom_errors import *
from app import db
from config import Config_is
from flask import g


class SendgridEmailSending:
    def __init__(self, to_emails: List, 
                 subject: str, html_content: str, 
                 event: int = None):
        self.to_emails = to_emails
        self.subject = subject
        self.html_content = html_content
        self.event =  event
        self.headers = {
            "Authorization": f"Bearer {Config_is.SENDGRID_API_KEY}",
            "Content-Type": "application/json"
            }
    
    def send_email_handle_log(self, data: Dict, bulk_insert_log: List):
        try:
            response = requests.post(
                "https://api.sendgrid.com/v3/mail/send", 
                headers=self.headers, json=data
                )
            print(f"sendgrid {response.status_code}")
            if response.status_code in [200, 202]:
                db.session.bulk_save_objects(bulk_insert_log)
                CRUD.db_commit()
                return True
        except Exception as e:
            print(f" handle error {e}")
            for log_obj in bulk_insert_log:
                log_obj.error =  f"Exception {e}"
                db.session.add(log_obj)
            CRUD.db_commit()
            return False
        print('no exception but not 200')
        for log_obj in bulk_insert_log:
            log_obj.error =  f"Exception {e}"
            db.session.add(log_obj)
        CRUD.db_commit()
        return False
    
    def send_email(self) -> bool:
        to_emails_structure, bulk_insert_log = [], []
        for user_data in self.to_emails:
            unique_id = uuid4()
            to_emails_structure.append(
                {
                    "to": [{"email": user_data.pop('email')}],
                    "custom_args": {"unique_id": str(unique_id)}
                })
            bulk_insert_log.append(SendgridLog(id=unique_id, event=self.event, user_id=user_data['user_id']))
        data = {
            "personalizations": to_emails_structure,
            "from": {"email": Config_is.SENDGRID_EMAIL_ADDRESS},
            "subject": self.subject,
            "content": [
                {
                    "type": "text/html",
                    "value": self.html_content
                }
                ]
            }
        return self.send_email_handle_log(data, bulk_insert_log)
        
    def send_email_without_logs(self) -> bool:
        print('send_email_without_logs')
        try:
            data = {
                "personalizations": [
                     {
                         "to": [{"email": email_address} for  email_address in self.to_emails]
                    }
                    ],
            "from": {"email": Config_is.SENDGRID_EMAIL_ADDRESS},
            "subject": self.subject,
            "content": [
                {
                    "type": "text/html",
                    "value": self.html_content
                }
                ]
            }
            response = requests.post(
                "https://api.sendgrid.com/v3/mail/send", 
                headers=self.headers, json=data
                )
            if response.status_code in [200, 202]:
                print(response.status_code)
                return True
            print(response.status_code)
        except Exception as e:
            print(f'Exception sendgrid {e}')
        return False

    def send_email_with_attachments(self, attachments: List[Dict]) -> bool:
            data = {
                "personalizations": [
                    {
                    "to": [{"email": email_address} for email_address in self.to_emails]
                    }
                ],
                "from": {"email": Config_is.SENDGRID_EMAIL_ADDRESS},
                "subject": self.subject,
                "content": [
                    {
                        "type": "text/html",
                        "value": self.html_content
                    }
                ],
                "attachments": [
                    {
                        "content": attachment['encoded_file'],
                        "filename": attachment['name'],
                        "type": attachment['type'],
                        "disposition": "attachment"
                    } for attachment in attachments
                ]
            }
            try:
                response = requests.post(
                    "https://api.sendgrid.com/v3/mail/send", 
                    headers=self.headers, json=data
            )
                if response.status_code in [200, 202]:
                    return True
                print(response.status_code)
            except Exception as e:
                print(f'Exception sendgrid {e}')
            return False
