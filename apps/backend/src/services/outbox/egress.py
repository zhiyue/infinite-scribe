"""Unified Outbox Egress for agents (DB -> Kafka via Relay)

Provides a simple async interface for agents to enqueue messages to the
`event_outbox` table. The OutboxRelay service will publish them to Kafka.

Usage:
    egress = OutboxEgress()
    await egress.enqueue_envelope(
        agent="writer",
        topic="genesis.writer.events",
        key="chapter-1",
        result={"type": "chapter_written", "chapter_id": 1, "content": "..."},
        correlation_id="...",
    )
"""

from __future__ import annotations

from typing import Any

from src.agents.message import encode_message
from src.db.sql.session import create_sql_session
from src.models.workflow import EventOutbox
from src.schemas.enums import OutboxStatus


class OutboxEgress:
    """Helper for enqueuing messages to EventOutbox with Envelope encoding."""

    async def enqueue_envelope(
        self,
        *,
        agent: str,
        topic: str,
        key: str | None,
        result: dict[str, Any],
        correlation_id: str | None = None,
        retries: int = 0,
        headers_extra: dict[str, Any] | None = None,
    ) -> str:
        """Encode `result` as Envelope and write to EventOutbox.

        Returns: outbox row id as string
        """
        envelope = encode_message(agent, result, correlation_id=correlation_id, retries=retries)
        async with create_sql_session() as db:
            out = EventOutbox(
                topic=topic,
                key=str(key) if key is not None else None,
                partition_key=str(key) if key is not None else None,
                payload=envelope,
                headers={
                    "type": envelope.get("type"),
                    "version": envelope.get("version"),
                    "correlation_id": correlation_id,
                    "agent": agent,
                    **(headers_extra or {}),
                },
                status=OutboxStatus.PENDING,
            )
            db.add(out)
            await db.flush()
            return str(out.id)

