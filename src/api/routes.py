from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from src.models.email_event import EmailEvent
from src.services.email_service import EmailService
from src.services.oauth_handler import OAuthHandler
from src.queue.redis_queue import RedisQueue
from src.validation.email_validator import EmailValidator
from src.db.database import Database
from src.config import Config
import os
import jwt
from datetime import datetime, timedelta
import base64
import json
from src.services.gmail_auth import GmailAuthService
import aiohttp
from google_auth_oauthlib.flow import Flow

app = FastAPI(title="Email Warmup Service")

# Serve static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Add new environment variables
GMAIL_USER_ID = os.getenv('GMAIL_USER_ID')
GMAIL_TENANT_ID = os.getenv('GMAIL_TENANT_ID')

class EmailRequest(BaseModel):
    provider: str
    to_address: str
    subject: str
    body: str

class AuthRequest(BaseModel):
    user_id: str
    tenant_id: str
    password: str

class GmailAuthRequest(BaseModel):
    user_id: str
    tenant_id: str
    password: str

class LinkAccountRequest(BaseModel):
    provider: str

security = HTTPBearer()
SECRET_KEY = os.getenv('SECRET_KEY')

@app.get("/")
async def index():
    return FileResponse("src/static/index.html")

@app.post("/api/send-email")
async def send_email(email_req: EmailRequest, request: Request):
    try:
        # Get credentials for the selected provider
        async with request.app.state.db.get_connection() as cursor:
            await cursor.execute("""
                SELECT email, access_token, refresh_token 
                FROM credentials 
                WHERE provider = %s 
                AND user_id = %s 
                AND tenant_id = %s
            """, (
                email_req.provider,
                os.getenv('GMAIL_USER_ID'),
                os.getenv('GMAIL_TENANT_ID')
            ))
            
            creds = await cursor.fetchone()
            if not creds:
                raise HTTPException(
                    status_code=400, 
                    detail=f"No linked {email_req.provider} account found"
                )

            # Create email event with provider and tokens
            event = EmailEvent(
                user_id=os.getenv('GMAIL_USER_ID'),
                tenant_id=os.getenv('GMAIL_TENANT_ID'),
                to_address=email_req.to_address,
                subject=email_req.subject,
                body=email_req.body,
                provider=email_req.provider,
                from_email=creds[0],
                access_token=creds[1],  # Added access_token
                refresh_token=creds[2]   # Added refresh_token
            )

            if await request.app.state.queue.publish(event):
                return {
                    'message': 'Email queued successfully',
                    'event_id': event.event_id
                }
            raise HTTPException(status_code=500, detail="Failed to queue email")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/validate")
async def validate_credentials(auth_req: AuthRequest):
    # In production, validate against your user database
    # For demo, we'll accept any credentials
    token = jwt.encode({
        'user_id': auth_req.user_id,
        'tenant_id': auth_req.tenant_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, SECRET_KEY, algorithm='HS256')
    
    return {'token': token}

@app.get("/api/oauth/callback/{provider}")
async def oauth_callback(
    provider: str, 
    code: Optional[str] = None, 
    state: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing parameters")
    
    try:
        # Validate JWT token
        token_data = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=['HS256'])
        
        # Decode state parameter
        state_data = json.loads(base64.b64decode(state))
        if (state_data['user_id'] != token_data['user_id'] or 
            state_data['tenant_id'] != token_data['tenant_id']):
            raise HTTPException(status_code=401, detail="Invalid state parameter")
        
        # Rest of the OAuth callback logic remains the same
        # Reference to original code:
        if provider == 'gmail':
            credentials = OAuthHandler.handle_gmail_oauth(code, redirect_uri)
        elif provider == 'outlook':
            credentials = OAuthHandler.handle_outlook_oauth(code, redirect_uri)
        else:
            raise HTTPException(status_code=400, detail="Invalid provider")
            
        # Store credentials and initialize quota
        with request.app.state.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Store credentials
            cursor.execute("""
                INSERT INTO credentials 
                (user_id, tenant_id, email, provider, access_token, refresh_token)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    access_token = VALUES(access_token),
                    refresh_token = VALUES(refresh_token)
            """, (
                'user1',  # Hardcoded for demo
                'tenant1',  # Hardcoded for demo
                credentials['email'],
                provider,
                credentials['access_token'],
                credentials['refresh_token']
            ))
            
            # Initialize quota
            cursor.execute("""
                INSERT INTO email_quotas 
                (email, daily_quota, warmup_start_date, last_reset_date)
                VALUES (%s, %s, CURRENT_DATE, CURRENT_DATE)
                ON DUPLICATE KEY UPDATE
                    warmup_start_date = CURRENT_DATE,
                    last_reset_date = CURRENT_DATE
            """, (credentials['email'], Config.INITIAL_QUOTA))
            
            conn.commit()
            
        return {'message': 'Account linked successfully'}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/gmail")
async def gmail_auth(auth_req: GmailAuthRequest, request: Request):
    try:
        gmail_service = GmailAuthService()
        auth_result = await gmail_service.authenticate(
            auth_req.user_id,
            auth_req.tenant_id,
            auth_req.password
        )
        
        async with request.app.state.db.get_connection() as cursor:
            # Store credentials
            await cursor.execute("""
                INSERT INTO credentials 
                (user_id, tenant_id, email, provider, access_token, refresh_token)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    access_token = VALUES(access_token),
                    refresh_token = VALUES(refresh_token)
            """, (
                auth_req.user_id,
                auth_req.tenant_id,
                auth_result['email'],
                auth_result['provider'],
                auth_result['access_token'],
                auth_result['refresh_token']
            ))
            
            # Initialize quota
            await cursor.execute("""
                INSERT INTO email_quotas 
                (email, daily_quota, warmup_start_date, last_reset_date)
                VALUES (%s, %s, CURRENT_DATE, CURRENT_DATE)
                ON DUPLICATE KEY UPDATE
                    warmup_start_date = CURRENT_DATE,
                    last_reset_date = CURRENT_DATE
            """, (auth_result['email'], Config.INITIAL_QUOTA))
            
        return {"message": "Gmail account linked successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/link-account")
async def link_account(request: LinkAccountRequest, request_obj: Request):
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": os.getenv("GMAIL_CLIENT_ID"),
                    "client_secret": os.getenv("GMAIL_CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=['openid', 'https://www.googleapis.com/auth/gmail.send']
        )
        
        flow.redirect_uri = "http://127.0.0.1:5000/oauth2callback"
        
        # Use environment variables for state
        state = base64.b64encode(json.dumps({
            "user_id": GMAIL_USER_ID,
            "tenant_id": GMAIL_TENANT_ID
        }).encode()).decode()
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )
        
        return {"auth_url": auth_url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/oauth2callback")
async def gmail_oauth_callback(code: str, state: str, request: Request):
    try:
        # Decode state
        state_data = json.loads(base64.b64decode(state))
        
        # Create flow instance
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": os.getenv("GMAIL_CLIENT_ID"),
                    "client_secret": os.getenv("GMAIL_CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://127.0.0.1:5000/oauth2callback"]
                }
            },
            scopes=[
                'openid',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/userinfo.email'
            ]
        )
        
        flow.redirect_uri = "http://127.0.0.1:5000/oauth2callback"
        
        # Exchange code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get user email using the credentials
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {credentials.token}'}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Failed to get user info: {error_text}"
                    )
                user_info = await response.json()

        # Store in database
        async with request.app.state.db.get_connection() as cursor:
            await cursor.execute("""
                INSERT INTO credentials 
                (user_id, tenant_id, email, provider, access_token, refresh_token)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    access_token = VALUES(access_token),
                    refresh_token = VALUES(refresh_token)
            """, (
                state_data['user_id'],
                state_data['tenant_id'],
                user_info['email'],  # Use actual email from Google
                'gmail',
                credentials.token,
                credentials.refresh_token
            ))
            
            # Initialize quota
            await cursor.execute("""
                INSERT INTO email_quotas 
                (email, daily_quota, warmup_start_date, last_reset_date)
                VALUES (%s, %s, CURRENT_DATE, CURRENT_DATE)
                ON DUPLICATE KEY UPDATE
                    warmup_start_date = CURRENT_DATE,
                    last_reset_date = CURRENT_DATE
            """, (user_info['email'], Config.INITIAL_QUOTA))
        
        return FileResponse("src/static/success.html")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))