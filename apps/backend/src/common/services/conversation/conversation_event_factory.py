"""
Event factory for conversation operations.

Handles domain event creation and management.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.events.config import build_event_type, get_aggregate_type
from src.models.event import DomainEvent

logger = logging.getLogger(__name__)


class ConversationEventFactory:
    """Factory for creating and managing conversation domain events."""

    async def get_or_create_domain_event(
        self,
        db: AsyncSession,
        session: Any,  # ConversationSession
        cmd: Any,  # CommandInbox
        command_type: str,
        payload: dict[str, Any] | None,
        *,
        user_id: int | None = None,
    ) -> Any:  # DomainEvent
        """Get existing or create new DomainEvent."""
        event_type = build_event_type(session.scope_type, "Command.Received")

        # Check for existing domain event
        dom_evt = await db.scalar(
            select(DomainEvent).where(and_(DomainEvent.correlation_id == cmd.id, DomainEvent.event_type == event_type))
        )

        if not dom_evt:
            # Enrich payload for downstream routing (SSE needs user_id/session_id)
            enriched_payload: dict[str, Any] = {
                "command_type": command_type,
                "payload": payload or {},
                "session_id": str(session.id),
            }
            if user_id is not None:
                enriched_payload["user_id"] = str(user_id)
            dom_evt = DomainEvent(
                event_type=event_type,
                aggregate_type=get_aggregate_type(session.scope_type),
                aggregate_id=str(session.id),
                payload=enriched_payload,
                correlation_id=cmd.id,
                # 初始命令投递的首个领域事件：将命令ID同时作为 causation_id 建立因果链起点
                causation_id=cmd.id,
                event_metadata={"source": "api-gateway", **({"user_id": str(user_id)} if user_id is not None else {})},
            )
            db.add(dom_evt)
            await db.flush()  # Get event_id

        return dom_evt
