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
            # Extract topic and partition key info
            topic = event.get("metadata", {}).get("topic", "genesis.session.events")
            aggregate_id = event.get("aggregate_id")

            # Fix aggregate_id handling - don't convert None to string
            key = None
            if aggregate_id is not None:
                key = str(aggregate_id)

            correlation_id = event.get("correlation_id") or event.get("metadata", {}).get("correlation_id")

            # Create EventBridge-compatible flat structure directly
            # Instead of using encode_message which creates nested Envelope structure
            eventbridge_payload = {
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "aggregate_id": aggregate_id,
                "correlation_id": correlation_id,
                "payload": event.get("payload", {}),
                # Preserve additional fields that might be needed
                "aggregate_type": event.get("aggregate_type", "Session"),
                "metadata": event.get("metadata", {}),
                "timestamp": event.get("timestamp"),
            }

            # Store directly to outbox without using enqueue_envelope
            # since that would wrap it in Envelope structure
            async with create_sql_session() as db:
                out = EventOutbox(
                    topic=topic,
                    key=key,
                    partition_key=key,
                    payload=eventbridge_payload,
                    headers={
                        "event_type": event.get("event_type"),
                        "correlation_id": correlation_id,
                        "agent": event.get("source", "api-gateway"),
                    },
                    status=OutboxStatus.PENDING,
                )
                db.add(out)
                await db.flush()

            return True

        except Exception as e:
            from src.core.logging import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to store event in outbox: {e}", exc_info=True)
            return False
