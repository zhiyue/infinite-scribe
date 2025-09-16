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
            # Handle scope_type as string or enum
            if isinstance(scope_type, str):
                scope_type_str = scope_type
                try:
                    scope_type_enum = ScopeType(scope_type)
                except ValueError:
                    logger.warning(
                        "Invalid scope type provided for session creation",
                        extra={
                            "provided_scope_type": scope_type,
                            "valid_scope_types": [e.value for e in ScopeType],
                            "user_id": user_id,
                            "scope_id": scope_id,
                            "operation": "create_session_validation",
                        },
                    )
                    return ConversationErrorHandler.validation_error(
                        f"Invalid scope type: {scope_type}",
                        logger_instance=logger,
                        context=f"Create session validation - invalid scope type: {scope_type}",
                    )
            else:
                scope_type_enum = scope_type
                scope_type_str = scope_type.value

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

            if scope_type_enum != ScopeType.GENESIS:
                logger.warning(
                    "Unsupported scope type for session creation",
                    extra={
                        "scope_type": scope_type_str,
                        "supported_scope_types": [ScopeType.GENESIS.value],
                        "user_id": user_id,
                        "scope_id": scope_id,
                        "operation": "create_session_validation",
                    },
                )
                return ConversationErrorHandler.validation_error(
                    "Only GENESIS scope is supported",
                    logger_instance=logger,
                    context=f"Create session validation - unsupported scope: {scope_type_str}",
                )

            # Verify access to the scope
            logger.debug(f"Verifying access to scope: {scope_type_str}, {scope_id}")
            novel_result = await self.access_control.get_novel_for_scope(db, user_id, scope_type_str, scope_id)
            logger.debug(f"Access control result: {novel_result}")
            if not novel_result["success"]:
                logger.warning(f"Access denied: {novel_result}")
                return novel_result

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

            # Serialize ORM object to dict at service boundary
            logger.debug("Serializing session")
            serialized_session = self.serializer.serialize_session(session)
            logger.debug(f"Serialized session keys: {serialized_session.keys()}")

            # Cache write-through (best effort) - already serialized
            try:
                logger.debug("Attempting to cache session")
                await self.cache.cache_session(str(session.id), serialized_session)
                logger.debug(f"Cached session {session.id}")
            except Exception as cache_error:
                # Cache failure should not affect main business flow
                logger.warning(
                    f"Failed to cache session {session.id}: {cache_error}", extra={"session_id": str(session.id)}
                )

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
                    "Session", logger_instance=logger, context="Update session not found"
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
                return ConversationErrorHandler.success_response(
                    {
                        "session": session,
                        "serialized_session": serialized_session,
                    }
                )

            # Update with optimistic concurrency control using transactional support
            async with transactional(db):
                updated_session = await repository.update(
                    session_id=session_id,
                    status=status,
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
                    "update_stage": stage,
                    "has_state_update": state is not None,
                    "expected_version": expected_version,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            return ConversationErrorHandler.internal_error(
                "Failed to update session",
                logger_instance=logger,
                context=f"Update session error - session: {session_id}, user: {user_id}, status: {status}, stage: {stage}",
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
                        "Session", logger_instance=logger, context="Delete session failed"
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
            scope_type: Scope type (e.g., "GENESIS")
            scope_id: Scope identifier (e.g., novel ID)
            status: Optional status filter
            limit: Maximum number of sessions to return
            offset: Offset for pagination

        Returns:
            Dict with success status and sessions list or error details
        """
        try:
            # Verify user has access to this scope
            access_result = await self.access_control.verify_scope_access(db, user_id, scope_type, scope_id)
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
            serialized_sessions = [self.serializer.serialize_session(session) for session in sessions]

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
