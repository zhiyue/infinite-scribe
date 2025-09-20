"""
Command service for conversation operations.

Handles command enqueueing with outbox pattern, domain events, and idempotency.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.conversation.conversation_access_control import ConversationAccessControl
from src.common.services.conversation.conversation_atomic_operations import ConversationAtomicOperations
from src.common.services.conversation.conversation_command_factory import ConversationCommandFactory
from src.common.services.conversation.conversation_error_handler import ConversationErrorHandler
from src.common.services.conversation.conversation_event_handler import ConversationEventHandler
from src.common.services.conversation.conversation_serializers import ConversationSerializer
from src.models.workflow import CommandInbox
from src.schemas.enums import CommandStatus

logger = logging.getLogger(__name__)


class ConversationCommandService:
    """Service for conversation command operations."""

    def __init__(
        self,
        access_control: ConversationAccessControl | None = None,
        event_handler: ConversationEventHandler | None = None,
        serializer: ConversationSerializer | None = None,
        command_factory: ConversationCommandFactory | None = None,
        atomic_operations: ConversationAtomicOperations | None = None,
    ) -> None:
        self.access_control = access_control or ConversationAccessControl()
        self.event_handler = event_handler or ConversationEventHandler()
        self.serializer = serializer or ConversationSerializer()
        self.command_factory = command_factory or ConversationCommandFactory()
        self.atomic_operations = atomic_operations or ConversationAtomicOperations()

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
            existing_cmd = await self.command_factory.check_existing_command(
                db, session_id, command_type, idempotency_key
            )
            if existing_cmd:
                # Ensure events exist for existing command (non-atomic is OK here)
                # Enrich with user_id for SSE routing convention
                await self.event_handler.ensure_command_events(db, session, existing_cmd, user_id=user_id)
                command = existing_cmd
            else:
                # 3. Use atomic method to create command AND round with full transaction safety
                result = await self.atomic_operations.enqueue_command_atomic(
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
                command_data: dict[str, Any] = {
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
                    "status": pending_cmd.status.value
                    if hasattr(pending_cmd.status, "value")
                    else str(pending_cmd.status),
                    "submitted_at": (
                        pending_cmd.created_at.isoformat() if getattr(pending_cmd, "created_at", None) else None
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
