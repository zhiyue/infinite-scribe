"""Redis service implementation for caching and session management."""

from contextlib import asynccontextmanager

import redis.asyncio as redis

from src.core.config import settings


class RedisService:
    """Service for interacting with Redis."""

    def __init__(self):
        """Initialize Redis service."""
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if not self._client:
            self._client = redis.from_url(
                settings.database.redis_url,
                decode_responses=True,
                health_check_interval=30,
                socket_connect_timeout=5,
                socket_timeout=5,
            )

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def check_connection(self) -> bool:
        """Check if Redis is accessible."""
        try:
            if self._client:
                await self._client.ping()
                return True
            return False
        except Exception:
            return False

    async def get(self, key: str) -> str | None:
        """Get value from Redis."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.get(key)

    async def set(self, key: str, value: str, expire: int | None = None) -> None:
        """Set value in Redis with optional expiration."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        await self._client.set(key, value, ex=expire)

    async def delete(self, key: str) -> None:
        """Delete key from Redis."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return bool(await self._client.exists(key))

    @asynccontextmanager
    async def acquire(self):
        """Context manager for Redis operations."""
        if not self._client:
            await self.connect()
        try:
            yield self._client
        finally:
            pass  # Keep connection open for reuse


redis_service = RedisService()
