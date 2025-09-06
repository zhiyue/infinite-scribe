"""
DomainEventBridgeService - Main service for EventBridge.

This module implements the main EventBridge service that coordinates all components
to bridge domain events from Kafka to SSE channels via Redis.
"""

import logging
from typing import Any

from src.agents.offset_manager import OffsetManager
from src.core.kafka.client import KafkaClientManager
from src.services.eventbridge.circuit_breaker import CircuitBreaker
from src.services.eventbridge.filter import EventFilter
from src.services.eventbridge.metrics import EventBridgeMetricsCollector
from src.services.eventbridge.publisher import Publisher
from src.services.sse.redis_client import RedisSSEService

logger = logging.getLogger(__name__)


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

        logger.info("DomainEventBridge service initialized")

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
                    logger.info(f"Circuit breaker registered with {len(partitions)} partitions")
            except Exception as e:
                logger.error(f"Failed to register circuit breaker: {e}")

    async def _process_event(self, message: Any) -> bool:
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
            logger.warning(f"Skipping malformed message at {message.topic}:{message.partition}:{message.offset}")
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
            logger.debug(f"Event filtered: {reason}, event_type={envelope.get('event_type')}")
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
        logger.debug(f"Event dropped due to open circuit, event_id={envelope.get('event_id')}")

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
            f"Successfully published event {envelope.get('event_type')} "
            f"for user {envelope.get('payload', {}).get('user_id')}"
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
            f"Failed to publish event {envelope.get('event_type')}: {error}",
            extra={
                "event_id": envelope.get("event_id"),
                "correlation_id": envelope.get("correlation_id"),
                "user_id": envelope.get("payload", {}).get("user_id"),
            },
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
            f"Unexpected error processing message at {message.topic}:{message.partition}:{message.offset}: {error}",
            exc_info=True,
        )

    async def _commit_processed_offsets(self) -> None:
        """Commit processed offsets in batch."""
        try:
            if self.consumer:
                await self.offset_manager.flush_pending_offsets(self.consumer)
                logger.debug("Successfully committed processed offsets")
            else:
                logger.warning("Cannot commit offsets: no consumer reference")
        except Exception as e:
            logger.error(f"Failed to commit offsets: {e}")

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the EventBridge service.

        Cleanup sequence:
        1. Flush pending offsets
        2. Stop Kafka consumer
        3. Close Redis connections
        """
        logger.info("Shutting down DomainEventBridge service")

        try:
            # Step 1: Flush pending offsets
            if self.consumer:
                await self.offset_manager.flush_pending_offsets(self.consumer)
                logger.info("Flushed pending offsets")
            else:
                logger.warning("Cannot flush offsets during shutdown: no consumer reference")

            # Step 2: Stop Kafka consumer
            await self.kafka_client_manager.stop_consumer()
            logger.info("Stopped Kafka consumer")

            # Step 3: Close Redis connections
            await self.redis_sse_service.close()
            logger.info("Closed Redis SSE service")

            # Log final metrics
            self.metrics_collector.log_final_metrics()

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

        logger.info("DomainEventBridge service shutdown complete")

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

            return envelope

        except Exception as e:
            logger.warning(f"Failed to extract envelope from message: {e}")
            return None

    def get_health_status(self) -> dict[str, Any]:
        """
        Get current health status of the EventBridge service.

        Returns:
            Health status dictionary
        """
        return self.metrics_collector.get_health_status()
