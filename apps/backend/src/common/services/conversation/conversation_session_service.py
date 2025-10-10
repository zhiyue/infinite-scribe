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
from src.common.services.conversation.cache import ConversationCacheManager
from src.common.services.conversation.conversation_access_control import ConversationAccessControl
from src.common.services.conversation.conversation_serializers import ConversationSerializer
from src.common.services.conversation.session import ConversationSessionCrudHandler
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

        # Initialize handlers with the configured dependencies
        self._crud_handler = ConversationSessionCrudHandler(
            cache=self.cache,
            access_control=self.access_control,
            serializer=self.serializer,
            repository_factory=self._repo_factory,
        )

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
        return await self._crud_handler.create_session(
            db=db,
            user_id=user_id,
            scope_type=scope_type,
            scope_id=scope_id,
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
        return await self._crud_handler.get_session(db=db, user_id=user_id, session_id=session_id)

    async def update_session(
        self,
        db: AsyncSession,
        user_id: int,
        session_id: UUID,
        *,
        status: SessionStatus | None = None,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        """
        Update a conversation session with optimistic concurrency control (Genesis 解耦后的精简版本).

        Args:
            db: Database session
            user_id: User ID for ownership verification
            session_id: Session ID to update
            status: New status (optional)
            expected_version: Expected version for optimistic locking (optional)

        Returns:
            Dict with success status and updated session or error details
        """
        return await self._crud_handler.update_session(
            db=db,
            user_id=user_id,
            session_id=session_id,
            status=status,
            expected_version=expected_version,
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
        return await self._crud_handler.delete_session(db=db, user_id=user_id, session_id=session_id)

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
        return await self._crud_handler.list_sessions(
            db=db,
            user_id=user_id,
            scope_type=scope_type,
            scope_id=scope_id,
            status=status,
            limit=limit,
            offset=offset,
        )
