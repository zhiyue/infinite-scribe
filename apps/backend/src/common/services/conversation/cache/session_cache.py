"""
Session cache for conversation operations.

Handles Redis caching for conversation sessions with TTL management.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.db.redis.service import redis_service

logger = logging.getLogger(__name__)


class ConversationSessionCache:
    """Specialized cache for conversation sessions."""

    def __init__(self, default_ttl: int = 2592000) -> None:  # 30 days = 2,592,000 seconds
        self.redis = redis_service  # Use the global connected Redis service
        self.default_ttl = default_ttl

    def get_session_key(self, session_id: str) -> str:
        """Generate cache key for session."""
        return f"conv:session:{session_id}"

    async def cache_session(self, session_id: str, session_data: dict[str, Any], ttl: int | None = None) -> bool:
        """
        Cache session data with TTL.

        Args:
            session_id: Session ID
            session_data: Session data to cache
            ttl: Time to live in seconds (default: self.default_ttl)

        Returns:
            True if cached successfully, False otherwise
        """
        try:
            key = self.get_session_key(session_id)
            ttl_value = ttl or self.default_ttl

            await self.redis.set(key, json.dumps(session_data), expire=ttl_value)
            logger.debug(f"Cached session {session_id} with TTL {ttl_value}s")
            return True

        except Exception as e:
            logger.error(f"Session cache error: {e}")
            return False

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """
        Get cached session data.

        Args:
            session_id: Session ID

        Returns:
            Session data dict or None if not found
        """
        try:
            key = self.get_session_key(session_id)
            cached = await self.redis.get(key)

            if cached:
                return json.loads(cached)
            return None

        except Exception as e:
            logger.error(f"Session cache retrieval error: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete cached session.

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            key = self.get_session_key(session_id)
            result = await self.redis.delete(key)
            return bool(result)

        except Exception as e:
            logger.error(f"Session cache deletion error: {e}")
            return False

    async def get_session_ttl(self, session_id: str) -> int | None:
        """
        Get remaining TTL for session.

        Args:
            session_id: Session ID

        Returns:
            TTL in seconds or None if not found or no TTL
        """
        try:
            key = self.get_session_key(session_id)
            ttl = await self.redis.ttl(key)

            if ttl > 0:
                return ttl
            return None

        except Exception as e:
            logger.error(f"Session TTL retrieval error: {e}")
            return None

    async def renew_session_ttl(self, session_id: str, ttl: int | None = None) -> bool:
        """
        Renew session TTL.

        Args:
            session_id: Session ID
            ttl: New TTL in seconds (default: self.default_ttl)

        Returns:
            True if renewed, False otherwise
        """
        try:
            key = self.get_session_key(session_id)
            ttl_value = ttl or self.default_ttl

            result = await self.redis.expire(key, ttl_value)
            if result:
                logger.debug(f"Renewed session {session_id} TTL to {ttl_value}s")
            return bool(result)

        except Exception as e:
            logger.error(f"Session TTL renewal error: {e}")
            return False
