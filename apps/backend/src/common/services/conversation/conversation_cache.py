"""
Conversation Cache Manager for Redis

Manages Redis-based caching for conversation sessions and rounds
with proper TTL management as specified in Task 1.
"""

import json
import logging
from typing import Any

from src.db.redis import redis_service

logger = logging.getLogger(__name__)


class ConversationCacheManager:
    """Manages conversation session and round caching with Redis."""

    def __init__(self):
        """Initialize conversation cache manager."""
        # 30 days TTL as specified in Task 1
        self.default_session_ttl = 30 * 24 * 60 * 60  # 30 days in seconds
        self.default_round_ttl = 30 * 24 * 60 * 60  # Same as session TTL
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Redis service."""
        try:
            await redis_service.connect()
            self._connected = await redis_service.check_connection()
            if self._connected:
                logger.info("ConversationCacheManager connected to Redis")
            return self._connected
        except Exception as e:
            logger.error(f"Failed to connect ConversationCacheManager to Redis: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis service."""
        try:
            await redis_service.disconnect()
            self._connected = False
            logger.info("ConversationCacheManager disconnected from Redis")
        except Exception as e:
            logger.warning(f"Error during ConversationCacheManager disconnect: {e}")

    async def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected and await redis_service.check_connection()

    def get_session_key(self, session_id: str) -> str:
        """Generate Redis key for conversation session."""
        return f"conversation:session:{session_id}"

    def get_round_key(self, session_id: str, round_path: str) -> str:
        """Generate Redis key for conversation round."""
        return f"conversation:session:{session_id}:round:{round_path}"

    def get_session_rounds_pattern(self, session_id: str) -> str:
        """Generate Redis key pattern for all rounds in a session."""
        return f"conversation:session:{session_id}:round:*"

    async def cache_session(self, session_id: str, session_data: dict[str, Any], ttl: int | None = None) -> bool:
        """Cache conversation session data with TTL."""
        try:
            if not await self.is_connected():
                await self.connect()

            key = self.get_session_key(session_id)
            data_json = json.dumps(session_data)
            expire_seconds = ttl or self.default_session_ttl

            await redis_service.set(key, data_json, expire=expire_seconds)
            logger.debug(f"Cached session {session_id} with TTL {expire_seconds}s")
            return True

        except Exception as e:
            logger.error(f"Failed to cache session {session_id}: {e}")
            return False

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve cached conversation session data."""
        try:
            if not await self.is_connected():
                await self.connect()

            key = self.get_session_key(session_id)
            data_json = await redis_service.get(key)

            if data_json:
                return json.loads(data_json)
            return None

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """Delete cached conversation session."""
        try:
            if not await self.is_connected():
                await self.connect()

            key = self.get_session_key(session_id)
            await redis_service.delete(key)
            logger.debug(f"Deleted session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    async def get_session_ttl(self, session_id: str) -> int:
        """Get TTL for cached session."""
        try:
            if not await self.is_connected():
                await self.connect()

            key = self.get_session_key(session_id)

            async with redis_service.acquire() as client:
                ttl = await client.ttl(key)
                return ttl if ttl > 0 else 0

        except Exception as e:
            logger.error(f"Failed to get TTL for session {session_id}: {e}")
            return 0

    async def renew_session_ttl(self, session_id: str, ttl: int | None = None) -> bool:
        """Renew TTL for cached session."""
        try:
            if not await self.is_connected():
                await self.connect()

            key = self.get_session_key(session_id)
            expire_seconds = ttl or self.default_session_ttl

            async with redis_service.acquire() as client:
                await client.expire(key, expire_seconds)
                logger.debug(f"Renewed TTL for session {session_id} to {expire_seconds}s")
                return True

        except Exception as e:
            logger.error(f"Failed to renew TTL for session {session_id}: {e}")
            return False

    async def cache_round(
        self, session_id: str, round_path: str, round_data: dict[str, Any], ttl: int | None = None
    ) -> bool:
        """Cache conversation round data with TTL."""
        try:
            if not await self.is_connected():
                await self.connect()

            key = self.get_round_key(session_id, round_path)
            data_json = json.dumps(round_data)
            expire_seconds = ttl or self.default_round_ttl

            await redis_service.set(key, data_json, expire=expire_seconds)
            logger.debug(f"Cached round {session_id}:{round_path} with TTL {expire_seconds}s")
            return True

        except Exception as e:
            logger.error(f"Failed to cache round {session_id}:{round_path}: {e}")
            return False

    async def get_round(self, session_id: str, round_path: str) -> dict[str, Any] | None:
        """Retrieve cached conversation round data."""
        try:
            if not await self.is_connected():
                await self.connect()

            key = self.get_round_key(session_id, round_path)
            data_json = await redis_service.get(key)

            if data_json:
                return json.loads(data_json)
            return None

        except Exception as e:
            logger.error(f"Failed to get round {session_id}:{round_path}: {e}")
            return None

    async def delete_round(self, session_id: str, round_path: str) -> bool:
        """Delete cached conversation round."""
        try:
            if not await self.is_connected():
                await self.connect()

            key = self.get_round_key(session_id, round_path)
            await redis_service.delete(key)
            logger.debug(f"Deleted round {session_id}:{round_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete round {session_id}:{round_path}: {e}")
            return False

    async def get_round_ttl(self, session_id: str, round_path: str) -> int:
        """Get TTL for cached round."""
        try:
            if not await self.is_connected():
                await self.connect()

            key = self.get_round_key(session_id, round_path)

            async with redis_service.acquire() as client:
                ttl = await client.ttl(key)
                return ttl if ttl > 0 else 0

        except Exception as e:
            logger.error(f"Failed to get TTL for round {session_id}:{round_path}: {e}")
            return 0

    async def get_session_rounds(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieve all cached rounds for a session."""
        try:
            if not await self.is_connected():
                await self.connect()

            pattern = self.get_session_rounds_pattern(session_id)

            async with redis_service.acquire() as client:
                # Get all keys matching the pattern
                keys = await client.keys(pattern)

                if not keys:
                    return []

                # Get all values for the keys
                rounds = []
                for key in keys:
                    data_json = await client.get(key)
                    if data_json:
                        rounds.append(json.loads(data_json))

                return rounds

        except Exception as e:
            logger.error(f"Failed to get session rounds for {session_id}: {e}")
            return []

    async def clear_session(self, session_id: str) -> bool:
        """Clear all cached data for a session (session + all rounds)."""
        try:
            if not await self.is_connected():
                await self.connect()

            # Delete session
            session_key = self.get_session_key(session_id)
            await redis_service.delete(session_key)

            # Delete all rounds for this session
            pattern = self.get_session_rounds_pattern(session_id)

            async with redis_service.acquire() as client:
                keys = await client.keys(pattern)
                if keys:
                    await client.delete(*keys)

            logger.debug(f"Cleared all cached data for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear session {session_id}: {e}")
            return False

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        try:
            if not await self.is_connected():
                await self.connect()

            async with redis_service.acquire() as client:
                # Get basic Redis info
                info = await client.info()

                # Count conversation-related keys
                session_keys = await client.keys("conversation:session:*")
                session_count = len([k for k in session_keys if ":round:" not in k])
                round_count = len([k for k in session_keys if ":round:" in k])

                # Parse db0 info string like "keys=1,expires=0"
                total_keys = 0
                if "db0" in info:
                    db0_info = info["db0"]
                    if isinstance(db0_info, str) and "keys=" in db0_info:
                        try:
                            keys_part = db0_info.split(",")[0]  # Get "keys=1"
                            total_keys = int(keys_part.split("=")[1])  # Extract "1"
                        except (ValueError, IndexError):
                            total_keys = 0

                return {
                    "redis_connected": True,
                    "redis_version": info.get("redis_version", "unknown"),
                    "total_keys": total_keys,
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "conversation_sessions": session_count,
                    "conversation_rounds": round_count,
                    "default_session_ttl_days": self.default_session_ttl / (24 * 60 * 60),
                }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "redis_connected": False,
                "error": str(e),
                "conversation_sessions": 0,
                "conversation_rounds": 0,
            }


__all__ = ["ConversationCacheManager"]
