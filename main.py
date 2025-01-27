import os
from dotenv import load_dotenv
import threading
from fastapi import FastAPI
from src.api.routes import app
from src.db.database import Database
from src.queue.redis_queue import RedisQueue
from src.services.email_service import EmailService
from src.validation.email_validator import EmailValidator
import asyncio
from src.config import Config
import logging
from src.workers.email_worker import EmailWorker

# Load environment variables
load_dotenv()

async def init_database():
    """Initialize database tables if they don't exist"""
    db = Database()
    async with db.get_connection() as cursor:
        # Disable table exists warnings
        await cursor.execute("SET sql_notes = 0;")
        
        with open('src/db/schema.sql', 'r') as f:
            schema = f.read()
            # Replace CREATE TABLE with CREATE TABLE IF NOT EXISTS
            schema = schema.replace(
                'CREATE TABLE', 
                'CREATE TABLE IF NOT EXISTS'
            )
            statements = schema.split(';')
            for statement in statements:
                if statement.strip():
                    await cursor.execute(statement)
            await cursor.connection.commit()
        
        # Re-enable warnings
        await cursor.execute("SET sql_notes = 1;")

async def run_queue_worker(queue: RedisQueue, email_service: EmailService):
    """Run the queue worker in an async context"""
    try:
        worker = EmailWorker(queue, email_service)
        await worker.start()
    except Exception as e:
        logging.error(f"Queue worker error: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """Initialize application dependencies on startup"""
    config = Config()
    await init_database()
    
    # Initialize services
    db = Database()
    validator = EmailValidator()
    queue = RedisQueue(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        queue_name=os.getenv('REDIS_QUEUE_NAME', 'email_queue')
    )
    # Initialize Redis connection
    await queue.connect()
    
    email_service = EmailService(db, validator)
    
    # Start queue worker as a background task
    app.state.worker_task = asyncio.create_task(
        run_queue_worker(queue, email_service)
    )

    # Store instances in app state
    app.state.db = db
    app.state.queue = queue
    app.state.email_service = email_service

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if hasattr(app.state, 'queue'):
        await app.state.queue.close()