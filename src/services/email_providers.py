from abc import ABC, abstractmethod
from typing import Dict
import aiohttp
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import smtplib
import ssl
import json
import os

class EmailProvider(ABC):
    @abstractmethod
    async def send_email(self, from_email: str, to_email: str, subject: str, body: str, access_token: str, refresh_token: str = None) -> Dict:
        pass

class GmailProvider(EmailProvider):
    def __init__(self):
        self.client_id = os.getenv('GMAIL_CLIENT_ID')
        self.client_secret = os.getenv('GMAIL_CLIENT_SECRET')
        self.token_uri = "https://oauth2.googleapis.com/token"

    async def send_email(self, from_email: str, to_email: str, subject: str, body: str, access_token: str, refresh_token: str = None) -> Dict:
        try:
            # Create credentials object with all required fields
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri=self.token_uri,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=['https://www.googleapis.com/auth/gmail.send']
            )

            # Refresh token if expired
            if credentials.expired:
                credentials.refresh(Request())

            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Create message
            message = MIMEText(body)
            message['to'] = to_email
            message['from'] = from_email
            message['subject'] = subject
            
            # Encode the message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send message
            service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return {
                'success': True,
                'new_access_token': credentials.token if credentials.expired else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

class OutlookProvider(EmailProvider):
    async def send_email(self, from_email: str, to_email: str, subject: str, body: str, access_token: str) -> Dict:
        try:
            endpoint = 'https://graph.microsoft.com/v1.0/me/sendMail'
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            email_data = {
                'message': {
                    'subject': subject,
                    'body': {'contentType': 'Text', 'content': body},
                    'toRecipients': [{'emailAddress': {'address': to_email}}]
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=headers, json=email_data) as response:
                    if response.status == 202:
                        return {'success': True}
                    error_data = await response.text()
                    return {'success': False, 'error': error_data}
                    
        except Exception as e:
            return {'success': False, 'error': str(e)} 