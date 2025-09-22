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

    async def store_event(self, event: dict[str, Any]) -> bool:
        """Store event in outbox for EventBridgePublisher compatibility.
        
        Args:
            event: Event data from EventBridgePublisher
            
        Returns:
            True if successfully stored
        """
        try:
            # Extract event data for enqueue_envelope
            agent = event.get("source", "api-gateway")
            topic = event.get("metadata", {}).get("topic", "genesis.session.events")
            key = str(event.get("aggregate_id", ""))
            correlation_id = event.get("metadata", {}).get("correlation_id")
            
            # Convert event to result format expected by enqueue_envelope
            result = {
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "aggregate_type": event.get("aggregate_type", "Session"),
                "aggregate_id": event.get("aggregate_id"),
                "payload": event.get("payload", {}),
                "metadata": event.get("metadata", {}),
            }
            
            await self.enqueue_envelope(
                agent=agent,
                topic=topic,
                key=key,
                result=result,
                correlation_id=correlation_id,
            )
            return True
            
        except Exception as e:
            from src.core.logging import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to store event in outbox: {e}", exc_info=True)
            return False
