"""
Outbox manager for conversation operations.

Handles outbox pattern implementation for reliable event publishing.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.events.config import get_domain_topic
from src.common.events.envelope import DomainEventBuilder
from src.models.workflow import EventOutbox
from src.schemas.enums import OutboxStatus

logger = logging.getLogger(__name__)


class ConversationOutboxManager:
    """Manager for conversation outbox pattern operations."""

    async def ensure_outbox_entry(
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
            await self.create_outbox_entry(db, session, dom_evt, cmd)

    async def create_outbox_entry(
        self,
        db: AsyncSession,
        session: Any,  # ConversationSession
        dom_evt: Any,  # DomainEvent
        cmd: Any,  # CommandInbox
    ) -> None:
        """Create new EventOutbox entry."""
        payload_envelope = DomainEventBuilder.from_domain_event(dom_evt).build().model_dump(exclude_none=True)

        out = EventOutbox(
            id=dom_evt.event_id,
            topic=get_domain_topic(session.scope_type),
            key=str(session.id),
            partition_key=str(session.id),
            payload=payload_envelope,
            headers={
                "event_type": payload_envelope["system"]["event_type"],
                "version": 1,
                "correlation_id": str(cmd.id),
            },
            status=OutboxStatus.PENDING,
        )
        db.add(out)
