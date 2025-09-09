"""Redis service implementation for caching and session management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import redis.asyncio as redis

from src.core.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """Service for interacting with Redis."""

    def __init__(self):
        """Initialize Redis service."""
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if not self._client:
            logger.info(
                "Connecting to Redis",
                extra={
                    "host": settings.database.redis_host,
                    "port": settings.database.redis_port,
                },
            )
            self._client = redis.from_url(
                settings.database.redis_url,
                decode_responses=True,
                health_check_interval=30,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            try:
                await self._client.ping()
                logger.info("Redis ping successful (client ready)")
            except Exception as e:
                logger.warning(f"Redis ping failed during connect: {e}")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis client closed")

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

    async def delete(self, *keys: str) -> int:
        """Delete key(s) from Redis. Returns number of keys deleted."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        if not keys:
            return 0
        return await self._client.delete(*keys)

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return bool(await self._client.exists(key))

    async def ping(self) -> bool:
        """Ping Redis server."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        try:
            await self._client.ping()
            return True
        except Exception:
            return False

    async def info(self, section: str | None = None) -> dict:
        """Get Redis server info."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.info(section)

    async def keys(self, pattern: str) -> list[str]:
        """Get keys matching pattern. Use scan() in production for better performance."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.keys(pattern)

    async def scan(self, cursor: int = 0, match: str | None = None, count: int | None = None) -> tuple[int, list[str]]:
        """Scan keys with cursor. Better performance than keys() for large datasets."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.scan(cursor=cursor, match=match, count=count)

    async def mget(self, keys: list[str]) -> list[str | None]:
        """Get multiple values."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        if not keys:
            return []
        return await self._client.mget(keys)

    async def ttl(self, key: str) -> int:
        """Get time to live for key in seconds. Returns -1 if no expiry, -2 if key doesn't exist."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.ttl(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiry for key in seconds."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.expire(key, seconds)

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[redis.Redis, None]:
        """Context manager for Redis operations."""
        if not self._client:
            await self.connect()

        if not self._client:
            raise RuntimeError("Failed to connect to Redis")

        try:
            yield self._client
        finally:
            pass  # Keep connection open for reuse


redis_service = RedisService()
