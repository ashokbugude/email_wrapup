from typing import Dict
import aiohttp
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from src.config import Config
import base64

class OAuthHandler:
    @staticmethod
    async def handle_gmail_oauth(code: str, redirect_uri: str) -> Dict:
        """Handle Gmail OAuth code exchange and token retrieval"""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": Config.GMAIL_CLIENT_ID,
                        "client_secret": Config.GMAIL_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                scopes=['https://www.googleapis.com/auth/gmail.send']
            )
            flow.redirect_uri = redirect_uri
            
            # Exchange code for tokens (synchronous due to library limitations)
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Get user email
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f'Bearer {credentials.token}'}
                ) as response:
                    user_info = await response.json()
            
            return {
                'email': user_info['email'],
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token
            }
            
        except Exception as e:
            raise Exception(f"Gmail OAuth failed: {str(e)}")
    
    @staticmethod
    async def handle_outlook_oauth(code: str, redirect_uri: str) -> Dict:
        """Handle Outlook OAuth code exchange and token retrieval"""
        try:
            async with aiohttp.ClientSession() as session:
                # Exchange code for tokens
                async with session.post(
                    'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                    data={
                        'client_id': Config.OUTLOOK_CLIENT_ID,
                        'client_secret': Config.OUTLOOK_CLIENT_SECRET,
                        'code': code,
                        'redirect_uri': redirect_uri,
                        'grant_type': 'authorization_code'
                    }
                ) as response:
                    token_response = await response.json()
                
                # Get user email
                async with session.get(
                    'https://graph.microsoft.com/v1.0/me',
                    headers={'Authorization': f'Bearer {token_response["access_token"]}'}
                ) as response:
                    user_info = await response.json()
            
            return {
                'email': user_info['userPrincipalName'],
                'access_token': token_response['access_token'],
                'refresh_token': token_response['refresh_token']
            }
            
        except Exception as e:
            raise Exception(f"Outlook OAuth failed: {str(e)}")
    
    @staticmethod
    async def refresh_gmail_token(refresh_token: str) -> Dict:
        """No refresh needed for basic auth"""
        return {
            'access_token': refresh_token,
            'refresh_token': refresh_token
        }
    
    @staticmethod
    async def refresh_outlook_token(refresh_token: str) -> Dict:
        """Refresh Outlook access token"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                    data={
                        'client_id': Config.OUTLOOK_CLIENT_ID,
                        'client_secret': Config.OUTLOOK_CLIENT_SECRET,
                        'refresh_token': refresh_token,
                        'grant_type': 'refresh_token'
                    }
                ) as response:
                    result = await response.json()
            
            return {
                'access_token': result['access_token'],
                'refresh_token': result.get('refresh_token', refresh_token)
            }
            
        except Exception as e:
            raise Exception(f"Outlook token refresh failed: {str(e)}") 