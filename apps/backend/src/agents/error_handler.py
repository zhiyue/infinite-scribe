"""Error handling and retry logic for agent message processing."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from src.agents.errors import NonRetriableError
from src.agents.metrics import inc_dlt, inc_error
from src.core.logging.config import get_logger

if TYPE_CHECKING:
    from src.common.outbox import BaseOutboxManager


class ErrorHandler:
    """Handles error classification, retry logic, and dead letter topic routing."""

    def __init__(self, agent_name: str, max_retries: int, retry_backoff_ms: int, dlt_suffix: str):
        self.agent_name = agent_name
        self.max_retries = max_retries
        self.retry_backoff_ms = retry_backoff_ms
        self.dlt_suffix = dlt_suffix

        # Structured logger bound with agent context
        self.log: Any = get_logger("error").bind(agent=agent_name)

    def classify_error(self, error: Exception, message: dict[str, Any]) -> Literal["retriable", "non_retriable"]:
        """Classify error as retriable or non-retriable.

        Args:
            error: The exception that occurred
            message: The message being processed

        Returns:
            Error classification
        """
        if isinstance(error, NonRetriableError):
            return "non_retriable"
        return "retriable"

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay in seconds."""
        return (self.retry_backoff_ms / 1000.0) * (2 ** (attempt - 1))

    async def handle_retry(
        self, error: Exception, attempt: int, message_id: str | None, correlation_id: str | None
    ) -> bool:
        """Handle retry logic for recoverable errors.

        Args:
            error: The exception that occurred
            attempt: Current attempt number
            message_id: Message ID for logging
            correlation_id: Correlation ID for logging

        Returns:
            True if should retry, False if exhausted
        """
        if attempt <= self.max_retries:
            backoff = self.calculate_backoff(attempt)
            self.log.warning(
                "message_retry",
                attempt=attempt,
                max_retries=self.max_retries,
                backoff_s=backoff,
                message_id=message_id,
                correlation_id=correlation_id,
                exc_info=True,
            )
            await asyncio.sleep(backoff)
            return True
        return False

    async def send_to_dlt(
        self,
        msg: Any,
        payload: dict[str, Any],
        error: Exception,
        *,
        attempts: int,
        correlation_id: str | None,
        message_id: str | None,
        outbox_manager: BaseOutboxManager | None = None,
    ) -> None:
        """Send failed message to Dead Letter Topic via outbox.

        Args:
            msg: Original Kafka message
            payload: Message payload
            error: Exception that caused the failure
            attempts: Number of retry attempts
            correlation_id: Correlation ID for tracing
            message_id: Message ID
            outbox_manager: Outbox manager for reliable delivery (required)
        """
        dlt_topic = f"{msg.topic}{self.dlt_suffix}" if getattr(msg, "topic", None) else "deadletter"

        # 修复correlation_id覆盖逻辑：优先使用入参，如果没有才从payload获取
        effective_correlation_id = correlation_id or (
            payload.get("correlation_id") if isinstance(payload, dict) else None
        )

        body: dict[str, Any] = {
            "type": "error",
            "agent": self.agent_name,
            "original_topic": getattr(msg, "topic", None),
            "partition": getattr(msg, "partition", None),
            "offset": getattr(msg, "offset", None),
            "error": str(error),
            "payload": payload,
            # Envelope fields
            "id": str(uuid4()),
            "ts": datetime.now(UTC).isoformat(),
            "correlation_id": effective_correlation_id,
            "message_id": message_id,
            # Metrics and retry info
            "retries": attempts,
        }

        # Use correlation_id as key when available to keep ordering by correlation
        key_value = str(effective_correlation_id) if effective_correlation_id is not None else None

        # Send to DLT via outbox for reliable delivery
        if outbox_manager:
            try:
                outbox_id = await outbox_manager.enqueue_message(
                    topic=dlt_topic,
                    payload=body,
                    key=key_value,
                    correlation_id=effective_correlation_id,
                )
                self.log.warning(
                    "dlt_enqueued_to_outbox",
                    dlt_topic=dlt_topic,
                    correlation_id=effective_correlation_id,
                    message_id=message_id,
                    retries=attempts,
                    outbox_id=outbox_id,
                )
            except Exception as e:
                self.log.error("dlt_outbox_enqueue_failed", error=str(e), dlt_topic=dlt_topic)
                raise
        else:
            self.log.error(
                "no_outbox_for_dlt",
                message="Outbox manager not provided for DLT",
                dlt_topic=dlt_topic,
                message_id=message_id,
            )
            raise ValueError("Outbox manager required for DLT")

    def record_error_metrics(self, error_type: str) -> None:
        """Record error metrics."""
        with contextlib.suppress(Exception):
            inc_error(self.agent_name, error_type)
            inc_dlt(self.agent_name)
