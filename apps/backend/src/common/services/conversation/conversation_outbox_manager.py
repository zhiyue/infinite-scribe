"""
Outbox manager for conversation operations.

Handles outbox pattern implementation for reliable event publishing.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.events.config import get_domain_topic
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
        # 扁平化 EventOutbox 载荷，避免 payload.payload 双重结构
        flat_payload = {
            "event_id": str(dom_evt.event_id),
            "event_type": dom_evt.event_type,
            "aggregate_type": dom_evt.aggregate_type,
            "aggregate_id": dom_evt.aggregate_id,
            "metadata": dom_evt.event_metadata or {},
        }
        if dom_evt.payload:
            try:
                flat_payload.update(dom_evt.payload)
            except Exception:
                flat_payload["payload"] = dom_evt.payload
        if getattr(dom_evt, "created_at", None):
            with contextlib.suppress(Exception):
                flat_payload["created_at"] = dom_evt.created_at.isoformat()  # type: ignore[attr-defined]

        out = EventOutbox(
            id=dom_evt.event_id,
            topic=get_domain_topic(session.scope_type),
            key=str(session.id),
            partition_key=str(session.id),
            payload=flat_payload,
            headers={
                "event_type": dom_evt.event_type,
                "version": 1,
                "correlation_id": str(cmd.id),
            },
            status=OutboxStatus.PENDING,
        )
        db.add(out)
