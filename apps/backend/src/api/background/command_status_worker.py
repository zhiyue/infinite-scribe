"""
Background worker to consume command status events alongside the API gateway.

This worker subscribes to Kafka topics carrying command status events and
delegates updates to CommandStatusConsumer, which applies DB updates and
publishes follow-up domain events (via the injected event publisher, if any).

Notes:
- Topics default to 'command.status.events' and can be overridden via the
  environment variable COMMAND_STATUS_TOPICS (comma-separated).
- Messages are expected to be JSON dicts. The worker accepts either the
  canonical command event shape:
    {"event_type": "Command.Started|Completed|Failed|...",
     "correlation_id": "<command_uuid>",
     "payload": {...}}
  or the generic Envelope shape produced by some agents:
    {"id": "...", "type": "...", "data": {...}, "correlation_id": "..."}
  In the latter case, the worker normalizes it into the canonical shape.
"""

from __future__ import annotations

import asyncio
from typing import Any

from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.core.config import settings
from src.core.kafka.client import KafkaClientManager
from src.core.logging import get_logger
from src.services.command.command_status_consumer import CommandStatusConsumer
from src.services.command.event_publisher import DomainEventPublisher, NoOpEventPublisher

logger = get_logger(__name__)


def _topics_from_settings() -> list[str]:
    try:
        topics = list(settings.command_status.topics or [])
        return topics or ["command.status.events"]
    except Exception:
        return ["command.status.events"]


class CommandStatusWorker:
    """API-embedded Kafka consumer for command status events."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        shutdown_event: asyncio.Event,
        event_publisher: DomainEventPublisher | None = None,
        topics: list[str] | None = None,
        batch_size: int | None = None,
        poll_timeout_ms: int | None = None,
    ) -> None:
        self._shutdown_event = shutdown_event
        cs = settings.command_status
        self._batch_size = max(1, int(batch_size if batch_size is not None else cs.batch_size))
        self._poll_timeout_ms = max(100, int(poll_timeout_ms if poll_timeout_ms is not None else cs.poll_timeout_ms))
        self._topics = topics or _topics_from_settings()

        # Core services
        self._session_factory = session_factory
        self._status_consumer = CommandStatusConsumer(session_factory, event_publisher or NoOpEventPublisher())

        # Kafka client manager
        group_suffix = settings.command_status.group_id_suffix or "command-status"
        self._kafka = KafkaClientManager(
            client_id="api-command-status",
            consume_topics=self._topics,
            group_id=f"{settings.kafka_group_id_prefix}-{group_suffix}-group",
            logger_context={"service": "api-gateway", "component": "cmd-status-worker"},
        )
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        try:
            logger.info("Starting CommandStatusWorker", topics=self._topics)
            self._consumer = await self._kafka.create_consumer()
            # Subscribe after create_consumer per KafkaClientManager contract
            self._kafka.subscribe_consumer()
            self._task = asyncio.create_task(self._run_loop())
        except Exception as e:  # pragma: no cover - defensive
            logger.error("Failed to start CommandStatusWorker", error=str(e), exc_info=True)
            # Best-effort cleanup
            try:
                await self._kafka.stop_consumer()
            except Exception:
                pass

    async def stop(self) -> None:
        logger.info("Stopping CommandStatusWorker")
        # Signal and wait for task
        if self._task:
            # Task will exit on shutdown_event being set by lifespan
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except Exception:
                self._task.cancel()
            finally:
                self._task = None

        # Close consumer
        try:
            await self._kafka.stop_consumer()
        except Exception:  # pragma: no cover - defensive
            logger.warning("CommandStatusWorker consumer stop failed", exc_info=True)

    async def _run_loop(self) -> None:
        assert self._consumer is not None
        consumer = self._consumer
        while not self._shutdown_event.is_set():
            try:
                # Poll batch
                records = await consumer.getmany(timeout_ms=self._poll_timeout_ms, max_records=self._batch_size)

                # Flatten messages
                batch: list[dict[str, Any]] = []
                for tp, messages in records.items():
                    for msg in messages:
                        val = msg.value if isinstance(msg.value, dict) else {}
                        norm = self._normalize_event(val)
                        if norm:
                            batch.append(norm)

                if batch:
                    result = await self._status_consumer.consume_command_events(batch, context={"source": "api-gateway"})
                    # Only commit if all events in batch were processed successfully
                    if result.get("batch_failed", 0) == 0:
                        await consumer.commit()
                        logger.debug(f"Committed offset after successful batch processing: {result.get('batch_success', 0)} events")
                    else:
                        logger.warning(
                            f"Skipping offset commit due to failed events: {result.get('batch_failed', 0)} failed, "
                            f"{result.get('batch_success', 0)} succeeded. Events will be reprocessed."
                        )

            except asyncio.CancelledError:  # pragma: no cover - cooperative shutdown
                raise
            except Exception as e:
                logger.error("CommandStatusWorker loop error", error=str(e), exc_info=True)
                await asyncio.sleep(1.0)

        logger.info("CommandStatusWorker loop exited")

    @staticmethod
    def _normalize_event(value: dict[str, Any]) -> dict[str, Any] | None:
        """Normalize input value to CommandStatusConsumer expected shape.

        Accepted shapes:
        - Canonical: {event_type, correlation_id|command_id, payload}
        - Envelope:  {id, type, data, correlation_id?}
        """
        if not isinstance(value, dict):
            return None

        if "event_type" in value:
            return value

        # Envelope -> canonical
        if {"type", "data"}.issubset(value.keys()):
            return {
                "event_type": value.get("type"),
                "correlation_id": value.get("correlation_id") or (value.get("data") or {}).get("command_id"),
                "payload": value.get("data") or {},
            }

        return None
