from typing import Dict
import base64
import smtplib
import ssl
from email.mime.text import MIMEText

class GmailAuthService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.port = 587
    
    def generate_email(self, user_id: str, tenant_id: str) -> str:
        """Generate email from user_id and tenant_id"""
        return f"{user_id}@{tenant_id}.com"
    
    async def authenticate(self, user_id: str, tenant_id: str, password: str) -> dict:
        """Authenticate Gmail using password"""
        try:
            email = self.generate_email(user_id, tenant_id)
            
            # Validate SMTP connection
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.port) as server:
                server.starttls(context=context)
                server.login(email, password)
            
            # Create a simple token from credentials
            token = base64.b64encode(
                f"{email}:{password}".encode()
            ).decode()
            
            return {
                'email': email,
                'access_token': token,
                'refresh_token': token,
                'provider': 'gmail'
            }
            
        except Exception as e:
            raise Exception(f"Gmail authentication failed: {str(e)}") 