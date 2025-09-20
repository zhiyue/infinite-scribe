"""
DomainEventBridgeService - EventBridge 主服务

本模块实现了 EventBridge 的主服务，协调所有组件将 Kafka 中的领域事件
通过 Redis 桥接到 SSE 通道。

架构概览:
========

EventBridge 服务采用流水线架构，领域事件流经多个阶段：

1. Kafka 消费者 → 从 Kafka 主题接收领域事件
2. 事件过滤器 → 根据业务规则验证和过滤事件
3. 熔断器 → 优雅处理 Redis 故障
4. 发布器 → 转换事件并发布到 SSE 通道
5. Redis SSE 服务 → 通过服务器发送事件将事件传递到前端

关键设计原则:
============

- 优雅降级：如果 Redis 失败，继续处理 Kafka 但丢弃 SSE
- 容错性：熔断器防止级联故障
- 数据最小化：只向前端发送必要数据
- 可观测性：全面的指标和日志记录
- 可测试性：依赖注入便于模拟测试

事件流程:
========

1. DomainEventBridgeService.process_event() 接收 Kafka 消息
2. 验证信封结构和必需字段
3. EventFilter 检查白名单（仅 Genesis.Session.*）
4. CircuitBreaker 检查 Redis 是否健康
5. Publisher 将信封转换为 SSEMessage 格式
6. RedisSSEService 路由到用户专用通道
7. OffsetManager 记录进度以保证精确一次语义

错误处理策略:
============

- 格式错误的消息：记录日志并跳过（继续处理）
- 验证失败：过滤掉并记录指标
- Redis 故障：熔断器打开，事件丢弃但 Kafka 处理继续
- 消费者错误：使用退避和重试处理
- 配置错误：快速失败并提供清晰的错误消息

指标和监控:
==========

服务跟踪全面的指标：
- 事件计数（消费、发布、丢弃、过滤）
- 熔断器状态和故障率
- Redis 发布延迟
- 健康状态计算
- 可选的 Prometheus 集成

配置:
====

所有配置都集中在 core/config.py 中，支持环境变量：
- Kafka 主题和消费者组设置
- 熔断器阈值和间隔
- 指标收集设置
- Redis 连接参数
"""

from typing import Any

from src.agents.offset_manager import OffsetManager
from src.core.kafka.client import KafkaClientManager
from src.core.logging import get_logger
from src.services.eventbridge.circuit_breaker import CircuitBreaker
from src.services.eventbridge.filter import EventFilter
from src.services.eventbridge.metrics import EventBridgeMetricsCollector
from src.services.eventbridge.publisher import Publisher
from src.services.sse.redis_client import RedisSSEService

logger = get_logger(__name__)


class DomainEventBridgeService:
    """
    Main EventBridge service coordinating all components.

    Implements the bridge pattern to connect Kafka domain events with SSE channels.
    Uses dependency injection and chain of responsibility patterns for clean
    separation of concerns and testability.

    Architecture:
    Kafka → EventFilter → CircuitBreaker → Publisher → Redis → SSE

    Features:
    - Event filtering and validation
    - Circuit breaker for Redis failures
    - Graceful degradation (continue processing, drop SSE)
    - Offset management with batching
    - Consumer pause/resume integration
    - Comprehensive error handling
    """

    def __init__(
        self,
        kafka_client_manager: KafkaClientManager,
        offset_manager: OffsetManager,
        redis_sse_service: RedisSSEService,
        event_filter: EventFilter,
        circuit_breaker: CircuitBreaker,
        publisher: Publisher,
        metrics_collector: EventBridgeMetricsCollector,
    ):
        """
        Initialize EventBridge service with all dependencies.

        Args:
            kafka_client_manager: Manages Kafka consumer lifecycle
            offset_manager: Handles batch offset commits
            redis_sse_service: Publishes SSE messages to Redis
            event_filter: Validates and filters events
            circuit_breaker: Handles Redis failure resilience
            publisher: Transforms and publishes events
            metrics_collector: Centralized metrics tracking
        """
        self.kafka_client_manager = kafka_client_manager
        self.offset_manager = offset_manager
        self.redis_sse_service = redis_sse_service
        self.event_filter = event_filter
        self.circuit_breaker = circuit_breaker
        self.publisher = publisher
        self.metrics_collector = metrics_collector

        # Consumer reference for offset management
        self.consumer = None

        logger.info("DomainEventBridge service initialized", service="eventbridge")

    def set_consumer(self, consumer) -> None:
        """Set the Kafka consumer reference for offset management."""
        self.consumer = consumer
        logger.debug("Consumer reference set for offset management")

        # Note: Circuit breaker registration with partitions will be done
        # after the first poll when partition assignment is available

    def _ensure_circuit_breaker_integration(self) -> None:
        """Ensure circuit breaker is integrated with consumer after partition assignment."""
        if self.consumer and not hasattr(self, "_circuit_breaker_registered"):
            try:
                # Get current partition assignment
                partitions = self.consumer.assignment()
                if partitions:
                    # Register consumer with circuit breaker using actual partitions
                    self.circuit_breaker.register_consumer(self.consumer, partitions)
                    self._circuit_breaker_registered = True
                    logger.info(
                        "Circuit breaker registered with consumer",
                        partitions_count=len(partitions),
                        service="eventbridge",
                    )
            except Exception as e:
                logger.error("Failed to register circuit breaker", error=str(e), service="eventbridge")

    def update_circuit_breaker_partitions(self, new_partitions: list[Any]) -> None:
        """
        Update circuit breaker with new partition assignment after rebalance.

        Args:
            new_partitions: New partition assignment from Kafka rebalance
        """
        try:
            if self.consumer and hasattr(self, "_circuit_breaker_registered"):
                # Update circuit breaker with new partitions
                self.circuit_breaker.update_partitions(new_partitions)
                logger.info(
                    "Updated circuit breaker partitions after rebalance",
                    new_partitions_count=len(new_partitions),
                    service="eventbridge",
                )
        except Exception as e:
            logger.error("Failed to update circuit breaker partitions", error=str(e), service="eventbridge")

    async def process_event(self, message: Any) -> bool:
        """
        Process a single Kafka message through the event pipeline.

        Pipeline: Validate → Filter → Circuit Check → Publish → Record Result

        Args:
            message: Kafka message with value, topic, partition, offset

        Returns:
            bool: True if processing should continue, False to stop
        """
        try:
            # Ensure circuit breaker is integrated on first message
            self._ensure_circuit_breaker_integration()

            self.metrics_collector.record_event_consumed()

            # Extract and validate envelope
            envelope = self._extract_and_validate_envelope(message)
            if not envelope:
                return True  # Continue processing

            # Filter and validate event
            if not self._filter_event(envelope):
                return True  # Continue processing (filtered events are normal)

            # Check circuit breaker and publish
            await self._attempt_publish_with_circuit_breaker(envelope)

            # Record offset for successful processing
            if self.consumer:
                await self.offset_manager.record_offset_and_maybe_commit(self.consumer, message)

            # Record metrics periodically
            self.metrics_collector.maybe_log_periodic_metrics(envelope, message)

            return True  # Continue processing

        except Exception as e:
            self._handle_unexpected_error(message, e)
            return True  # Continue processing even on unexpected errors

    def _extract_and_validate_envelope(self, message: Any) -> dict[str, Any] | None:
        """
        Extract and validate event envelope from Kafka message.

        Args:
            message: Kafka message

        Returns:
            Event envelope dict or None if invalid
        """
        envelope = self._extract_envelope(message)
        if not envelope:
            logger.warning(
                "Skipping malformed message",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                service="eventbridge",
            )
            return None
        return envelope

    def _filter_event(self, envelope: dict[str, Any]) -> bool:
        """
        Filter and validate event against business rules.

        Args:
            envelope: Event envelope

        Returns:
            True if event should be processed, False if filtered out
        """
        is_valid, reason = self.event_filter.validate(envelope)
        if not is_valid:
            self.metrics_collector.record_event_filtered()
            logger.debug("Event filtered", reason=reason, event_type=envelope.get("event_type"), service="eventbridge")
            return False
        return True

    async def _attempt_publish_with_circuit_breaker(self, envelope: dict[str, Any]) -> None:
        """
        Attempt to publish event with circuit breaker protection.

        Args:
            envelope: Event envelope to publish
        """
        # Check circuit breaker state
        if not self.circuit_breaker.can_attempt():
            self._handle_circuit_breaker_open(envelope)
            return

        # Attempt to publish
        try:
            await self._publish_event(envelope)
        except Exception as publish_error:
            self._handle_publish_failure(envelope, publish_error)
        finally:
            # Always record attempt for circuit breaker metrics
            self.circuit_breaker.record_attempt()

    def _handle_circuit_breaker_open(self, envelope: dict[str, Any]) -> None:
        """
        Handle event when circuit breaker is open.

        Args:
            envelope: Event envelope that was dropped
        """
        self.metrics_collector.record_event_dropped()
        logger.debug(
            "Event dropped due to open circuit",
            event_id=envelope.get("event_id"),
            event_type=envelope.get("event_type"),
            service="eventbridge",
        )

    async def _publish_event(self, envelope: dict[str, Any]) -> None:
        """
        Publish event and record success.

        Args:
            envelope: Event envelope to publish
        """
        await self.publisher.publish(envelope)
        self.metrics_collector.record_event_published()
        self.circuit_breaker.record_success()

        logger.debug(
            "Successfully published event",
            event_type=envelope.get("event_type"),
            event_id=envelope.get("event_id"),
            user_id=envelope.get("payload", {}).get("user_id"),
            service="eventbridge",
        )

    def _handle_publish_failure(self, envelope: dict[str, Any], error: Exception) -> None:
        """
        Handle publish failure with proper error logging.

        Args:
            envelope: Event envelope that failed to publish
            error: Exception that occurred during publishing
        """
        self.metrics_collector.record_event_dropped()
        self.circuit_breaker.record_failure()

        logger.error(
            "Failed to publish event",
            event_type=envelope.get("event_type"),
            event_id=envelope.get("event_id"),
            correlation_id=envelope.get("correlation_id"),
            user_id=envelope.get("payload", {}).get("user_id"),
            error=str(error),
            service="eventbridge",
        )
        # In degraded mode, we continue processing Kafka but drop SSE
        # This maintains event fact consistency while losing real-time UI updates

    def _handle_unexpected_error(self, message: Any, error: Exception) -> None:
        """
        Handle unexpected errors during event processing.

        Args:
            message: Kafka message that caused the error
            error: Exception that occurred
        """
        logger.error(
            "Unexpected error processing message",
            topic=message.topic,
            partition=message.partition,
            offset=message.offset,
            error=str(error),
            service="eventbridge",
            exc_info=True,
        )

    async def commit_processed_offsets(self) -> None:
        """Commit processed offsets in batch."""
        try:
            if self.consumer:
                await self.offset_manager.flush_pending_offsets(self.consumer)
                logger.debug("Successfully committed processed offsets", service="eventbridge")
            else:
                logger.warning("Cannot commit offsets: no consumer reference", service="eventbridge")
        except Exception as e:
            logger.error("Failed to commit offsets", error=str(e), service="eventbridge")

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the EventBridge service.

        Cleanup sequence:
        1. Flush pending offsets
        2. Stop Kafka consumer
        3. Close Redis connections
        """
        logger.info("Shutting down DomainEventBridge service", service="eventbridge")

        try:
            # Step 1: Flush pending offsets
            if self.consumer:
                await self.offset_manager.flush_pending_offsets(self.consumer)
                logger.info("Flushed pending offsets", service="eventbridge")
            else:
                logger.warning("Cannot flush offsets during shutdown: no consumer reference", service="eventbridge")

            # Step 2: Stop Kafka consumer
            await self.kafka_client_manager.stop_consumer()
            logger.info("Stopped Kafka consumer", service="eventbridge")

            # Step 3: Close Redis connections
            await self.redis_sse_service.close()
            logger.info("Closed Redis SSE service", service="eventbridge")

            # Log final metrics
            self.metrics_collector.log_final_metrics()

        except Exception as e:
            logger.error("Error during shutdown", error=str(e), service="eventbridge", exc_info=True)

        logger.info("DomainEventBridge service shutdown complete", service="eventbridge")

    def _extract_envelope(self, message: Any) -> dict[str, Any] | None:
        """
        Extract and validate event envelope from Kafka message.

        Args:
            message: Kafka message

        Returns:
            Event envelope dict or None if invalid
        """
        try:
            if not hasattr(message, "value") or not isinstance(message.value, dict):
                return None

            envelope = message.value

            # Basic envelope validation
            if not isinstance(envelope, dict):
                return None

            # Merge selected Kafka headers into envelope for downstream validation
            try:
                headers = dict((k, (v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else v)) for k, v in (message.headers or []))
            except Exception:  # pragma: no cover - defensive
                headers = {}

            if "correlation_id" not in envelope and headers.get("correlation_id"):
                envelope["correlation_id"] = headers.get("correlation_id")

            # Ensure required payload shape with sensible fallbacks
            payload = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}
            if not payload:
                payload = {}
                envelope["payload"] = payload

            if "session_id" not in payload and envelope.get("aggregate_id"):
                payload["session_id"] = envelope.get("aggregate_id")

            if "timestamp" not in payload and envelope.get("created_at"):
                payload["timestamp"] = envelope.get("created_at")

            return envelope

        except Exception as e:
            logger.warning("Failed to extract envelope from message", error=str(e), service="eventbridge")
            return None

    def get_health_status(self) -> dict[str, Any]:
        """
        Get current health status of the EventBridge service.

        Returns:
            Health status dictionary
        """
        return self.metrics_collector.get_health_status()
