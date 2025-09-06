"""
EventBridge service factory.

This module implements the Factory pattern for creating and configuring
EventBridge service instances with proper dependency injection.
"""

import logging
from collections.abc import Callable
from typing import TypeVar

from src.agents.offset_manager import OffsetManager
from src.common.services.redis_service import RedisService
from src.core.config import get_settings
from src.core.kafka.client import KafkaClientManager
from src.services.eventbridge.bridge import DomainEventBridgeService
from src.services.eventbridge.circuit_breaker import CircuitBreaker
from src.services.eventbridge.filter import EventFilter
from src.services.eventbridge.metrics import EventBridgeMetricsCollector
from src.services.eventbridge.publisher import Publisher
from src.services.sse.redis_client import RedisSSEService

T = TypeVar("T")

logger = logging.getLogger(__name__)


class EventBridgeServiceFactory:
    """
    Factory for creating EventBridge service instances.

    Implements the Factory pattern with dependency injection to create
    properly configured EventBridge services with all required dependencies.

    Features:
    - Dependency injection container
    - Configuration-driven instantiation
    - Singleton management for shared resources
    - Proper cleanup and lifecycle management
    """

    def __init__(self):
        """Initialize the service factory with unified configuration."""
        settings = get_settings()
        self.settings = settings
        self.eventbridge_config = settings.eventbridge

        # Singleton instances for shared resources
        self._kafka_client_manager: KafkaClientManager | None = None
        self._offset_manager: OffsetManager | None = None
        self._redis_service: RedisService | None = None
        self._redis_sse_service: RedisSSEService | None = None

        # Service instances
        self._event_filter: EventFilter | None = None
        self._circuit_breaker: CircuitBreaker | None = None
        self._publisher: Publisher | None = None
        self._metrics_collector: EventBridgeMetricsCollector | None = None
        self._bridge_service: DomainEventBridgeService | None = None

        logger.info("EventBridge service factory initialized")

    def _get_or_create_singleton(self, attr_name: str, factory_func: Callable[[], T], description: str) -> T:
        """
        Generic singleton getter that creates instances on first access.

        Args:
            attr_name: Name of the instance attribute to check/set
            factory_func: Function to create the instance if it doesn't exist
            description: Description for logging purposes

        Returns:
            The singleton instance
        """
        instance = getattr(self, attr_name, None)
        if instance is None:
            instance = factory_func()
            setattr(self, attr_name, instance)
            logger.debug(f"Created {description}")
        return instance

    def create_event_bridge_service(self) -> DomainEventBridgeService:
        """
        Create a fully configured EventBridge service.

        Returns:
            Configured DomainEventBridgeService instance
        """
        if self._bridge_service is None:
            logger.info("Creating EventBridge service with dependencies...")

            # Create core dependencies
            kafka_client_manager = self._get_kafka_client_manager()
            offset_manager = self._get_offset_manager()
            redis_sse_service = self._get_redis_sse_service()

            # Create EventBridge components
            event_filter = self._get_event_filter()
            circuit_breaker = self._get_circuit_breaker()
            publisher = self._get_publisher()
            metrics_collector = self._get_metrics_collector()

            # Create the main service
            self._bridge_service = DomainEventBridgeService(
                kafka_client_manager=kafka_client_manager,
                offset_manager=offset_manager,
                redis_sse_service=redis_sse_service,
                event_filter=event_filter,
                circuit_breaker=circuit_breaker,
                publisher=publisher,
                metrics_collector=metrics_collector,
            )

            # Note: Circuit breaker consumer integration is handled at runtime
            # when the actual consumer is created in main.py

            logger.info("EventBridge service created successfully")

        return self._bridge_service

    def _get_kafka_client_manager(self) -> KafkaClientManager:
        """Get or create KafkaClientManager instance."""
        return self._get_or_create_singleton(
            "_kafka_client_manager",
            lambda: KafkaClientManager(
                agent_name="event-bridge",
                consume_topics=self.eventbridge_config.domain_topics,
                produce_topics=[],  # EventBridge doesn't produce to Kafka
            ),
            "KafkaClientManager",
        )

    def _get_offset_manager(self) -> OffsetManager:
        """Get or create OffsetManager instance."""
        return self._get_or_create_singleton(
            "_offset_manager",
            lambda: OffsetManager(
                agent_name="event-bridge",
                commit_batch_size=self.eventbridge_config.commit_batch_size,
                commit_interval_ms=self.eventbridge_config.commit_interval_ms,
            ),
            "OffsetManager",
        )

    def _get_redis_service(self) -> RedisService:
        """Get or create RedisService instance."""
        return self._get_or_create_singleton("_redis_service", lambda: RedisService(), "RedisService")

    def _get_redis_sse_service(self) -> RedisSSEService:
        """Get or create RedisSSEService instance."""
        return self._get_or_create_singleton(
            "_redis_sse_service", lambda: RedisSSEService(self._get_redis_service()), "RedisSSEService"
        )

    def _get_event_filter(self) -> EventFilter:
        """Get or create EventFilter instance."""
        return self._get_or_create_singleton("_event_filter", lambda: EventFilter(), "EventFilter")

    def _get_circuit_breaker(self) -> CircuitBreaker:
        """Get or create CircuitBreaker instance."""

        def create_circuit_breaker() -> CircuitBreaker:
            return CircuitBreaker(
                window_seconds=self.eventbridge_config.cb_window_seconds,
                failure_threshold=self.eventbridge_config.cb_fail_rate_threshold,
                half_open_interval_seconds=self.eventbridge_config.cb_half_open_interval_seconds,
            )

        return self._get_or_create_singleton("_circuit_breaker", create_circuit_breaker, "CircuitBreaker")

    def _get_publisher(self) -> Publisher:
        """Get or create Publisher instance."""
        return self._get_or_create_singleton(
            "_publisher", lambda: Publisher(self._get_redis_sse_service()), "Publisher"
        )

    def _get_metrics_collector(self) -> EventBridgeMetricsCollector:
        """Get or create EventBridgeMetricsCollector instance."""
        return self._get_or_create_singleton(
            "_metrics_collector",
            lambda: EventBridgeMetricsCollector(self._get_circuit_breaker()),
            "EventBridgeMetricsCollector",
        )

    def _setup_circuit_breaker_consumer_integration(self) -> None:
        """Setup circuit breaker integration with Kafka consumer."""
        try:
            kafka_client_manager = self._get_kafka_client_manager()
            circuit_breaker = self._get_circuit_breaker()

            # Create consumer to get partitions
            consumer = kafka_client_manager.create_consumer()
            if consumer:
                # Subscribe to topics to get partition assignment
                consumer.subscribe(self.eventbridge_config.domain_topics)

                # Get assigned partitions (this might be empty initially)
                partitions = consumer.assignment()

                # Register consumer with circuit breaker
                circuit_breaker.register_consumer(consumer, partitions)

                logger.info("Circuit breaker integrated with Kafka consumer")
            else:
                logger.warning("Could not create consumer for circuit breaker integration")

        except Exception as e:
            logger.error(f"Failed to setup circuit breaker consumer integration: {e}")

    async def cleanup(self) -> None:
        """Cleanup all created resources."""
        logger.info("Cleaning up EventBridge factory resources...")

        try:
            # Cleanup in reverse order of creation
            if self._bridge_service:
                await self._bridge_service.shutdown()

            if self._redis_sse_service:
                await self._redis_sse_service.close()

            if self._kafka_client_manager:
                self._kafka_client_manager.stop_all()

            logger.info("EventBridge factory cleanup completed")

        except Exception as e:
            logger.error(f"Error during factory cleanup: {e}", exc_info=True)

    def get_health_status(self) -> dict:
        """Get health status of created services."""
        status = {"factory_initialized": True, "services": {}}

        if self._bridge_service:
            status["services"]["bridge"] = self._bridge_service.get_health_status()

        if self._redis_sse_service:
            # Could add Redis SSE health check here
            status["services"]["redis_sse"] = {"initialized": True}

        return status


# Global factory instance
_factory_instance: EventBridgeServiceFactory | None = None


def get_event_bridge_factory() -> EventBridgeServiceFactory:
    """Get the global EventBridge service factory instance."""
    global _factory_instance

    if _factory_instance is None:
        _factory_instance = EventBridgeServiceFactory()

    return _factory_instance


def create_event_bridge_service() -> DomainEventBridgeService:
    """
    Convenience function to create EventBridge service.

    Returns:
        Configured DomainEventBridgeService instance
    """
    factory = get_event_bridge_factory()
    return factory.create_event_bridge_service()
