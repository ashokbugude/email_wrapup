import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailWorker:
    def __init__(self, queue, email_service, max_retries=3, retry_delay=300):  # 5 minutes retry delay
        self.queue = queue
        self.email_service = email_service
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.is_running = False

    async def start(self):
        """Start the worker"""
        self.is_running = True
        logger.info("Email worker started")
        
        while self.is_running:
            try:
                # Get event from queue
                event = await self.queue.get()
                if event:
                    await self.process_event(event)
            except Exception as e:
                logger.error(f"Error processing queue: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def process_event(self, event):
        """Process a single email event"""
        try:
            logger.info(f"Processing email event: {event.event_id}")
            
            # Check if event should be retried
            if hasattr(event, 'attempt_count') and event.attempt_count >= self.max_retries:
                logger.error(f"Max retries exceeded for event {event.event_id}")
                await self._update_event_status(event, 'failed', 'Max retries exceeded')
                return

            # Process the email
            success = await self.email_service.process_email(event)
            
            if not success:
                # Increment attempt count and requeue if needed
                event.attempt_count = getattr(event, 'attempt_count', 0) + 1
                if event.attempt_count < self.max_retries:
                    await self._requeue_event(event)
                else:
                    await self._update_event_status(event, 'failed', 'Max retries exceeded')
            
        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {str(e)}")
            await self._update_event_status(event, 'failed', str(e))

    async def _requeue_event(self, event):
        """Requeue event with exponential backoff"""
        delay = self.retry_delay * (2 ** (event.attempt_count - 1))  # Exponential backoff
        logger.info(f"Requeueing event {event.event_id} with delay {delay}s")
        await asyncio.sleep(delay)
        await self.queue.publish(event)

    async def _update_event_status(self, event, status: str, error_message: Optional[str] = None):
        """Update event status in database"""
        try:
            async with self.email_service.db.get_connection() as cursor:
                await cursor.execute("""
                    UPDATE email_logs
                    SET status = %s,
                        error_message = %s,
                        updated_at = %s,
                        attempt_count = %s
                    WHERE event_id = %s
                """, (
                    status,
                    error_message,
                    datetime.utcnow(),
                    getattr(event, 'attempt_count', 1),
                    event.event_id
                ))
        except Exception as e:
            logger.error(f"Failed to update event status: {str(e)}")

    async def stop(self):
        """Stop the worker"""
        self.is_running = False
        logger.info("Email worker stopped") 