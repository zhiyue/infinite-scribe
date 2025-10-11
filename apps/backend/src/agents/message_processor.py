"""Message processing pipeline for agent services."""

import asyncio
from collections.abc import Callable
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Literal, cast

from aiokafka.errors import KafkaError, UnknownTopicOrPartitionError

from src.agents.agent_metrics import AgentMetrics
from src.agents.error_handler import ErrorHandler
from src.agents.message import decode_message, encode_message
from src.agents.metrics import record_latency
from src.core.logging.config import get_logger

if TYPE_CHECKING:
    from src.common.outbox import BaseOutboxManager


class MessageProcessor:
    """Handles the message processing pipeline with retry and error handling."""

    def __init__(
        self,
        agent_name: str,
        error_handler: ErrorHandler,
        produce_topics: list[str] | None = None,
        classify_error: Callable[[Exception, dict[str, Any]], Literal["retriable", "non_retriable"]] | None = None,
    ):
        self.agent_name = agent_name
        self.error_handler = error_handler
        self.produce_topics = produce_topics or []
        self.classify_error_func = classify_error or error_handler.classify_error

        # Structured logger bound with agent context
        self.log: Any = get_logger("processor").bind(agent=agent_name)

    def decode_message_with_context(self, msg: Any) -> tuple[dict[str, Any], dict[str, Any], str | None, str | None]:
        """Decode message and build context metadata.

        Returns:
            Tuple of (decoded_message, context, correlation_id, message_id)
        """
        # Decode message (Envelope or raw dict)
        message_value = cast(dict[str, Any] | None, getattr(msg, "value", None))
        raw_value: dict[str, Any] = message_value if isinstance(message_value, dict) else {}
        safe_message, meta = decode_message(raw_value)
        correlation_id = cast(str | None, meta.get("correlation_id"))
        message_id = cast(str | None, meta.get("message_id") or meta.get("id"))

        # Build context with topic/headers metadata
        headers_list = getattr(msg, "headers", None)
        headers_dict: dict[str, Any] | None = None
        if headers_list:
            try:
                headers_dict = {
                    k: (v.decode("utf-8") if isinstance(v, bytes | bytearray) else v) for k, v in headers_list
                }
            except Exception:
                headers_dict = None

        context = {
            "topic": getattr(msg, "topic", None),
            "partition": getattr(msg, "partition", None),
            "offset": getattr(msg, "offset", None),
            "timestamp": getattr(msg, "timestamp", None),
            "key": getattr(msg, "key", None),
            "headers": headers_dict or headers_list,
            "meta": meta,
        }

        return safe_message, context, correlation_id, message_id

    async def process_message_with_retry(
        self,
        msg: Any,
        safe_message: dict[str, Any],
        context: dict[str, Any],
        correlation_id: str | None,
        message_id: str | None,
        process_func: Callable[[dict[str, Any], dict[str, Any] | None], Any],
        producer_func: Callable[[], Any] | None,
        agent_metrics: AgentMetrics,
        outbox_manager: "BaseOutboxManager | None" = None,
    ) -> dict[str, Any]:
        """Process message with retry logic and error handling.

        Args:
            msg: Original Kafka message
            safe_message: Decoded message content
            context: Message context
            correlation_id: Correlation ID for tracing
            message_id: Message ID
            process_func: Function to process the message
            producer_func: (Deprecated) Function to get Kafka producer. Use outbox_manager instead.
            agent_metrics: Agent metrics instance
            outbox_manager: (Recommended) Outbox manager for reliable message delivery

        Returns:
            dict with keys:
            - handled: bool - True if message was processed (successfully or sent to DLT)
            - success: bool - True only if message was processed successfully
        """
        attempt = 0
        start = asyncio.get_event_loop().time()

        while True:
            try:
                result: dict[str, Any] | None = await process_func(safe_message, context)
                if result:
                    await self._send_result(
                        result,
                        retries=attempt,
                        correlation_id=correlation_id,
                        message_id=message_id,
                        producer_func=producer_func,
                        outbox_manager=outbox_manager,
                    )

                # Record processing latency only - processed count由BaseAgent处理
                end = asyncio.get_event_loop().time()
                latency_ms = (end - start) * 1000.0
                agent_metrics.record_processing_latency(latency_ms)

                # Record latency metric (optional)
                with suppress(Exception):
                    record_latency(self.agent_name, end - start)

                return {"handled": True, "success": True}

            except asyncio.CancelledError:
                raise
            except Exception as e:
                # 使用传入的错误分类回调而不是error_handler.classify_error
                classification = self.classify_error_func(e, safe_message)

                if classification == "non_retriable":
                    await self._handle_non_retriable_error(
                        msg, safe_message, e, attempt, correlation_id, message_id, producer_func, agent_metrics
                    )
                    return {"handled": True, "success": False}
                else:
                    attempt += 1
                    if await self.error_handler.handle_retry(e, attempt, message_id, correlation_id):
                        agent_metrics.increment_retries()
                        continue
                    else:
                        # Exhausted retries
                        await self._handle_exhausted_retries(
                            msg, safe_message, e, attempt, correlation_id, message_id, producer_func, agent_metrics
                        )
                        return {"handled": True, "success": False}

    async def _handle_non_retriable_error(
        self,
        msg: Any,
        safe_message: dict[str, Any],
        error: Exception,
        attempts: int,
        correlation_id: str | None,
        message_id: str | None,
        producer_func: Callable[[], Any],
        agent_metrics: Any,  # AgentMetrics对象
    ) -> None:
        """Handle non-retriable errors by sending directly to DLT."""
        try:
            producer = await producer_func()
            await self.error_handler.send_to_dlt(
                producer,
                msg,
                safe_message,
                error,
                attempts=attempts,
                correlation_id=correlation_id,
                message_id=message_id,
            )
        except Exception:
            self.log.error("dlt_send_failed", exc_info=True)

        # 使用AgentMetrics方法更新指标
        agent_metrics.increment_failed()
        agent_metrics.increment_dlt()
        agent_metrics.record_error(str(error))
        self.error_handler.record_error_metrics("non_retriable")

    async def _handle_exhausted_retries(
        self,
        msg: Any,
        safe_message: dict[str, Any],
        error: Exception,
        attempts: int,
        correlation_id: str | None,
        message_id: str | None,
        producer_func: Callable[[], Any],
        agent_metrics: Any,  # AgentMetrics对象
    ) -> None:
        """Handle exhausted retries by sending to DLT."""
        try:
            producer = await producer_func()
            await self.error_handler.send_to_dlt(
                producer,
                msg,
                safe_message,
                error,
                attempts=attempts,
                correlation_id=correlation_id,
                message_id=message_id,
            )
        except Exception:
            self.log.error("dlt_send_failed", exc_info=True)

        # 使用AgentMetrics方法更新指标
        agent_metrics.increment_failed()
        agent_metrics.increment_dlt()
        agent_metrics.record_error(str(error))
        self.error_handler.record_error_metrics("exhausted")

    async def _send_result(
        self,
        result: dict[str, Any],
        *,
        retries: int,
        correlation_id: str | None,
        message_id: str | None,
        producer_func: Callable[[], Any] | None,
        outbox_manager: "BaseOutboxManager | None" = None,
    ) -> None:
        """Send processing result to output topic.

        Prefers outbox_manager for reliable delivery. Falls back to producer_func
        for backward compatibility.

        Args:
            result: Processing result with optional _topic and _key fields
            retries: Number of retry attempts
            correlation_id: Correlation ID for tracing
            message_id: Message ID
            producer_func: (Deprecated) Producer function for backward compatibility
            outbox_manager: (Recommended) Outbox manager for reliable delivery
        """
        # Get target topic from result or use default
        topic = result.pop("_topic", None)
        if not topic and self.produce_topics:
            topic = self.produce_topics[0]

        if not topic:
            self.log.warning("no_topic_for_result", message_id=message_id)
            return

        # Optional partitioning key support
        # Try explicit _key first, then fallback to common fields
        key_value = result.pop("_key", None)
        if not key_value:
            # Intelligent fallback: use session_id or user_id for partitioning
            key_value = result.get("session_id") or result.get("user_id")
            if key_value:
                self.log.debug(
                    "using_fallback_partition_key",
                    key=key_value,
                    source="session_id" if "session_id" in result else "user_id",
                )

        # Attach retries info if not provided by business logic
        result.setdefault("retries", retries)

        # Encode envelope
        encoded = encode_message(self.agent_name, result, correlation_id=correlation_id, retries=retries)

        # Prefer outbox for reliable delivery
        if outbox_manager:
            try:
                outbox_id = await outbox_manager.enqueue_message(
                    topic=topic,
                    payload=encoded,
                    key=str(key_value) if key_value is not None else None,
                    correlation_id=correlation_id,
                )
                self.log.debug(
                    "result_enqueued_to_outbox",
                    topic=topic,
                    key=key_value,
                    retries=retries,
                    correlation_id=correlation_id,
                    message_id=message_id,
                    outbox_id=outbox_id,
                )
            except Exception as e:
                self.log.error("outbox_enqueue_failed", error=str(e), topic=topic)
                raise
        elif producer_func:
            # Fallback to direct producer (deprecated path)
            producer = await producer_func()
            try:
                key_bytes = str(key_value).encode("utf-8") if key_value is not None else None

                # Try send with simple topic auto-creation retry like OutboxRelay
                max_retries = 3
                for attempt in range(max_retries + 1):
                    try:
                        await producer.send_and_wait(topic, encoded, key=key_bytes)
                        break
                    except UnknownTopicOrPartitionError:
                        if attempt < max_retries:
                            # Trigger metadata refresh to auto-create topics when enabled
                            with suppress(Exception):
                                await producer.client.fetch_all_metadata()
                            await asyncio.sleep(1.0)
                            continue
                        else:
                            raise
                self.log.debug(
                    "result_sent_via_producer",
                    topic=topic,
                    key=key_value,
                    retries=retries,
                    correlation_id=correlation_id,
                    message_id=message_id,
                )
            except KafkaError as e:
                self.log.error("result_send_failed", error=str(e))
                # Re-raise to trigger upper-level retry/DLT logic
                raise
        else:
            self.log.error(
                "no_send_method_available",
                message="Neither outbox_manager nor producer_func provided",
                topic=topic,
                message_id=message_id,
            )
            raise ValueError("No send method available for result")
