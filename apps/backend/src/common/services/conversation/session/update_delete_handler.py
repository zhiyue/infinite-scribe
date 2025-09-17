"""
Session update and delete operations handler for conversation services.

Handles session updates and deletions with optimistic concurrency and caching.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.conversation import ConversationSessionRepository
from src.common.services.conversation.conversation_error_handler import ConversationErrorHandler
from src.common.services.conversation.session.access_operations import (
    ConversationSessionAccessOperations,
)
from src.common.services.conversation.session.cache_operations import (
    ConversationSessionCacheOperations,
)
from src.common.services.conversation.session.validator import ConversationSessionValidator
from src.db.sql.session import transactional
from src.schemas.novel.dialogue import SessionStatus

logger = logging.getLogger(__name__)


class ConversationSessionUpdateDeleteHandler:
    """Handler for conversation session update and delete operations."""

    def __init__(
        self,
        cache_ops: ConversationSessionCacheOperations,
        access_ops: ConversationSessionAccessOperations,
        repository_factory: Callable[[AsyncSession], ConversationSessionRepository],
    ) -> None:
        self._cache_ops = cache_ops
        self._access_ops = access_ops
        self._repo_factory = repository_factory

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
            stage: New stage (optional, but not stored in session - handled by Genesis service)
            state: New state (optional, but not stored in session - handled by Genesis service)
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
                    "Session", logger_instance=logger, context="Update session not found"
                )

            # Verify access to the found session
            access_result = await self._access_ops.verify_session_access(db, user_id, session, "update_session")
            if not access_result["success"]:
                return access_result

            # Check if there are no values to update using validator
            # Note: We only check for status updates since stage/state are not stored in session table
            needs_update, error_response = ConversationSessionValidator.validate_session_update_params(
                status, None, None  # Pass None for stage and state since they're not stored here
            )
            if error_response:
                return error_response

            if not needs_update:
                # Nothing to update - serialize ORM object at service boundary
                serialized_session = self._cache_ops.serialize_session_with_logging(session, "update_session_no_change")
                return ConversationErrorHandler.success_response(
                    {
                        "session": session,
                        "serialized_session": serialized_session,
                    }
                )

            # Update with optimistic concurrency control using transactional support
            # Note: stage and state are no longer stored in conversation_sessions table
            async with transactional(db):
                updated_session = await repository.update(
                    session_id=session_id,
                    status=status,
                    expected_version=expected_version,
                )

                if not updated_session:
                    return ConversationErrorHandler.precondition_failed_error(
                        "Version mismatch or conflict",
                        logger_instance=logger,
                        context="Update session version conflict",
                    )

            # Serialize and update cache
            serialized_updated = self._cache_ops.serialize_session_with_logging(updated_session, "update_session")
            await self._cache_ops.cache_session(updated_session.id, serialized_updated)

            return ConversationErrorHandler.success_response(
                {
                    "session": updated_session,
                    "serialized_session": serialized_updated,
                }
            )

        except ValueError as e:
            # Handle optimistic lock conflicts and not found errors from repository
            if "not found" in str(e).lower():
                return ConversationErrorHandler.not_found_error(
                    "Session",
                    logger_instance=logger,
                    context="Update session not found",
                )
            else:
                return ConversationErrorHandler.precondition_failed_error(
                    "Version conflict: session has been modified",
                    logger_instance=logger,
                    context="Update session version conflict",
                )
        except Exception as e:
            # Add structured logging with context before error response
            logger.error(
                "Session update failed with detailed context",
                extra={
                    "session_id": str(session_id),
                    "user_id": user_id,
                    "update_status": status.value if status else None,
                    "update_stage": stage,  # Log for debugging, but not used in update
                    "has_state_update": state is not None,  # Log for debugging, but not used in update
                    "expected_version": expected_version,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            return ConversationErrorHandler.internal_error(
                "Failed to update session",
                logger_instance=logger,
                context=f"Update session error - session: {session_id}, user: {user_id}, status: {status}",
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
                    "Session", logger_instance=logger, context="Delete session not found"
                )

            # Verify access to the found session
            access_result = await self._access_ops.verify_session_access(db, user_id, session, "delete_session")
            if not access_result["success"]:
                return access_result

            # Delete session using transactional support
            async with transactional(db):
                success = await repository.delete(session_id)
                if not success:
                    return ConversationErrorHandler.not_found_error(
                        "Session", logger_instance=logger, context="Delete session failed"
                    )

            # Clear cache (best effort)
            await self._cache_ops.clear_cached_session(session_id)

            return ConversationErrorHandler.success_response()

        except Exception as e:
            # Add structured logging with context before error response
            logger.error(
                "Session deletion failed with detailed context",
                extra={
                    "session_id": str(session_id),
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            return ConversationErrorHandler.internal_error(
                "Failed to delete session",
                logger_instance=logger,
                context=f"Delete session error - session: {session_id}, user: {user_id}",
                exception=e,
                session_id=str(session_id),
                user_id=user_id,
            )
