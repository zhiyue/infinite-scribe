"""
Session read operations handler for conversation services.

Handles session retrieval and listing with caching and access control.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.conversation import ConversationSessionRepository
from src.common.services.conversation.conversation_error_handler import ConversationErrorHandler
from src.common.services.conversation.conversation_serializers import ConversationSerializer
from src.common.services.conversation.session.access_operations import (
    ConversationSessionAccessOperations,
)
from src.common.services.conversation.session.cache_operations import (
    ConversationSessionCacheOperations,
)

logger = logging.getLogger(__name__)


class ConversationSessionReadHandler:
    """Handler for conversation session read operations."""

    def __init__(
        self,
        cache_ops: ConversationSessionCacheOperations,
        access_ops: ConversationSessionAccessOperations,
        serializer: ConversationSerializer,
        repository_factory: Callable[[AsyncSession], ConversationSessionRepository],
    ) -> None:
        self._cache_ops = cache_ops
        self._access_ops = access_ops
        self._serializer = serializer
        self._repo_factory = repository_factory

    async def get_session(self, db: AsyncSession, user_id: int, session_id: UUID) -> dict[str, Any]:
        """
        Get a conversation session by ID.

        Args:
            db: Database session
            user_id: User ID for ownership verification
            session_id: Session ID to retrieve

        Returns:
            Dict with success status and session or error details
        """
        try:
            # Try cache first
            cached = await self._cache_ops.get_cached_session(session_id)
            if cached:
                # Verify access to cached session
                access_result = await self._access_ops.verify_cached_session_access(db, user_id, cached)
                if not access_result["success"]:
                    return access_result
                # Log successful cache hit with context
                logger.info(
                    "Session retrieved from cache successfully",
                    extra={
                        "session_id": str(session_id),
                        "user_id": user_id,
                        "from_cache": True,
                        "operation": "get_session_cache_success",
                    },
                )
                return ConversationErrorHandler.success_response({"session": cached, "cached": True})

            # Get repository from factory
            repository = self._repo_factory(db)

            # Fallback to database with access verification
            session = await repository.find_by_id(session_id)
            if not session:
                return ConversationErrorHandler.not_found_error(
                    "Session", logger_instance=logger, context="Get session not found"
                )

            # Verify access to the found session
            access_result = await self._access_ops.verify_session_access(db, user_id, session, "get_session")
            if not access_result["success"]:
                return access_result

            # Serialize ORM object to dict at service boundary
            serialized_session = self._cache_ops.serialize_session_with_logging(session, "get_session")

            # Cache for future use (best effort) - already serialized
            await self._cache_ops.cache_session(session.id, serialized_session)

            # Log successful operation with context
            logger.info(
                "Session retrieved successfully with context",
                extra={
                    "session_id": str(session_id),
                    "user_id": user_id,
                    "from_cache": False,
                    "operation": "get_session_success",
                },
            )
            return ConversationErrorHandler.success_response({"session": serialized_session})

        except Exception as e:
            # Add structured logging with context before error response
            logger.error(
                "Session retrieval failed with detailed context",
                extra={
                    "session_id": str(session_id),
                    "user_id": user_id,
                    "attempted_cache": True,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            return ConversationErrorHandler.internal_error(
                "Failed to get session",
                logger_instance=logger,
                context=f"Get session error - session: {session_id}, user: {user_id}",
                exception=e,
                session_id=str(session_id),
                user_id=user_id,
            )

    async def list_sessions(
        self,
        db: AsyncSession,
        user_id: int,
        scope_type: str,
        scope_id: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List conversation sessions for a given scope.

        Args:
            db: Database session
            user_id: User ID for ownership verification
            scope_type: Scope type
            scope_id: Scope identifier
            status: Optional status filter
            limit: Maximum number of sessions to return
            offset: Offset for pagination

        Returns:
            Dict with success status and sessions list or error details
        """
        try:
            # Verify user has access to this scope
            access_result = await self._access_ops.verify_scope_access(db, user_id, scope_type, scope_id)
            if not access_result["success"]:
                return access_result

            # Get repository from factory
            repository = self._repo_factory(db)

            # Get sessions from repository
            sessions = await repository.list_by_scope(
                scope_type=scope_type,
                scope_id=scope_id,
                status=status,
                limit=limit,
                offset=offset,
            )

            # Serialize ORM objects to dicts at service boundary
            serialized_sessions = [self._serializer.serialize_session(session) for session in sessions]

            # Log successful operation with context
            logger.info(
                "Sessions listed successfully with context",
                extra={
                    "scope_type": scope_type,
                    "scope_id": scope_id,
                    "user_id": user_id,
                    "session_count": len(serialized_sessions),
                    "status_filter": status,
                    "limit": limit,
                    "offset": offset,
                    "operation": "list_sessions_success",
                },
            )
            return ConversationErrorHandler.success_response({"sessions": serialized_sessions})

        except Exception as e:
            # Add structured logging with context before error response
            logger.error(
                "Session listing failed with detailed context",
                extra={
                    "scope_type": scope_type,
                    "scope_id": scope_id,
                    "user_id": user_id,
                    "status_filter": status,
                    "limit": limit,
                    "offset": offset,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            return ConversationErrorHandler.internal_error(
                "Failed to list sessions",
                logger_instance=logger,
                context=f"List sessions error - scope: {scope_type}:{scope_id}, user: {user_id}",
                exception=e,
                user_id=user_id,
            )
