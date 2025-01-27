from typing import Dict, Optional
from datetime import datetime, timedelta
from src.db.database import Database
from src.models.email_event import EmailEvent
from src.services.email_providers import GmailProvider, OutlookProvider
from src.services.oauth_handler import OAuthHandler
from src.services.quota_service import QuotaService
from src.validation.email_validator import EmailValidator
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self, db: Database, validator: EmailValidator):
        self.db = db
        self.validator = validator
        self.quota_service = QuotaService(db)
        self.providers = {
            'gmail': GmailProvider(),
            'outlook': OutlookProvider()
        }
        
    async def process_email(self, event: EmailEvent) -> bool:
        try:
            # Get sender details
            sender_info = await self._get_sender_info(event.user_id, event.tenant_id)
            if not sender_info:
                await self._log_event(event, 'failed', 'Sender credentials not found')
                return False
            
            # Update quota based on warmup progress
            await self.quota_service.update_quota(sender_info['email'])
            
            # Validate recipient
            if not await self.validator.is_valid_email(event.to_address):
                await self._log_event(event, 'failed', 'Invalid recipient email')
                return False
                
            # Check quota
            if not await self._check_quota(sender_info['email']):
                await self._log_event(event, 'delayed', 'Daily quota exceeded')
                return False
                
            # Send email
            provider = self.providers.get(sender_info['provider'])
            if not provider:
                await self._log_event(event, 'failed', 'Invalid provider')
                return False
                
            result = await provider.send_email(
                sender_info['email'],
                event.to_address,
                event.subject,
                event.body,
                sender_info['access_token'],
                sender_info['refresh_token']
            )
            
            if result['success']:
                if result.get('new_access_token'):
                    await self._update_access_token(
                        sender_info['email'], 
                        result['new_access_token']
                    )
                await self._update_quota(sender_info['email'])
                await self._log_event(event, 'sent')
                return True
            else:
                await self._log_event(event, 'failed', result['error'])
                return False
                
        except Exception as e:
            await self._log_event(event, 'failed', str(e))
            return False
            
    def _refresh_token(self, sender_info: Dict) -> None:
        try:
            refresh_result = (
                OAuthHandler.refresh_gmail_token(sender_info['refresh_token'])
                if sender_info['provider'] == 'gmail'
                else OAuthHandler.refresh_outlook_token(sender_info['refresh_token'])
            )
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE credentials
                    SET access_token = %s, refresh_token = %s
                    WHERE email = %s
                """, (
                    refresh_result['access_token'],
                    refresh_result['refresh_token'],
                    sender_info['email']
                ))
                conn.commit()
                
        except Exception as e:
            raise Exception(f"Token refresh failed: {str(e)}")

    async def _log_event(self, event: EmailEvent, status: str, error_message: Optional[str] = None):
        """Log email event status to database"""
        try:
            if not hasattr(event, 'from_email'):
                raise AttributeError("Email event missing required 'from_email' field")
            
            async with self.db.get_connection() as cursor:
                await cursor.execute("""
                    INSERT INTO email_logs (
                        event_id,
                        from_email,
                        to_email,
                        subject,
                        status,
                        error_message,
                        created_at,
                        updated_at,
                        attempt_count
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        status = VALUES(status),
                        error_message = VALUES(error_message),
                        updated_at = VALUES(updated_at),
                        attempt_count = VALUES(attempt_count)
                """, (
                    event.event_id,
                    event.from_email,
                    event.to_address,
                    event.subject,
                    status,
                    error_message,
                    event.created_at,
                    datetime.utcnow(),
                    getattr(event, 'attempt_count', 1)
                ))
        except AttributeError as e:
            logging.error(f"Failed to log email event: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Database error: {str(e)}")
            raise

    async def _get_sender_info(self, user_id: str, tenant_id: str) -> Optional[Dict]:
        """Get sender credentials from database"""
        try:
            async with self.db.get_connection() as cursor:
                await cursor.execute("""
                    SELECT email, provider, access_token, refresh_token
                    FROM credentials 
                    WHERE user_id = %s 
                    AND tenant_id = %s
                    LIMIT 1
                """, (user_id, tenant_id))
                
                result = await cursor.fetchone()
                if not result:
                    return None
                    
                return {
                    'email': result[0],
                    'provider': result[1],
                    'access_token': result[2],
                    'refresh_token': result[3]
                }
                
        except Exception as e:
            logging.error(f"Failed to get sender info: {str(e)}")
            return None 

    async def _check_quota(self, email: str) -> bool:
        """Check if sender has remaining quota for today"""
        try:
            async with self.db.get_connection() as cursor:
                await cursor.execute("""
                    SELECT daily_quota, used_quota, last_reset_date
                    FROM email_quotas
                    WHERE email = %s
                """, (email,))
                
                result = await cursor.fetchone()
                if not result:
                    return False
                    
                daily_quota, used_quota, last_reset_date = result
                
                # Reset quota if it's a new day
                today = datetime.now().date()
                if last_reset_date < today:
                    await cursor.execute("""
                        UPDATE email_quotas
                        SET used_quota = 0,
                            last_reset_date = CURRENT_DATE
                        WHERE email = %s
                    """, (email,))
                    used_quota = 0
                
                return used_quota < daily_quota
                
        except Exception as e:
            logging.error(f"Failed to check quota: {str(e)}")
            return False

    async def _update_quota(self, email: str) -> None:
        """Increment used quota count"""
        try:
            async with self.db.get_connection() as cursor:
                await cursor.execute("""
                    UPDATE email_quotas
                    SET used_quota = used_quota + 1
                    WHERE email = %s
                """, (email,))
                
        except Exception as e:
            logging.error(f"Failed to update quota usage: {str(e)}") 

    async def _update_access_token(self, email: str, new_token: str) -> None:
        """Update access token in database"""
        try:
            async with self.db.get_connection() as cursor:
                await cursor.execute("""
                    UPDATE credentials
                    SET access_token = %s
                    WHERE email = %s
                """, (new_token, email))
        except Exception as e:
            logging.error(f"Failed to update access token: {str(e)}") 

    def process_email_event(self, event_data):
        try:
            # Log the full event data for debugging
            logger.info(f"Processing email event with data: {event_data}")
            
            # Validate required fields
            required_fields = ['event_id', 'from_email', 'to_address', 'subject', 'body']
            missing_fields = [field for field in required_fields if field not in event_data]
            
            if missing_fields:
                error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Create event with explicit field extraction
            from_email = event_data.get('from_email')
            if not from_email:
                logger.error("from_email is empty or None")
                raise ValueError("from_email cannot be empty")
            
            email_event = EmailEvent(
                event_id=event_data['event_id'],
                from_email=from_email,
                to_address=event_data['to_address'],
                subject=event_data['subject'],
                body=event_data['body']
            )
            
            logger.info(f"Successfully created EmailEvent {email_event.event_id}")
            return email_event
            
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to create EmailEvent: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in process_email_event: {str(e)}", exc_info=True)
            raise

    def log_email_event(self, email_event):
        try:
            # Validate email_event before processing
            if not isinstance(email_event, EmailEvent):
                raise TypeError(f"Expected EmailEvent, got {type(email_event)}")
            
            if not hasattr(email_event, 'from_email') or not email_event.from_email:
                logger.error(f"Invalid EmailEvent {email_event.event_id}: missing from_email")
                raise ValueError("Email event missing required 'from_email' field")
            
            logger.info(f"Logging email event {email_event.event_id} with from_email: {email_event.from_email}")
            
            # Process the event...
            # Add your database logging logic here
            
            logger.info(f"Successfully logged email event {email_event.event_id}")
            
        except Exception as e:
            logger.error(f"Failed to log email event: {str(e)}", exc_info=True)
            raise 