"""
Atomic operations for conversation commands.

Handles transactional operations for command and round creation.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.conversation.conversation_command_factory import ConversationCommandFactory
from src.common.services.conversation.conversation_event_factory import ConversationEventFactory
from src.common.services.conversation.conversation_outbox_manager import ConversationOutboxManager
from src.common.services.conversation.conversation_round_creation_service import ConversationRoundCreationService
from src.db.sql.session import transactional

logger = logging.getLogger(__name__)


class ConversationAtomicOperations:
    """Handler for atomic conversation command operations."""

    def __init__(
        self,
        command_factory: ConversationCommandFactory | None = None,
        event_factory: ConversationEventFactory | None = None,
        outbox_manager: ConversationOutboxManager | None = None,
        round_creation_service: ConversationRoundCreationService | None = None,
    ) -> None:
        self.command_factory = command_factory or ConversationCommandFactory()
        self.event_factory = event_factory or ConversationEventFactory()
        self.outbox_manager = outbox_manager or ConversationOutboxManager()
        self.round_creation_service = round_creation_service or ConversationRoundCreationService()

    async def enqueue_command_atomic(
        self,
        db: AsyncSession,
        user_id: int,
        session: Any,  # ConversationSession
        command_type: str,
        payload: dict[str, Any] | None,
        idempotency_key: str | None,
    ) -> dict[str, Any] | None:  # {"command": CommandInbox, "round": ConversationRound} | None
        """
        Atomically enqueue command with domain events, outbox pattern, and conversation round.

        Implements the complete outbox pattern:
        - CommandInbox + DomainEvents + EventOutbox (command creation)
        - ConversationRound + DomainEvents + EventOutbox (round creation)

        Args:
            db: Database session
            user_id: User ID for round creation
            session: ConversationSession instance
            command_type: Type of command
            payload: Command payload
            idempotency_key: Idempotency key

        Returns:
            Dict with CommandInbox and ConversationRound instances or None if failed
        """
        try:
            async with transactional(db):
                # 1. Create CommandInbox with events and outbox
                cmd = await self.command_factory.get_or_create_command(
                    db, session.id, command_type, payload, idempotency_key
                )
                dom_evt = await self.event_factory.get_or_create_domain_event(
                    db, session, cmd, command_type, payload, user_id=user_id
                )
                await self.outbox_manager.ensure_outbox_entry(db, session, dom_evt, cmd)

                # 2. Create ConversationRound for the command (in the same transaction)
                round_obj = await self.create_round_for_command_atomic(
                    db, session, cmd, command_type, payload, idempotency_key
                )

                return {"command": cmd, "round": round_obj}

        except Exception as e:
            logger.error(f"Atomic command+round creation error: {e}")
            return None

    async def create_round_for_command_atomic(
        self,
        db: AsyncSession,
        session: Any,  # ConversationSession
        command: Any,  # CommandInbox
        command_type: str,
        payload: dict[str, Any] | None,
        idempotency_key: str | None,
    ) -> Any:  # ConversationRound
        """
        Create conversation round for command within the same transaction.

        This reuses the core logic from ConversationRoundCreationService but
        operates within the existing transaction instead of creating a new one.

        Args:
            db: Database session (already in transaction)
            session: ConversationSession instance
            command: CommandInbox instance
            command_type: Type of command
            payload: Command payload
            idempotency_key: Idempotency key

        Returns:
            Created ConversationRound instance
        """
        from src.common.repositories.conversation import SqlAlchemyConversationRoundRepository
        from src.schemas.novel.dialogue import DialogueRole

        # Prepare input data representing the command
        input_data = {
            "command_type": command_type,
            "command_id": str(command.id),
            "payload": payload or {},
            "source": "command_api",
        }

        # Parse correlation UUID for events
        corr_uuid = None
        if idempotency_key:
            try:
                corr_uuid = UUID(str(idempotency_key))
            except Exception:
                corr_uuid = None

        # Create repository instance
        repository = SqlAlchemyConversationRoundRepository(db)

        # Reuse the round creation service's core logic but within our transaction
        round_obj = await self.round_creation_service._create_new_round(
            db=db,
            session=session,
            repository=repository,
            role=DialogueRole.USER,  # Command is user-initiated
            input_data=input_data,
            model=None,  # Will be set when agent responds
            correlation_id=idempotency_key,  # Link to command
            corr_uuid=corr_uuid,
            parent_round_path=None,  # Top-level round
        )

        return round_obj
