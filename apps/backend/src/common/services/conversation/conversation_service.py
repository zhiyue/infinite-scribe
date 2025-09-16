"""
Conversation service (persistent) for Genesis conversation flows.

Main facade for conversation operations. Delegates to specialized services:
- ConversationSessionService: Session CRUD operations
- ConversationRoundService: Round CRUD operations
- ConversationCommandService: Command operations

Maintains backward compatibility with existing API while providing better separation of concerns.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.conversation.cache import ConversationCacheManager
from src.common.services.conversation.conversation_command_service import ConversationCommandService
from src.common.services.conversation.conversation_event_handler import ConversationEventHandler
from src.common.services.conversation.conversation_round_service import ConversationRoundService
from src.common.services.conversation.conversation_session_service import ConversationSessionService
from src.schemas.novel.dialogue import DialogueRole, ScopeType, SessionStatus


class ConversationService:
    """
    Main facade for conversation operations.

    Delegates to specialized services while maintaining backward compatibility.
    """

    def __init__(
        self,
        cache: ConversationCacheManager | None = None,
        session_service: ConversationSessionService | None = None,
        round_service: ConversationRoundService | None = None,
        command_service: ConversationCommandService | None = None,
    ) -> None:
        self.cache = cache or ConversationCacheManager()
        self.session_service = session_service or ConversationSessionService(self.cache)
        self.round_service = round_service or ConversationRoundService(self.cache)
        # Provide event handler to command service for outbox/event creation
        self.command_service = command_service or ConversationCommandService(event_handler=ConversationEventHandler())

    # ---------- Session Operations ----------

    async def create_session(
        self,
        db: AsyncSession,
        user_id: int,
        scope_type: ScopeType,
        scope_id: str,
        stage: str | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new conversation session."""
        return await self.session_service.create_session(db, user_id, scope_type, scope_id, stage, initial_state)

    async def get_session(self, db: AsyncSession, user_id: int, session_id: UUID) -> dict[str, Any]:
        """Get a conversation session by ID."""
        return await self.session_service.get_session(db, user_id, session_id)

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
        """Update a conversation session with optimistic concurrency control."""
        return await self.session_service.update_session(
            db, user_id, session_id, status=status, stage=stage, state=state, expected_version=expected_version
        )

    async def delete_session(self, db: AsyncSession, user_id: int, session_id: UUID) -> dict[str, Any]:
        """Delete a conversation session."""
        return await self.session_service.delete_session(db, user_id, session_id)

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
        """List conversation sessions for a given scope."""
        return await self.session_service.list_sessions(db, user_id, scope_type, scope_id, status, limit, offset)

    # ---------- Round Operations ----------

    async def list_rounds(
        self,
        db: AsyncSession,
        user_id: int,
        session_id: UUID,
        *,
        after: str | None = None,
        limit: int = 50,
        order: str = "asc",
        role: DialogueRole | None = None,
    ) -> dict[str, Any]:
        """List conversation rounds for a session."""
        return await self.round_service.list_rounds(
            db, user_id, session_id, after=after, limit=limit, order=order, role=role
        )

    async def create_round(
        self,
        db: AsyncSession,
        user_id: int,
        session_id: UUID,
        *,
        role: DialogueRole,
        input_data: dict[str, Any],
        model: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new conversation round with domain events."""
        return await self.round_service.create_round(
            db, user_id, session_id, role=role, input_data=input_data, model=model, correlation_id=correlation_id
        )

    async def get_round(self, db: AsyncSession, user_id: int, session_id: UUID, round_path: str) -> dict[str, Any]:
        """Get a specific conversation round."""
        return await self.round_service.get_round(db, user_id, session_id, round_path)

    # ---------- Command Operations ----------

    async def enqueue_command(
        self,
        db: AsyncSession,
        user_id: int,
        session_id: UUID,
        *,
        command_type: str,
        payload: dict[str, Any] | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        """Enqueue a command with outbox pattern for async processing."""
        return await self.command_service.enqueue_command(
            db, user_id, session_id, command_type=command_type, payload=payload, idempotency_key=idempotency_key
        )


conversation_service = ConversationService()

__all__ = ["conversation_service", "ConversationService"]
