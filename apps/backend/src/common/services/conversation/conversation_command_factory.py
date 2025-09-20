"""
Command factory for conversation operations.

Handles command creation, validation, and idempotency checking.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.workflow import CommandInbox
from src.schemas.enums import CommandStatus

logger = logging.getLogger(__name__)


class ConversationCommandFactory:
    """Factory for creating and validating conversation commands."""

    async def check_existing_command(
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

    async def get_or_create_command(
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
