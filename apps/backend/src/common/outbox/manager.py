"""Generic Outbox Manager for reliable message delivery across all agents.

This module provides a base implementation of the Outbox pattern, ensuring that
all agent messages are persisted to the EventOutbox table before being asynchronously
sent to Kafka by the OutboxRelay service.

Key Benefits:
- Transactional message persistence
- Automatic retry through OutboxRelay
- Message delivery guarantees
- Decoupling from Kafka availability
"""

from __future__ import annotations

import logging
from typing import Any

from src.db.sql.session import create_sql_session
from src.models.workflow import EventOutbox
from src.schemas.enums import OutboxStatus

logger = logging.getLogger(__name__)


class BaseOutboxManager:
    """Generic outbox manager for reliable message delivery.

    This class provides the core functionality for enqueuing messages to the
    EventOutbox table. All agents should use this for message delivery instead
    of directly calling Kafka producers.

    The actual sending to Kafka is handled asynchronously by the OutboxRelay service.
    """

    def __init__(self, agent_name: str):
        """Initialize the outbox manager.

        Args:
            agent_name: Name of the agent using this manager (for logging and tracing)
        """
        self.agent_name = agent_name
        self.log = logger

    async def enqueue_message(
        self,
        topic: str,
        payload: dict[str, Any],
        key: str | None = None,
        correlation_id: str | None = None,
        headers: dict[str, Any] | None = None,
    ) -> str:
        """Enqueue a message to the EventOutbox for async delivery to Kafka.

        This is the primary method for sending messages. It persists the message
        to the outbox table, and the OutboxRelay service will pick it up and send
        it to Kafka asynchronously.

        Args:
            topic: Kafka topic to send the message to
            payload: Message payload (will be stored as-is)
            key: Optional partition key for Kafka
            correlation_id: Optional correlation ID for request tracing
            headers: Optional additional headers for the message

        Returns:
            The UUID of the created outbox entry (as string)

        Raises:
            Exception: If database persistence fails

        Example:
            ```python
            outbox_mgr = BaseOutboxManager("my-agent")
            await outbox_mgr.enqueue_message(
                topic="agent.responses",
                payload={"result": "success", "data": {...}},
                key="session-123",
                correlation_id="req-456"
            )
            ```
        """
        if not topic:
            self.log.warning(
                "message_enqueue_skipped",
                extra={
                    "reason": "missing_topic",
                    "agent": self.agent_name,
                    "payload_keys": list(payload.keys()) if payload else [],
                },
            )
            raise ValueError("Topic is required for message enqueuing")

        # Build headers
        message_headers = headers or {}
        if "agent" not in message_headers:
            message_headers["agent"] = self.agent_name
        if correlation_id and "correlation_id" not in message_headers:
            message_headers["correlation_id"] = correlation_id

        # Create outbox entry
        outbox_id = await self._create_outbox_entry(
            topic=topic,
            payload=payload,
            key=key,
            correlation_id=correlation_id,
            headers=message_headers,
        )

        self.log.info(
            "message_enqueued_to_outbox",
            extra={
                "agent": self.agent_name,
                "outbox_id": outbox_id,
                "topic": topic,
                "key": key,
                "correlation_id": correlation_id,
            },
        )

        return outbox_id

    async def _create_outbox_entry(
        self,
        topic: str,
        payload: dict[str, Any],
        key: str | None,
        correlation_id: str | None,
        headers: dict[str, Any],
    ) -> str:
        """Create an entry in the EventOutbox table.

        Args:
            topic: Kafka topic
            payload: Message payload
            key: Partition key
            correlation_id: Correlation ID
            headers: Message headers

        Returns:
            The UUID of the created entry (as string)

        Raises:
            Exception: If database operation fails
        """
        async with create_sql_session() as db:
            # Create outbox entry with PENDING status
            outbox_entry = EventOutbox(
                topic=topic,
                key=str(key) if key is not None else None,
                partition_key=str(key) if key is not None else None,
                payload=payload,
                headers=headers,
                status=OutboxStatus.PENDING,
            )
            db.add(outbox_entry)

            # Flush to get the generated ID
            await db.flush()

            outbox_id = str(outbox_entry.id)

            self.log.debug(
                "outbox_entry_created",
                extra={
                    "agent": self.agent_name,
                    "outbox_id": outbox_id,
                    "topic": topic,
                    "key": key,
                    "payload_size": len(str(payload)),
                },
            )

            return outbox_id

    async def enqueue_batch(
        self,
        messages: list[dict[str, Any]],
        correlation_id: str | None = None,
    ) -> list[str]:
        """Enqueue multiple messages in a single transaction.

        Args:
            messages: List of message dicts, each containing 'topic', 'payload',
                     and optionally 'key' and 'headers'
            correlation_id: Optional correlation ID applied to all messages

        Returns:
            List of outbox entry UUIDs (as strings)

        Example:
            ```python
            messages = [
                {"topic": "t1", "payload": {"data": 1}, "key": "k1"},
                {"topic": "t2", "payload": {"data": 2}, "key": "k2"},
            ]
            ids = await outbox_mgr.enqueue_batch(messages, correlation_id="req-123")
            ```
        """
        if not messages:
            return []

        outbox_ids = []
        for msg in messages:
            outbox_id = await self.enqueue_message(
                topic=msg["topic"],
                payload=msg["payload"],
                key=msg.get("key"),
                correlation_id=correlation_id or msg.get("correlation_id"),
                headers=msg.get("headers"),
            )
            outbox_ids.append(outbox_id)

        self.log.info(
            "batch_messages_enqueued",
            extra={
                "agent": self.agent_name,
                "count": len(messages),
                "correlation_id": correlation_id,
            },
        )

        return outbox_ids
