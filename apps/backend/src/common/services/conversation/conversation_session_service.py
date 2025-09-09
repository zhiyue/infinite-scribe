"""
Session service for conversation operations.

Handles CRUD operations for conversation sessions with caching and access control.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.conversation import ConversationSessionRepository, SqlAlchemyConversationSessionRepository
from src.common.services.conversation.conversation_access_control import ConversationAccessControl
from src.common.services.conversation.conversation_cache import ConversationCacheManager
from src.common.services.conversation.conversation_error_handler import ConversationErrorHandler
from src.common.services.conversation.conversation_serializers import ConversationSerializer
from src.db.sql.session import transactional
from src.schemas.novel.dialogue import ScopeType, SessionStatus

logger = logging.getLogger(__name__)


class ConversationSessionService:
    """Service for conversation session operations."""

    def __init__(
        self,
        cache: ConversationCacheManager | None = None,
        access_control: ConversationAccessControl | None = None,
        serializer: ConversationSerializer | None = None,
        repository: ConversationSessionRepository | None = None,
        repository_factory: Callable[[AsyncSession], ConversationSessionRepository] | None = None,
    ) -> None:
        self.cache = cache or ConversationCacheManager()
        self.access_control = access_control or ConversationAccessControl()
        self.serializer = serializer or ConversationSerializer()

        # Repository factory pattern - prioritize factory > instance > default
        if repository_factory:
            self._repo_factory = repository_factory
        elif repository:
            self._repo_factory = lambda _: repository  # Convert instance to factory
        else:
            self._repo_factory = SqlAlchemyConversationSessionRepository

    async def create_session(
        self,
        db: AsyncSession,
        user_id: int,
        scope_type: ScopeType,
        scope_id: str,
        stage: str | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new conversation session.

        Args:
            db: Database session
            user_id: User ID for ownership
            scope_type: Type of scope (currently only GENESIS supported)
            scope_id: ID of the scope (novel ID for GENESIS)
            stage: Optional stage name
            initial_state: Optional initial state data

        Returns:
            Dict with success status and session or error details
        """
        try:
            if scope_type != ScopeType.GENESIS:
                return ConversationErrorHandler.validation_error(
                    "Only GENESIS scope is supported", logger_instance=logger, context="Create session validation"
                )

            # Verify access to the scope
            novel_result = await self.access_control.get_novel_for_scope(db, user_id, scope_type.value, scope_id)
            if not novel_result["success"]:
                return novel_result

            # Get repository from factory
            repository = self._repo_factory(db)

            # Check for existing active session
            existing = await repository.find_active_by_scope(scope_type.value, str(scope_id))
            if existing:
                return ConversationErrorHandler.conflict_error(
                    "An active session already exists for this novel",
                    logger_instance=logger,
                    context="Create session conflict",
                )

            # Create new session with transactional support
            async with transactional(db):
                session = await repository.create(
                    scope_type=scope_type.value,
                    scope_id=str(scope_id),
                    status=SessionStatus.ACTIVE.value,
                    stage=stage,
                    state=initial_state or {},
                    version=1,
                )

            # Serialize ORM object to dict at service boundary
            serialized_session = self.serializer.serialize_session(session)

            # Cache write-through (best effort) - already serialized
            try:
                await self.cache.cache_session(str(session.id), serialized_session)
                logger.debug(f"Cached session {session.id}")
            except Exception as cache_error:
                # Cache failure should not affect main business flow
                logger.warning(
                    f"Failed to cache session {session.id}: {cache_error}", extra={"session_id": str(session.id)}
                )

            return ConversationErrorHandler.success_response({"session": serialized_session})

        except Exception as e:
            return ConversationErrorHandler.internal_error(
                "Failed to create session",
                logger_instance=logger,
                context="Create session error",
                exception=e,
                session_id=str(session.id) if "session" in locals() else None,
                user_id=user_id,
            )

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
            cached = await self.cache.get_session(str(session_id))
            if cached:
                # Verify access to cached session
                access_result = await self.access_control.verify_cached_session_access(db, user_id, cached)
                if not access_result["success"]:
                    return access_result
                # Cache already contains serialized dict
                return ConversationErrorHandler.success_response({"session": cached, "cached": True})

            # Get repository from factory
            repository = self._repo_factory(db)

            # Fallback to database with access verification
            session = await repository.find_by_id(session_id)
            if not session:
                return ConversationErrorHandler.not_found_error(
                    "Session not found", logger_instance=logger, context="Get session not found"
                )

            # Verify access to the found session
            access_result = await self.access_control.verify_cached_session_access(
                db, user_id, {"scope_type": session.scope_type, "scope_id": session.scope_id, "status": session.status}
            )
            if not access_result["success"]:
                return access_result

            # Serialize ORM object to dict at service boundary
            serialized_session = self.serializer.serialize_session(session)

            # Cache for future use (best effort) - already serialized
            try:
                await self.cache.cache_session(str(session.id), serialized_session)
                logger.debug(f"Cached session {session.id}")
            except Exception as cache_error:
                # Cache failure should not affect main business flow
                logger.warning(
                    f"Failed to cache session {session.id}: {cache_error}", extra={"session_id": str(session.id)}
                )

            return ConversationErrorHandler.success_response({"session": serialized_session})

        except Exception as e:
            return ConversationErrorHandler.internal_error(
                "Failed to get session",
                logger_instance=logger,
                context="Get session error",
                exception=e,
                session_id=str(session_id),
                user_id=user_id,
            )

    async def update_session(
        self,
        db: AsyncSession,
        user_id: int,
        session_id: UUID,
        *,
        status: SessionStatus | None = None,
        stage: str | None = None,
        state: dict[str, Any] | None = None,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        """
        Update a conversation session with optimistic concurrency control.

        Args:
            db: Database session
            user_id: User ID for ownership verification
            session_id: Session ID to update
            status: New status (optional)
            stage: New stage (optional)
            state: New state (optional)
            expected_version: Expected version for optimistic locking (optional)

        Returns:
            Dict with success status and updated session or error details
        """
        try:
            # Get repository from factory
            repository = self._repo_factory(db)

            # Get session first to verify access
            session = await repository.find_by_id(session_id)
            if not session:
                return ConversationErrorHandler.not_found_error(
                    "Session not found", logger_instance=logger, context="Update session not found"
                )

            # Verify access to the found session
            access_result = await self.access_control.verify_cached_session_access(
                db, user_id, {"scope_type": session.scope_type, "scope_id": session.scope_id, "status": session.status}
            )
            if not access_result["success"]:
                return access_result

            # Check if there are no values to update
            if status is None and stage is None and state is None:
                # Nothing to update - serialize ORM object at service boundary
                serialized_session = self.serializer.serialize_session(session)
                return ConversationErrorHandler.success_response({"session": serialized_session})

            # Update with optimistic concurrency control using transactional support
            async with transactional(db):
                updated_session = await repository.update(
                    session_id=session_id,
                    status=status.value if status else None,
                    stage=stage,
                    state=state,
                    expected_version=expected_version,
                )

                if not updated_session:
                    return ConversationErrorHandler.precondition_failed_error(
                        "Version mismatch or conflict",
                        logger_instance=logger,
                        context="Update session version conflict",
                    )

            # Serialize ORM object to dict at service boundary
            serialized_updated = self.serializer.serialize_session(updated_session)

            # Update cache (best effort) - already serialized
            try:
                await self.cache.cache_session(str(updated_session.id), serialized_updated)
                logger.debug(f"Updated cache for session {updated_session.id}")
            except Exception as cache_error:
                # Cache failure should not affect main business flow
                logger.warning(
                    f"Failed to update cache for session {updated_session.id}: {cache_error}",
                    extra={"session_id": str(updated_session.id)},
                )

            return ConversationErrorHandler.success_response({"session": serialized_updated})

        except Exception as e:
            return ConversationErrorHandler.internal_error(
                "Failed to update session",
                logger_instance=logger,
                context="Update session error",
                exception=e,
                session_id=str(session_id),
                user_id=user_id,
            )

    async def delete_session(self, db: AsyncSession, user_id: int, session_id: UUID) -> dict[str, Any]:
        """
        Delete a conversation session.

        Args:
            db: Database session
            user_id: User ID for ownership verification
            session_id: Session ID to delete

        Returns:
            Dict with success status or error details
        """
        try:
            # Get repository from factory
            repository = self._repo_factory(db)

            # Get session first to verify access
            session = await repository.find_by_id(session_id)
            if not session:
                return ConversationErrorHandler.not_found_error(
                    "Session not found", logger_instance=logger, context="Delete session not found"
                )

            # Verify access to the found session
            access_result = await self.access_control.verify_cached_session_access(
                db, user_id, {"scope_type": session.scope_type, "scope_id": session.scope_id, "status": session.status}
            )
            if not access_result["success"]:
                return access_result

            # Delete session using transactional support
            async with transactional(db):
                success = await repository.delete(session_id)
                if not success:
                    return ConversationErrorHandler.not_found_error(
                        "Session not found during deletion", logger_instance=logger, context="Delete session failed"
                    )

            # Clear cache (best effort)
            try:
                await self.cache.clear_session(str(session_id))
                logger.debug(f"Cleared cache for session {session_id}")
            except Exception as cache_error:
                # Cache failure should not affect main business flow
                logger.warning(
                    f"Failed to clear cache for session {session_id}: {cache_error}",
                    extra={"session_id": str(session_id)},
                )

            return ConversationErrorHandler.success_response()

        except Exception as e:
            return ConversationErrorHandler.internal_error(
                "Failed to delete session",
                logger_instance=logger,
                context="Delete session error",
                exception=e,
                session_id=str(session_id),
                user_id=user_id,
            )
