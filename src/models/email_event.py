from datetime import datetime
from typing import Optional
from uuid import uuid4

class EmailEvent:
    def __init__(
        self,
        user_id: str,
        tenant_id: str,
        to_address: str,
        subject: str,
        body: str,
        provider: str,
        from_email: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        event_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        attempt_count: int = 1
    ):
        self.event_id = event_id or str(uuid4())
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.from_email = from_email
        self.to_address = to_address
        self.subject = subject
        self.body = body
        self.provider = provider
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.created_at = created_at or datetime.utcnow()
        self.attempt_count = attempt_count