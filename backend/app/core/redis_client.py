"""Redis client for caching and session management"""

import json
from typing import Any, Optional
import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import settings


class RedisClient:
    """Redis client wrapper with async support"""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        self.redis = await aioredis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis
        
        Args:
            key: Redis key
            
        Returns:
            Value or None if not found
        """
        if not self.redis:
            await self.connect()
        
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ):
        """
        Set value in Redis
        
        Args:
            key: Redis key
            value: Value to store
            expire: Expiration time in seconds
        """
        if not self.redis:
            await self.connect()
        
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        await self.redis.set(key, value, ex=expire)
    
    async def delete(self, key: str):
        """
        Delete key from Redis
        
        Args:
            key: Redis key
        """
        if not self.redis:
            await self.connect()
        
        await self.redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis
        
        Args:
            key: Redis key
            
        Returns:
            bool: True if key exists
        """
        if not self.redis:
            await self.connect()
        
        return await self.redis.exists(key) > 0
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment value in Redis
        
        Args:
            key: Redis key
            amount: Amount to increment
            
        Returns:
            int: New value
        """
        if not self.redis:
            await self.connect()
        
        return await self.redis.incrby(key, amount)
    
    async def expire(self, key: str, seconds: int):
        """
        Set expiration time for key
        
        Args:
            key: Redis key
            seconds: Expiration time in seconds
        """
        if not self.redis:
            await self.connect()
        
        await self.redis.expire(key, seconds)


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """
    Dependency for getting Redis client
    
    Returns:
        RedisClient: Redis client instance
    """
    if not redis_client.redis:
        await redis_client.connect()
    return redis_client

