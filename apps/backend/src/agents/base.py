"""Base Agent class for all agent services."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Literal

from src.agents.agent_metrics import AgentMetrics
from src.agents.error_handler import ErrorHandler
from src.agents.message_processor import MessageProcessor
from src.agents.offset_manager import OffsetManager
from src.core.config import settings
from src.core.kafka.client import KafkaClientManager
from src.core.logging.config import get_logger


class BaseAgent(ABC):
    """Base class for all agent services with Kafka integration."""

    def __init__(self, name: str, consume_topics: list[str], produce_topics: list[str] | None = None):
        self.name = name
        self.config = settings
        self.consume_topics = consume_topics
        self.produce_topics = produce_topics or []

        # Runtime state
        self.is_running = False
        self._stopping = False
        self._stop_lock = asyncio.Lock()
        self.ready = False

        # Initialize component modules
        self.kafka_client = KafkaClientManager(
            client_id=name, consume_topics=consume_topics, produce_topics=produce_topics, logger_context={"agent": name}
        )
        self.offset_manager = OffsetManager(
            name, self.config.agent_commit_batch_size, self.config.agent_commit_interval_ms
        )
        self.error_handler = ErrorHandler(
            name, self.config.agent_max_retries, self.config.agent_retry_backoff_ms, self.config.agent_dlt_suffix
        )
        # 传入classify_error回调以保证子类重载生效
        self.message_processor = MessageProcessor(
            name, self.error_handler, produce_topics, classify_error=self.classify_error
        )
        self.metrics = AgentMetrics(name)

        # Configuration validation
        self._validate_config()

        # Structured logger bound with agent context
        self.log: Any = get_logger("agent").bind(agent=self.name)

    def _validate_config(self) -> None:
        if self.config.agent_max_retries < 0:
            raise ValueError("agent_max_retries must be >= 0")
        if self.config.agent_retry_backoff_ms < 0:
            raise ValueError("agent_retry_backoff_ms must be >= 0")
        if self.config.agent_commit_batch_size <= 0:
            raise ValueError("agent_commit_batch_size must be > 0")
        if self.config.agent_commit_interval_ms < 0:
            raise ValueError("agent_commit_interval_ms must be >= 0")

    @abstractmethod
    async def process_message(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Process received message.

        Args:
            message: Parsed message content
            context: Message context with metadata

        Returns:
            Response message to send, or None if no response needed
        """
        pass

    def classify_error(self, error: Exception, message: dict[str, Any]) -> Literal["retriable", "non_retriable"]:
        """Classify error as retriable or non-retriable.

        Args:
            error: The exception that occurred
            message: The message being processed

        Returns:
            Error classification
        """
        return self.error_handler.classify_error(error, message)

    # Compatibility properties for test and launcher backward compatibility
    @property
    def consumer(self):
        """Backward compatibility property for accessing Kafka consumer."""
        return self.kafka_client.consumer

    @property
    def producer(self):
        """Backward compatibility property for accessing Kafka producer."""
        return self.kafka_client.producer

    # Test-friendly thin wrapper methods for kafka client operations
    async def _create_consumer(self) -> Any:
        """Test-friendly wrapper for creating consumer. Delegates to KafkaClientManager."""
        return await self.kafka_client.create_consumer()

    async def _create_producer(self) -> Any:
        """Test-friendly wrapper for creating producer. Delegates to KafkaClientManager."""
        return await self.kafka_client.create_producer()

    async def _get_or_create_producer(self) -> Any:
        """Test-friendly wrapper for getting or creating producer. Delegates to KafkaClientManager."""
        return await self.kafka_client.get_or_create_producer()

    # Test-friendly configuration properties (for backward compatibility with tests)
    @property
    def max_retries(self) -> int:
        """Get max retries configuration."""
        return self.error_handler.max_retries

    @max_retries.setter
    def max_retries(self, value: int) -> None:
        """Set max retries configuration."""
        self.error_handler.max_retries = int(value)

    @property
    def retry_backoff_ms(self) -> int:
        """Get retry backoff configuration."""
        return self.error_handler.retry_backoff_ms

    @retry_backoff_ms.setter
    def retry_backoff_ms(self, value: int) -> None:
        """Set retry backoff configuration."""
        self.error_handler.retry_backoff_ms = int(value)

    @property
    def commit_batch_size(self) -> int:
        """Get commit batch size configuration."""
        return self.offset_manager.commit_batch_size

    @commit_batch_size.setter
    def commit_batch_size(self, value: int) -> None:
        """Set commit batch size configuration."""
        self.offset_manager.commit_batch_size = int(value)

    @property
    def commit_interval_ms(self) -> int:
        """Get commit interval configuration."""
        return self.offset_manager.commit_interval_ms

    @commit_interval_ms.setter
    def commit_interval_ms(self, value: int) -> None:
        """Set commit interval configuration."""
        self.offset_manager.commit_interval_ms = int(value)

    async def _consume_messages(self):
        """Main message consumption loop."""
        try:
            consumer = self.kafka_client.consumer
            if consumer is None:
                self.log.error("consumer_not_initialized")
                return

            async for msg in consumer:
                if not self.is_running:
                    break

                try:
                    # Decode message and build context
                    safe_message, context, correlation_id, message_id = (
                        self.message_processor.decode_message_with_context(msg)
                    )

                    # Log received message
                    self.log.debug(
                        "message_received",
                        topic=msg.topic,
                        partition=msg.partition,
                        offset=msg.offset,
                        message_id=message_id,
                        correlation_id=correlation_id,
                    )

                    # Update consumed counter
                    self.metrics.increment_consumed()

                    # Process message with retry logic - 使用薄封装方法
                    result = await self.message_processor.process_message_with_retry(
                        msg=msg,
                        safe_message=safe_message,
                        context=context,
                        correlation_id=correlation_id,
                        message_id=message_id,
                        process_func=self.process_message,
                        producer_func=self._get_or_create_producer,  # 使用薄封装方法
                        agent_metrics=self.metrics,
                    )

                    if result["handled"]:
                        # Record offset and maybe commit for any handled message
                        await self.offset_manager.record_offset_and_maybe_commit(consumer, msg)

                        # Only increment processed count and clear error for truly successful processing
                        if result["success"]:
                            self.metrics.increment_processed()
                            self.metrics.clear_error()

                except Exception as e:
                    self.log.error("message_loop_error", error=str(e), exc_info=True)
                    self.metrics.record_error(str(e))

        except Exception as e:
            self.log.error("consume_loop_error", error=str(e), exc_info=True)
            self.metrics.record_error(str(e))

    # Delegate offset management methods to offset_manager
    async def _commit_offset_for_message(self, msg: Any) -> None:
        """Commit offset for specific message immediately (not recommended for frequent use)."""
        if self.kafka_client.consumer:
            await self.offset_manager.commit_offset_for_message(self.kafka_client.consumer, msg)

    async def _record_offset_and_maybe_commit(self, msg: Any, force: bool = False) -> None:
        """Record offset and evaluate whether to perform batch commit."""
        if self.kafka_client.consumer:
            await self.offset_manager.record_offset_and_maybe_commit(self.kafka_client.consumer, msg, force)

    # DLT handling is now delegated to error_handler via message_processor

    async def start(self):
        """Start agent service."""
        self.log.info("agent_starting")
        self.is_running = True
        self._stopping = False

        try:
            # If no consume topics configured, enter idle loop to avoid task immediate exit
            if not self.consume_topics:
                self.log.info("agent_idle_mode")
                # If need to send messages, create producer
                if self.produce_topics:
                    await self._create_producer()  # 使用薄封装方法

                await self.on_start()
                self.ready = True

                # Idle loop, wait for stop signal
                while self.is_running:
                    await asyncio.sleep(1)
            else:
                # Create Kafka consumer
                await self._create_consumer()  # 使用薄封装方法

                # If need to send messages, create producer
                if self.produce_topics:
                    await self._create_producer()  # 使用薄封装方法

                # Call subclass start hook
                await self.on_start()
                self.ready = True

                # Start consuming messages
                await self._consume_messages()

        except Exception as e:
            self.log.error("agent_start_failed", error=str(e), exc_info=True)
            self.metrics.record_error(str(e))
            raise
        finally:
            try:
                await self.stop()
            except Exception:
                # Swallow exceptions during cleanup to not mask original errors
                self.log.warning("agent_stop_during_finally_failed", exc_info=True)

    async def stop(self):
        """Stop agent service."""
        async with self._stop_lock:
            if self._stopping:
                self.log.debug("stop_already_in_progress", reason="duplicate_call")
                return
            self._stopping = True
        self.log.info("agent_stopping")
        self.is_running = False

        # Call subclass stop hook
        try:
            await self.on_stop()
        except Exception:
            self.log.warning("agent_on_stop_failed", exc_info=True)

        # Flush remaining offsets before stopping consumer
        if self.kafka_client.consumer:
            try:
                await self.offset_manager.flush_pending_offsets(self.kafka_client.consumer)
            except Exception:
                self.log.warning("commit_remaining_offsets_failed", exc_info=True)

        # Stop Kafka clients
        await self.kafka_client.stop_all()
        self.log.info("agent_stopped")

    def get_status(self) -> dict[str, Any]:
        """Return per-agent status for health reporting."""
        state = self._compute_state()
        return {
            "running": self.is_running,
            "ready": self.ready,
            "connected": self.kafka_client.connected,
            "assigned_partitions": self.kafka_client.assigned_partitions,
            "metrics": self.metrics.get_metrics_dict(),
            "state": state,
            **self.metrics.get_status_dict(),
        }

    def _compute_state(self) -> str:
        """Compute current agent state."""
        if self.is_running and not self.ready:
            return "STARTING"
        if self.is_running and self.ready:
            return "DEGRADED" if self.metrics.last_error else "RUNNING"
        if self.metrics.last_error:
            return "FAILED"
        return "STOPPED"

    async def on_start(self):
        """Hook method called on start, subclasses can override."""
        # Provide a non-empty default implementation to satisfy linting rules
        self.log.debug("on_start_hook_invoked", implementation="default_no_op")

    async def on_stop(self):
        """Hook method called on stop, subclasses can override."""
        # Provide a non-empty default implementation to satisfy linting rules
        self.log.debug("on_stop_hook_invoked", implementation="default_no_op")
