"""
Cache manager for conversation operations.

Facade that coordinates specialized session and round cache strategies.
"""

from __future__ import annotations

import logging
from typing import Any

from src.db.redis.service import RedisService

from .round_cache import ConversationRoundCache
from .session_cache import ConversationSessionCache

logger = logging.getLogger(__name__)


class ConversationCacheManager:
    """
    Facade for conversation caching operations.

    Delegates to specialized cache strategies while maintaining backward compatibility.
    """

    def __init__(self, session_ttl: int = 2592000, round_ttl: int = 1800) -> None:  # 30 days = 2,592,000 seconds
        self.redis = RedisService()
        self.session_cache = ConversationSessionCache(default_ttl=session_ttl)
        self.round_cache = ConversationRoundCache(default_ttl=round_ttl)
        self.default_session_ttl = session_ttl
        self.default_round_ttl = round_ttl
        self._connected = False

    # ---------- Connection Management ----------

    async def connect(self) -> bool:
        """Connect to Redis."""
        try:
            # First establish Redis connection, then ping
            await self.redis.connect()
            await self.redis.ping()
            self._connected = True
            logger.debug("Connected to conversation cache")
            return True
        except Exception as e:
            logger.error(f"Cache connection error: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        try:
            # Properly disconnect from Redis service
            await self.redis.disconnect()
            self._connected = False
            logger.debug("Disconnected from conversation cache")
        except Exception as e:
            logger.error(f"Cache disconnection error: {e}")

    async def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected

    async def _ensure_connection(self) -> bool:
        """Ensure Redis connection is active, attempt lazy reconnection if needed."""
        if self._connected:
            try:
                # Quick health check with ping
                await self.redis.ping()
                return True
            except Exception:
                logger.warning("Redis ping failed, attempting reconnection")
                self._connected = False

        # Connection lost or never established, attempt reconnection
        if not self._connected:
            try:
                await self.redis.connect()
                await self.redis.ping()
                self._connected = True
                logger.info("Redis connection restored")
                return True
            except Exception as e:
                logger.warning(f"Failed to reconnect to Redis: {e}")
                self._connected = False
                return False

        return self._connected

    # ---------- Key Generation (Backward Compatibility) ----------

    @staticmethod
    def get_session_key(session_id: str) -> str:
        """Generate cache key for session."""
        return f"conv:session:{session_id}"

    @staticmethod
    def get_round_key(session_id: str, round_path: str) -> str:
        """Generate cache key for round."""
        return f"conv:round:{session_id}:{round_path}"

    @staticmethod
    def get_session_rounds_pattern(session_id: str) -> str:
        """Generate pattern for all rounds in a session."""
        return f"conv:round:{session_id}:*"

    # ---------- Session Operations ----------

    async def cache_session(self, session_id: str, session_data: dict[str, Any], ttl: int | None = None) -> bool:
        """Cache session data with TTL."""
        if not await self._ensure_connection():
            logger.warning("Cache unavailable: session caching skipped")
            return False
        return await self.session_cache.cache_session(session_id, session_data, ttl)

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get cached session data."""
        if not await self._ensure_connection():
            return None
        return await self.session_cache.get_session(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """Delete cached session."""
        if not await self._ensure_connection():
            logger.warning("Cache unavailable: session deletion skipped")
            return False
        return await self.session_cache.delete_session(session_id)

    async def get_session_ttl(self, session_id: str) -> int | None:
        """Get remaining TTL for session."""
        if not await self._ensure_connection():
            return None
        return await self.session_cache.get_session_ttl(session_id)

    async def renew_session_ttl(self, session_id: str, ttl: int | None = None) -> bool:
        """Renew session TTL."""
        if not await self._ensure_connection():
            logger.warning("Cache unavailable: session TTL renewal skipped")
            return False
        return await self.session_cache.renew_session_ttl(session_id, ttl)

    # ---------- Round Operations ----------

    async def cache_round(
        self, session_id: str, round_path: str, round_data: dict[str, Any], ttl: int | None = None
    ) -> bool:
        """Cache round data with TTL."""
        if not await self._ensure_connection():
            logger.warning("Cache unavailable: round caching skipped")
            return False
        return await self.round_cache.cache_round(session_id, round_path, round_data, ttl)

    async def get_round(self, session_id: str, round_path: str) -> dict[str, Any] | None:
        """Get cached round data."""
        if not await self._ensure_connection():
            return None
        return await self.round_cache.get_round(session_id, round_path)

    async def delete_round(self, session_id: str, round_path: str) -> bool:
        """Delete cached round."""
        if not await self._ensure_connection():
            logger.warning("Cache unavailable: round deletion skipped")
            return False
        return await self.round_cache.delete_round(session_id, round_path)

    async def get_round_ttl(self, session_id: str, round_path: str) -> int | None:
        """Get remaining TTL for round."""
        if not await self._ensure_connection():
            return None
        return await self.round_cache.get_round_ttl(session_id, round_path)

    # ---------- Batch Operations ----------

    async def get_session_rounds(self, session_id: str) -> list[dict[str, Any]]:
        """Get all cached rounds for a session."""
        if not await self._ensure_connection():
            return []
        return await self.round_cache.get_session_rounds(session_id)

    async def clear_session(self, session_id: str) -> dict[str, Any]:
        """
        Clear all cached data for a session (session + rounds).

        Args:
            session_id: Session ID

        Returns:
            Dict with operation results
        """
        try:
            if not await self._ensure_connection():
                return {"success": False, "error": "Cache unavailable"}

            session_deleted = await self.session_cache.delete_session(session_id)
            rounds_cleared = await self.round_cache.clear_session_rounds(session_id)

            return {
                "success": True,
                "session_deleted": session_deleted,
                "rounds_cleared": rounds_cleared,
            }
        except Exception as e:
            logger.error(f"Session clearing error: {e}")
            return {"success": False, "error": str(e)}

    # ---------- Statistics ----------

    async def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics using SCAN for performance.

        Returns:
            Dict with cache statistics
        """
        try:
            if not await self._ensure_connection():
                return {"connected": False, "error": "Cache unavailable"}

            info = await self.redis.info("memory")
            keyspace_info = await self.redis.info("keyspace")

            # Count conversation-related keys using SCAN instead of KEYS
            session_pattern = "conv:session:*"
            round_pattern = "conv:round:*"

            # Count session keys
            session_count = 0
            cursor = 0
            while True:
                cursor, batch_keys = await self.redis.scan(cursor, match=session_pattern, count=100)
                session_count += len(batch_keys)
                if cursor == 0:
                    break

            # Count round keys
            round_count = 0
            cursor = 0
            while True:
                cursor, batch_keys = await self.redis.scan(cursor, match=round_pattern, count=100)
                round_count += len(batch_keys)
                if cursor == 0:
                    break

            stats = {
                "connected": self._connected,
                "redis_memory_used": info.get("used_memory", 0),
                "redis_memory_human": info.get("used_memory_human", "0B"),
                "total_keys": keyspace_info.get("db0", {}).get("keys", 0) if "db0" in keyspace_info else 0,
                "conversation_sessions": session_count,
                "conversation_rounds": round_count,
                "default_session_ttl": self.default_session_ttl,
                "default_round_ttl": self.default_round_ttl,
            }

            return {"success": True, "stats": stats}

        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"success": False, "error": str(e)}


__all__ = ["ConversationCacheManager"]
