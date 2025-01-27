import json
import redis.asyncio as aioredis
from typing import Optional
from src.models.email_event import EmailEvent

class RedisQueue:
    def __init__(self, host: str, port: int, queue_name: str = "email_queue"):
        self.redis_url = f'redis://{host}:{port}'
        self.queue_name = queue_name
        self.redis = None

    async def connect(self):  # Using connect() consistently
        """Initialize Redis connection"""
        if not self.redis:
            self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

    async def publish(self, event: EmailEvent) -> bool:
        """Add event to queue"""
        try:
            if not self.redis:
                await self.connect()
                
            event_data = {
                'event_id': event.event_id,
                'to_address': event.to_address,
                'tenant_id': event.tenant_id,
                'user_id': event.user_id,
                'subject': event.subject,
                'body': event.body,
                'provider': event.provider,
                'from_email': event.from_email,
                'access_token': event.access_token,
                'refresh_token': event.refresh_token,
                'attempt_count': getattr(event, 'attempt_count', 0)
            }
            await self.redis.rpush(self.queue_name, json.dumps(event_data))
            return True
        except Exception as e:
            print(f"Failed to publish event: {str(e)}")
            return False

    async def get(self) -> Optional[EmailEvent]:
        """Get next event from queue"""
        try:
            if not self.redis:
                await self.connect()  # Using connect()
                
            event_data = await self.redis.lpop(self.queue_name)
            if event_data:
                event_dict = json.loads(event_data)
                return EmailEvent(**event_dict)
            return None
        except Exception as e:
            print(f"Failed to get event from queue: {str(e)}")
            return None

    async def get_length(self) -> int:
        """Get current queue length"""
        try:
            if not self.redis:
                await self.connect()  # Using connect()
            return await self.redis.llen(self.queue_name)
        except Exception as e:
            print(f"Failed to get queue length: {str(e)}")
            return 0

    async def clear(self) -> bool:
        """Clear all items from queue"""
        try:
            if not self.redis:
                await self.connect()  # Using connect()
            await self.redis.delete(self.queue_name)
            return True
        except Exception as e:
            print(f"Failed to clear queue: {str(e)}")
            return False

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()