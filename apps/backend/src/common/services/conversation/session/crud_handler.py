"""
Session CRUD operations handler for conversation services.

Coordinates CRUD operations by delegating to specialized handlers.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.conversation import ConversationSessionRepository
from src.common.services.conversation.cache import ConversationCacheManager
from src.common.services.conversation.conversation_access_control import ConversationAccessControl
from src.common.services.conversation.conversation_serializers import ConversationSerializer
from src.common.services.conversation.session.access_operations import (
    ConversationSessionAccessOperations,
)
from src.common.services.conversation.session.cache_operations import (
    ConversationSessionCacheOperations,
)
from src.common.services.conversation.session.create_handler import (
    ConversationSessionCreateHandler,
)
from src.common.services.conversation.session.read_handler import ConversationSessionReadHandler
from src.common.services.conversation.session.update_delete_handler import (
    ConversationSessionUpdateDeleteHandler,
)
from src.schemas.novel.dialogue import ScopeType, SessionStatus


class ConversationSessionCrudHandler:
    """Handler for conversation session CRUD operations."""

    def __init__(
        self,
        cache: ConversationCacheManager,
        access_control: ConversationAccessControl,
        serializer: ConversationSerializer,
        repository_factory: Callable[[AsyncSession], ConversationSessionRepository],
    ) -> None:
        self.cache = cache
        self.access_control = access_control
        self.serializer = serializer
        self._repo_factory = repository_factory

        # Initialize helper operations
        cache_ops = ConversationSessionCacheOperations(cache, serializer)
        access_ops = ConversationSessionAccessOperations(access_control)

        # Initialize specialized handlers
        self._create_handler = ConversationSessionCreateHandler(cache_ops, access_ops, repository_factory)
        self._read_handler = ConversationSessionReadHandler(cache_ops, access_ops, serializer, repository_factory)
        self._update_delete_handler = ConversationSessionUpdateDeleteHandler(cache_ops, access_ops, repository_factory)

    async def create_session(
        self,
        db: AsyncSession,
        user_id: int,
        scope_type: ScopeType | str,
        scope_id: str,
    ) -> dict[str, Any]:
        """
        Create a new conversation session.

        Args:
            db: Database session
            user_id: User ID for ownership
            scope_type: Type of scope (supports all ScopeType values)
            scope_id: ID of the scope

        Returns:
            Dict with success status and session or error details
        """
        return await self._create_handler.create_session(
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
        return await self._read_handler.get_session(db=db, user_id=user_id, session_id=session_id)

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
        Update a conversation session with optimistic concurrency control.

        Args:
            db: Database session
            user_id: User ID for ownership verification
            session_id: Session ID to update
            status: New status (optional)
            expected_version: Expected version for optimistic locking (optional)

        Returns:
            Dict with success status and updated session or error details
        """
        return await self._update_delete_handler.update_session(
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
        return await self._update_delete_handler.delete_session(db=db, user_id=user_id, session_id=session_id)

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
        return await self._read_handler.list_sessions(
            db=db,
            user_id=user_id,
            scope_type=scope_type,
            scope_id=scope_id,
            status=status,
            limit=limit,
            offset=offset,
        )
