import aiomysql
from contextlib import asynccontextmanager
import os
from typing import Dict
import logging
from src.config import Config

class Database:
    def __init__(self):
        self.pool = None
        self.config = Config()
        
    async def init_pool(self):
        """Initialize the connection pool"""
        if not self.pool:
            try:
                self.pool = await aiomysql.create_pool(
                    host=self.config.DB_HOST,
                    port=self.config.DB_PORT,
                    user=self.config.DB_USER,
                    password=self.config.DB_PASSWORD,
                    db=self.config.DB_NAME,
                    autocommit=True,
                    minsize=1,
                    maxsize=10
                )
            except Exception as e:
                logging.error(f"Failed to initialize database pool: {str(e)}")
                raise

    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool"""
        if not self.pool:
            await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    yield cursor
                except Exception as e:
                    logging.error(f"Database error: {str(e)}")
                    await conn.rollback()
                    raise
                finally:
                    await cursor.close()

    async def close(self):
        """Close the connection pool"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()