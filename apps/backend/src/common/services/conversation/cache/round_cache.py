"""
Round cache for conversation operations.

Handles Redis caching for conversation rounds with pattern-based operations.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.db.redis.service import RedisService

logger = logging.getLogger(__name__)


class ConversationRoundCache:
    """Specialized cache for conversation rounds."""

    def __init__(self, redis_service: RedisService | None = None, default_ttl: int = 1800) -> None:
        self.redis = redis_service or RedisService()
        self.default_ttl = default_ttl

    def get_round_key(self, session_id: str, round_path: str) -> str:
        """Generate cache key for round."""
        return f"conv:round:{session_id}:{round_path}"

    def get_session_rounds_pattern(self, session_id: str) -> str:
        """Generate pattern for all rounds in a session."""
        return f"conv:round:{session_id}:*"

    async def cache_round(
        self, session_id: str, round_path: str, round_data: dict[str, Any], ttl: int | None = None
    ) -> bool:
        """
        Cache round data with TTL.

        Args:
            session_id: Session ID
            round_path: Round path identifier
            round_data: Round data to cache
            ttl: Time to live in seconds (default: self.default_ttl)

        Returns:
            True if cached successfully, False otherwise
        """
        try:
            key = self.get_round_key(session_id, round_path)
            ttl_value = ttl or self.default_ttl

            await self.redis.set(key, json.dumps(round_data), expire=ttl_value)
            logger.debug(f"Cached round {session_id}:{round_path} with TTL {ttl_value}s")
            return True

        except Exception as e:
            logger.error(f"Round cache error: {e}")
            return False

    async def get_round(self, session_id: str, round_path: str) -> dict[str, Any] | None:
        """
        Get cached round data.

        Args:
            session_id: Session ID
            round_path: Round path identifier

        Returns:
            Round data dict or None if not found
        """
        try:
            key = self.get_round_key(session_id, round_path)
            cached = await self.redis.get(key)

            if cached:
                return json.loads(cached)
            return None

        except Exception as e:
            logger.error(f"Round cache retrieval error: {e}")
            return None

    async def delete_round(self, session_id: str, round_path: str) -> bool:
        """
        Delete cached round.

        Args:
            session_id: Session ID
            round_path: Round path identifier

        Returns:
            True if deleted, False otherwise
        """
        try:
            key = self.get_round_key(session_id, round_path)
            result = await self.redis.delete(key)
            return bool(result)

        except Exception as e:
            logger.error(f"Round cache deletion error: {e}")
            return False

    async def get_round_ttl(self, session_id: str, round_path: str) -> int | None:
        """
        Get remaining TTL for round.

        Args:
            session_id: Session ID
            round_path: Round path identifier

        Returns:
            TTL in seconds or None if not found or no TTL
        """
        try:
            key = self.get_round_key(session_id, round_path)
            ttl = await self.redis.ttl(key)

            if ttl > 0:
                return ttl
            return None

        except Exception as e:
            logger.error(f"Round TTL retrieval error: {e}")
            return None

    async def get_session_rounds(self, session_id: str) -> list[dict[str, Any]]:
        """
        Get all cached rounds for a session using SCAN for performance.

        Args:
            session_id: Session ID

        Returns:
            List of round data dicts
        """
        try:
            pattern = self.get_session_rounds_pattern(session_id)
            keys = []

            # Use SCAN instead of KEYS for better performance in production
            cursor = 0
            while True:
                cursor, batch_keys = await self.redis.scan(cursor, match=pattern, count=100)
                keys.extend(batch_keys)
                if cursor == 0:
                    break

            if not keys:
                return []

            # Get all round data in batch using MGET
            cached_data = await self.redis.mget(keys)
            rounds = []

            for data in cached_data:
                if data:
                    try:
                        rounds.append(json.loads(data))
                    except json.JSONDecodeError:
                        continue

            return rounds

        except Exception as e:
            logger.error(f"Session rounds retrieval error: {e}")
            return []

    async def clear_session_rounds(self, session_id: str) -> int:
        """
        Clear all cached rounds for a session using SCAN for performance.

        Args:
            session_id: Session ID

        Returns:
            Number of rounds cleared
        """
        try:
            pattern = self.get_session_rounds_pattern(session_id)
            keys = []

            # Use SCAN instead of KEYS for better performance
            cursor = 0
            while True:
                cursor, batch_keys = await self.redis.scan(cursor, match=pattern, count=100)
                keys.extend(batch_keys)
                if cursor == 0:
                    break

            if not keys:
                return 0

            # Delete keys in batches to avoid large single DELETE operations
            deleted_total = 0
            batch_size = 100
            for i in range(0, len(keys), batch_size):
                batch = keys[i : i + batch_size]
                deleted = await self.redis.delete(*batch)
                deleted_total += deleted

            logger.debug(f"Cleared {deleted_total} rounds for session {session_id}")
            return deleted_total

        except Exception as e:
            logger.error(f"Session rounds clearing error: {e}")
            return 0
