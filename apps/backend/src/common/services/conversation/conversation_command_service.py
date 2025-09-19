"""
Command service for conversation operations.

Handles command enqueueing with outbox pattern, domain events, and idempotency.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.events.config import build_event_type, get_aggregate_type, get_domain_topic
from src.common.services.conversation.conversation_access_control import ConversationAccessControl
from src.common.services.conversation.conversation_error_handler import ConversationErrorHandler
from src.common.services.conversation.conversation_event_handler import ConversationEventHandler
from src.common.services.conversation.conversation_round_creation_service import ConversationRoundCreationService
from src.common.services.conversation.conversation_serializers import ConversationSerializer
from src.db.sql.session import transactional
from src.models.event import DomainEvent
from src.models.workflow import CommandInbox, EventOutbox
from src.schemas.enums import CommandStatus, OutboxStatus

logger = logging.getLogger(__name__)


class ConversationCommandService:
    """Service for conversation command operations."""

    def __init__(
        self,
        access_control: ConversationAccessControl | None = None,
        event_handler: ConversationEventHandler | None = None,
        serializer: ConversationSerializer | None = None,
        round_creation_service: ConversationRoundCreationService | None = None,
    ) -> None:
        self.access_control = access_control or ConversationAccessControl()
        self.event_handler = event_handler or ConversationEventHandler()
        self.serializer = serializer or ConversationSerializer()
        self.round_creation_service = round_creation_service or ConversationRoundCreationService()

    async def enqueue_command(
        self,
        db: AsyncSession,
        user_id: int,
        session_id: UUID,
        *,
        command_type: str,
        payload: dict[str, Any] | None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Enqueue a command with outbox pattern for async processing.

        Uses atomic transaction to ensure data consistency across:
        - CommandInbox creation
        - DomainEvent creation
        - EventOutbox entry

        Args:
            db: Database session
            user_id: User ID for ownership verification
            session_id: Session ID for the command
            command_type: Type of command to enqueue
            payload: Command payload data
            idempotency_key: Optional idempotency key for duplicate prevention

        Returns:
            Dict with success status and command or error details
        """
        try:
            # 1. Verify session access
            access_result = await self.access_control.verify_session_access(db, user_id, session_id)
            if not access_result["success"]:
                return access_result
            session = access_result["session"]

            # 2. Check for existing commands
            existing_cmd = await self._check_existing_command(db, session_id, command_type, idempotency_key)
            if existing_cmd:
                # Ensure events exist for existing command (non-atomic is OK here)
                await self.event_handler.ensure_command_events(db, session, existing_cmd)
                command = existing_cmd
            else:
                # 3. Use atomic method to create command AND round with full transaction safety
                result = await self._enqueue_command_atomic(
                    db, user_id, session, command_type, payload, idempotency_key
                )

                if result:
                    command = result["command"]
                    round_obj = result["round"]
                    logger.info(
                        f"Atomically created command {command.id} and round {round_obj.round_path}",
                        extra={
                            "command_id": str(command.id),
                            "round_path": round_obj.round_path,
                            "session_id": str(session_id),
                            "command_type": command_type,
                        },
                    )
                else:
                    command = None

            if not command:
                return ConversationErrorHandler.internal_error(
                    "Failed to create command atomically",
                    logger_instance=logger,
                    context="Atomic command creation failed",
                    correlation_id=idempotency_key,
                    session_id=str(session.id),
                )

            # 4. Serialize command (optional, not part of transaction)
            serialized_command = None
            try:
                serialized_command = self.serializer.serialize_command(command)
            except Exception as serialize_error:
                logger.warning(
                    f"Failed to serialize command {getattr(command, 'id', None)}: {serialize_error}",
                    extra={
                        "session_id": str(session.id),
                        "idempotency_key": idempotency_key,
                    },
                )

            # 5. Build response payload
            response_payload: dict[str, Any] = {"command": command}
            if serialized_command is not None:
                response_payload["serialized_command"] = serialized_command

            return ConversationErrorHandler.success_response(response_payload)

        except Exception as e:
            return ConversationErrorHandler.internal_error(
                "Failed to enqueue command",
                logger_instance=logger,
                context="Command enqueue error",
                exception=e,
                correlation_id=idempotency_key,
                session_id=str(session_id) if session_id else None,
                user_id=user_id,
            )

    async def _check_existing_command(
        self,
        db: AsyncSession,
        session_id: UUID,
        command_type: str,
        idempotency_key: str | None,
    ) -> Any:  # CommandInbox | None
        """
        Check for existing commands by idempotency key or any pending command in session.

        Args:
            db: Database session
            session_id: Session ID
            command_type: Command type (used for logging only)
            idempotency_key: Optional idempotency key

        Returns:
            Existing CommandInbox or None
        """
        try:
            # 1. Check by idempotency_key if provided (highest priority)
            if idempotency_key:
                existing_cmd = await db.scalar(
                    select(CommandInbox).where(CommandInbox.idempotency_key == idempotency_key)
                )
                if existing_cmd:
                    return existing_cmd

            # 2. Check for any existing pending command in session (global validation)
            from src.schemas.enums import CommandStatus

            existing_cmd = await db.scalar(
                select(CommandInbox).where(
                    CommandInbox.session_id == session_id,
                    CommandInbox.status.in_([CommandStatus.RECEIVED, CommandStatus.PROCESSING]),
                )
            )
            return existing_cmd

        except Exception as e:
            logger.error(
                f"Failed to check existing command: {e}",
                extra={
                    "session_id": str(session_id),
                    "command_type": command_type,
                    "idempotency_key": idempotency_key,
                },
            )
            # Return None to proceed with new command creation
            return None

    async def _enqueue_command_atomic(
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
                cmd = await self._get_or_create_command(db, session.id, command_type, payload, idempotency_key)
                dom_evt = await self._get_or_create_domain_event(db, session, cmd, command_type, payload)
                await self._ensure_outbox_entry(db, session, dom_evt, cmd)

                # 2. Create ConversationRound for the command (in the same transaction)
                round_obj = await self._create_round_for_command_atomic(
                    db, session, cmd, command_type, payload, idempotency_key
                )

                return {"command": cmd, "round": round_obj}

        except Exception as e:
            logger.error(f"Atomic command+round creation error: {e}")
            return None

    async def _create_round_for_command_atomic(
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

    async def _get_or_create_command(
        self,
        db: AsyncSession,
        session_id: UUID,
        command_type: str,
        payload: dict[str, Any] | None,
        idempotency_key: str | None,
    ) -> Any:  # CommandInbox
        """Get existing or create new CommandInbox entry."""
        cmd = None

        # Check for existing command by idempotency key
        if idempotency_key:
            cmd = await db.scalar(select(CommandInbox).where(CommandInbox.idempotency_key == idempotency_key))

        if not cmd:
            cmd = CommandInbox(
                session_id=session_id,
                command_type=command_type,
                idempotency_key=idempotency_key or f"cmd-{uuid4()}",
                payload=payload or {},
                status=CommandStatus.RECEIVED,
            )
            db.add(cmd)
            await db.flush()  # Get cmd.id

        return cmd

    async def _get_or_create_domain_event(
        self,
        db: AsyncSession,
        session: Any,  # ConversationSession
        cmd: Any,  # CommandInbox
        command_type: str,
        payload: dict[str, Any] | None,
    ) -> Any:  # DomainEvent
        """Get existing or create new DomainEvent."""
        event_type = build_event_type(session.scope_type, "Command.Received")

        # Check for existing domain event
        dom_evt = await db.scalar(
            select(DomainEvent).where(and_(DomainEvent.correlation_id == cmd.id, DomainEvent.event_type == event_type))
        )

        if not dom_evt:
            dom_evt = DomainEvent(
                event_type=event_type,
                aggregate_type=get_aggregate_type(session.scope_type),
                aggregate_id=str(session.id),
                payload={"command_type": command_type, "payload": payload or {}},
                correlation_id=cmd.id,
                causation_id=None,
                event_metadata={"source": "api-gateway"},
            )
            db.add(dom_evt)
            await db.flush()  # Get event_id

        return dom_evt

    async def _ensure_outbox_entry(
        self,
        db: AsyncSession,
        session: Any,  # ConversationSession
        dom_evt: Any,  # DomainEvent
        cmd: Any,  # CommandInbox
    ) -> None:
        """Ensure EventOutbox entry exists for the domain event."""
        # Check if outbox entry already exists
        existing_out = await db.scalar(select(EventOutbox).where(EventOutbox.id == dom_evt.event_id))

        if not existing_out:
            await self._create_outbox_entry(db, session, dom_evt, cmd)

    async def _create_outbox_entry(
        self,
        db: AsyncSession,
        session: Any,  # ConversationSession
        dom_evt: Any,  # DomainEvent
        cmd: Any,  # CommandInbox
    ) -> None:
        """Create new EventOutbox entry."""
        out = EventOutbox(
            id=dom_evt.event_id,
            topic=get_domain_topic(session.scope_type),
            key=str(session.id),
            partition_key=str(session.id),
            payload={
                "event_id": str(dom_evt.event_id),
                "event_type": dom_evt.event_type,
                "aggregate_type": dom_evt.aggregate_type,
                "aggregate_id": dom_evt.aggregate_id,
                "payload": dom_evt.payload or {},
                "metadata": dom_evt.event_metadata or {},
                "created_at": getattr(dom_evt.created_at, "isoformat", lambda: str(dom_evt.created_at))()
                if getattr(dom_evt, "created_at", None)
                else None,
            },
            headers={
                "event_type": dom_evt.event_type,
                "version": 1,
                "correlation_id": str(cmd.id),
            },
            status=OutboxStatus.PENDING,
        )
        db.add(out)

    async def get_pending_command(
        self,
        db: AsyncSession,
        user_id: int,
        session_id: UUID,
    ) -> dict[str, Any]:
        """
        Get the current pending command for a session.

        Args:
            db: Database session
            user_id: User ID for ownership verification
            session_id: Session ID to check

        Returns:
            Dict with success status and command details or None
        """
        try:
            # 1. Verify session access
            access_result = await self.access_control.verify_session_access(db, user_id, session_id)
            if not access_result["success"]:
                return access_result

            # 2. Query for pending commands
            from src.schemas.enums import CommandStatus

            pending_cmd = await db.scalar(
                select(CommandInbox)
                .where(
                    CommandInbox.session_id == session_id,
                    CommandInbox.status.in_([CommandStatus.RECEIVED, CommandStatus.PROCESSING]),
                )
                .order_by(CommandInbox.created_at.desc())  # Get the most recent
            )

            if not pending_cmd:
                # No pending command found
                command_data = {
                    "command_id": None,
                    "command_type": None,
                    "status": None,
                    "submitted_at": None,
                }
            else:
                # Build response data
                command_data = {
                    "command_id": pending_cmd.id,
                    "command_type": pending_cmd.command_type,
                    "status": pending_cmd.status.value if hasattr(pending_cmd.status, "value") else str(pending_cmd.status),
                    "submitted_at": (
                        pending_cmd.created_at.isoformat()
                        if getattr(pending_cmd, "created_at", None)
                        else None
                    ),
                }

            return ConversationErrorHandler.success_response(command_data)

        except Exception as e:
            return ConversationErrorHandler.internal_error(
                "Failed to get pending command",
                logger_instance=logger,
                context="Pending command query error",
                exception=e,
                session_id=str(session_id),
                user_id=user_id,
            )
