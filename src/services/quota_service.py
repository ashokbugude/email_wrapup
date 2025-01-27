from datetime import datetime, timedelta
from src.db.database import Database
from src.config import Config

class QuotaService:
    def __init__(self, db: Database):
        self.db = db
        
    async def update_quota(self, email: str) -> None:
        """Update quota based on warmup duration"""
        try:
            async with self.db.get_connection() as cursor:
                # Get current quota info
                await cursor.execute("""
                    SELECT daily_quota, warmup_start_date
                    FROM email_quotas
                    WHERE email = %s
                """, (email,))
                
                result = await cursor.fetchone()
                if not result:
                    return
                    
                current_quota, warmup_start_date = result
                days_since_start = (datetime.now().date() - warmup_start_date).days
                
                # Calculate new quota based on warmup duration
                new_quota = current_quota
                for days, quota in sorted(Config.QUOTA_INCREASE_RATE.items()):
                    if days_since_start >= days and quota > new_quota:
                        new_quota = min(quota, Config.MAX_QUOTA)
                
                # Update if quota changed
                if new_quota != current_quota:
                    await cursor.execute("""
                        UPDATE email_quotas
                        SET daily_quota = %s
                        WHERE email = %s
                    """, (new_quota, email))
                    
        except Exception as e:
            print(f"Failed to update quota: {str(e)}") 