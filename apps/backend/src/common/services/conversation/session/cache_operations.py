"""
Session cache operations helper for conversation services.

Handles caching operations with error handling and logging.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.common.services.conversation.cache import ConversationCacheManager
from src.common.services.conversation.conversation_serializers import ConversationSerializer

logger = logging.getLogger(__name__)


class ConversationSessionCacheOperations:
    """Helper for conversation session cache operations."""

    def __init__(self, cache: ConversationCacheManager, serializer: ConversationSerializer) -> None:
        self.cache = cache
        self.serializer = serializer

    async def get_cached_session(self, session_id: UUID) -> dict[str, Any] | None:
        """
        Get session from cache with error handling.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Cached session dict or None if not found/error
        """
        try:
            return await self.cache.get_session(str(session_id))
        except Exception as cache_error:
            logger.warning(
                f"Failed to get session from cache {session_id}: {cache_error}",
                extra={"session_id": str(session_id), "operation": "cache_get_error"},
            )
            return None

    async def cache_session(self, session_id: UUID, serialized_session: dict[str, Any]) -> None:
        """
        Cache session with error handling (best effort).

        Args:
            session_id: Session ID
            serialized_session: Serialized session data
        """
        try:
            await self.cache.cache_session(str(session_id), serialized_session)
            logger.debug(f"Cached session {session_id}")
        except Exception as cache_error:
            # Cache failure should not affect main business flow
            logger.warning(
                f"Failed to cache session {session_id}: {cache_error}",
                extra={"session_id": str(session_id), "operation": "cache_set_error"},
            )

    async def clear_cached_session(self, session_id: UUID) -> None:
        """
        Clear session from cache with error handling (best effort).

        Args:
            session_id: Session ID to clear
        """
        try:
            await self.cache.clear_session(str(session_id))
            logger.debug(f"Cleared cache for session {session_id}")
        except Exception as cache_error:
            # Cache failure should not affect main business flow
            logger.warning(
                f"Failed to clear cache for session {session_id}: {cache_error}",
                extra={"session_id": str(session_id), "operation": "cache_clear_error"},
            )

    def serialize_session_with_logging(self, session: Any, operation: str = "serialize") -> dict[str, Any]:
        """
        Serialize session with debug logging.

        Args:
            session: Session ORM object to serialize
            operation: Operation name for logging

        Returns:
            Serialized session dict
        """
        logger.debug(f"Serializing session for {operation}")
        serialized_session = self.serializer.serialize_session(session)
        logger.debug(f"Serialized session keys: {serialized_session.keys()}")
        return serialized_session
