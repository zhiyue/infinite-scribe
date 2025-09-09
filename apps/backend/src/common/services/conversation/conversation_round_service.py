"""
Round service for conversation operations.

Facade service that delegates to specialized query and creation services for better separation of concerns.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.conversation import ConversationRoundRepository, SqlAlchemyConversationRoundRepository
from src.common.services.conversation.conversation_access_control import ConversationAccessControl
from src.common.services.conversation.conversation_cache import ConversationCacheManager
from src.common.services.conversation.conversation_event_handler import ConversationEventHandler
from src.common.services.conversation.conversation_round_creation_service import ConversationRoundCreationService
from src.common.services.conversation.conversation_round_query_service import ConversationRoundQueryService
from src.common.services.conversation.conversation_serializers import ConversationSerializer
from src.models.conversation import ConversationRound, ConversationSession
from src.schemas.novel.dialogue import DialogueRole

logger = logging.getLogger(__name__)


class ConversationRoundService:
    """Facade service for conversation round operations."""

    def __init__(
        self,
        cache: ConversationCacheManager | None = None,
        access_control: ConversationAccessControl | None = None,
        serializer: ConversationSerializer | None = None,
        event_handler: ConversationEventHandler | None = None,
        repository: ConversationRoundRepository | None = None,
        query_service: ConversationRoundQueryService | None = None,
        creation_service: ConversationRoundCreationService | None = None,
    ) -> None:
        """
        Initialize ConversationRoundService with dependency injection support.

        Args:
            cache: Cache manager instance
            access_control: Access control service instance
            serializer: Serializer service instance
            event_handler: Event handler service instance
            repository: Repository for data access
            query_service: Pre-configured query service (overrides other params)
            creation_service: Pre-configured creation service (overrides other params)
        """
        # Store repository for potential direct use
        self.repository = repository
        
        # Allow direct injection of services for maximum flexibility
        if query_service is not None:
            self.query_service = query_service
        else:
            # Create query service with injected dependencies
            cache_manager = cache or ConversationCacheManager()
            access_ctrl = access_control or ConversationAccessControl()
            serializer_inst = serializer or ConversationSerializer()
            self.query_service = ConversationRoundQueryService(
                cache_manager, access_ctrl, serializer_inst, repository
            )

        if creation_service is not None:
            self.creation_service = creation_service
        else:
            # Create creation service with injected dependencies
            cache_manager = cache or ConversationCacheManager()
            access_ctrl = access_control or ConversationAccessControl()
            serializer_inst = serializer or ConversationSerializer()
            event_handler_inst = event_handler or ConversationEventHandler()
            self.creation_service = ConversationRoundCreationService(
                cache_manager, access_ctrl, serializer_inst, event_handler_inst, repository
            )

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
        return await self.query_service.list_rounds(
            db, user_id, session_id, after=after, limit=limit, order=order, role=role
        )

    async def get_round(self, db: AsyncSession, user_id: int, session_id: UUID, round_path: str) -> dict[str, Any]:
        """Get a specific conversation round."""
        return await self.query_service.get_round(db, user_id, session_id, round_path)

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
        parent_round_path: str | None = None,
    ) -> dict[str, Any]:
        """Create a new conversation round with domain events and optional branching support."""
        return await self.creation_service.create_round(
            db,
            user_id,
            session_id,
            role=role,
            input_data=input_data,
            model=model,
            correlation_id=correlation_id,
            parent_round_path=parent_round_path,
        )

    # ------------------------------
    # Back-compat utility functions
    # ------------------------------
    @staticmethod
    def _compute_next_round_path(existing_count: int) -> str:
        try:
            n = int(existing_count or 0)
        except Exception:
            n = 0
        return str(max(0, n) + 1)

    @staticmethod
    def _parse_correlation_uuid(correlation_id: str | None):
        from uuid import UUID

        if not correlation_id:
            return None
        try:
            return UUID(str(correlation_id))
        except Exception:
            return None
