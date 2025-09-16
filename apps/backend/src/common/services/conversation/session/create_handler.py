"""
Session creation handler for conversation services.

Handles session creation with validation, access control, and caching.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

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
from src.schemas.novel.dialogue import ScopeType, SessionStatus

logger = logging.getLogger(__name__)


class ConversationSessionCreateHandler:
    """Handler for conversation session creation operations."""

    def __init__(
        self,
        cache_ops: ConversationSessionCacheOperations,
        access_ops: ConversationSessionAccessOperations,
        repository_factory: Callable[[AsyncSession], ConversationSessionRepository],
    ) -> None:
        self._cache_ops = cache_ops
        self._access_ops = access_ops
        self._repo_factory = repository_factory

    async def create_session(
        self,
        db: AsyncSession,
        user_id: int,
        scope_type: ScopeType | str,
        scope_id: str,
        stage: str | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new conversation session.

        Args:
            db: Database session
            user_id: User ID for ownership
            scope_type: Type of scope (ScopeType enum or string, currently only GENESIS supported)
            scope_id: ID of the scope (novel ID for GENESIS)
            stage: Optional stage name
            initial_state: Optional initial state data

        Returns:
            Dict with success status and session or error details
        """
        try:
            # Validate and normalize scope type
            error_response, scope_type_enum, scope_type_str = (
                ConversationSessionValidator.validate_and_normalize_scope_type(scope_type, user_id, scope_id)
            )
            if error_response:
                return error_response

            # Type assertion: After error check, these values cannot be None
            assert scope_type_enum is not None
            assert scope_type_str is not None

            logger.info(
                "Starting session creation with detailed context",
                extra={
                    "user_id": user_id,
                    "scope_type": scope_type_str,
                    "scope_id": scope_id,
                    "stage": stage,
                    "has_initial_state": initial_state is not None,
                    "operation": "create_session",
                },
            )

            # Validate supported scope type
            error_response = ConversationSessionValidator.validate_supported_scope_type(
                scope_type_enum, scope_type_str, user_id, scope_id
            )
            if error_response:
                return error_response

            # Verify access to the scope
            access_result = await self._access_ops.verify_scope_access_for_creation(
                db, user_id, scope_type_str, scope_id
            )
            if not access_result["success"]:
                return access_result

            # Get repository from factory
            logger.debug("Creating repository instance")
            repository = self._repo_factory(db)

            # Check for existing active session
            logger.debug(f"Checking for existing active sessions for scope: {scope_type_str}, {scope_id}")
            existing = await repository.find_active_by_scope(scope_type_str, str(scope_id))
            if existing:
                logger.warning(
                    "Active session conflict detected",
                    extra={
                        "existing_session_id": str(existing.id),
                        "scope_type": scope_type_str,
                        "scope_id": scope_id,
                        "user_id": user_id,
                        "existing_session_status": existing.status,
                        "operation": "create_session_conflict",
                    },
                )
                return ConversationErrorHandler.conflict_error(
                    "An active session already exists for this novel",
                    logger_instance=logger,
                    context=f"Create session conflict - existing session: {existing.id} for scope: {scope_type_str}:{scope_id}",
                )

            # Create new session with transactional support
            logger.info("Creating new session")
            async with transactional(db):
                session = await repository.create(
                    scope_type=scope_type_str,
                    scope_id=str(scope_id),
                    status=SessionStatus.ACTIVE.value,
                    stage=stage,
                    state=initial_state or {},
                    version=1,
                )
                logger.info(
                    "Session created successfully with context",
                    extra={
                        "session_id": str(session.id),
                        "scope_type": scope_type_str,
                        "scope_id": scope_id,
                        "user_id": user_id,
                        "stage": stage,
                        "version": 1,
                        "operation": "create_session_success",
                    },
                )

            # Serialize and cache session
            serialized_session = self._cache_ops.serialize_session_with_logging(session, "create_session")
            await self._cache_ops.cache_session(session.id, serialized_session)

            logger.debug("Session creation successful")
            return ConversationErrorHandler.success_response(
                {
                    "session": session,
                    "serialized_session": serialized_session,
                }
            )

        except Exception as e:
            # Add structured logging with context before error response
            logger.error(
                "Session creation failed with detailed context",
                extra={
                    "scope_type": scope_type_str if "scope_type_str" in locals() else str(scope_type),
                    "scope_id": scope_id,
                    "user_id": user_id,
                    "stage": stage,
                    "has_initial_state": initial_state is not None,
                    "session_id": str(session.id) if "session" in locals() else None,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            return ConversationErrorHandler.internal_error(
                "Failed to create session",
                logger_instance=logger,
                context=f"Create session error - scope: {scope_type_str if 'scope_type_str' in locals() else str(scope_type)}:{scope_id}, user: {user_id}, stage: {stage}",
                exception=e,
                session_id=str(session.id) if "session" in locals() else None,
                user_id=user_id,
            )
