"""
EventBridge service main entry point.

This module provides the main application entry point for the EventBridge service
with proper signal handling, lifecycle management, and graceful shutdown.
"""

import asyncio
import signal
import sys

from aiokafka.abc import ConsumerRebalanceListener

from src.core.logging import get_logger
from src.services.eventbridge.factory import get_event_bridge_factory


class EventBridgeRebalanceListener:
    """
    Kafka consumer rebalance listener for EventBridge.

    Handles partition assignment and revocation events to ensure proper
    circuit breaker integration and resource management.
    """

    def __init__(self, bridge_service, logger):
        """
        Initialize the rebalance listener.

        Args:
            bridge_service: DomainEventBridgeService instance
            logger: Structured logger for event tracking
        """
        self.bridge_service = bridge_service
        self.logger = logger

    def on_partitions_assigned(self, assigned):
        """
        Called when partitions are assigned to the consumer.

        Args:
            assigned: List of TopicPartition objects assigned to consumer
        """
        try:
            partition_info = [f"{tp.topic}:{tp.partition}" for tp in assigned]
            self.logger.info(
                "Kafka partitions assigned",
                partitions_count=len(assigned),
                partitions=partition_info,
                service="eventbridge",
            )

            # Update circuit breaker with new partition assignment
            if assigned and self.bridge_service:
                self.bridge_service.update_circuit_breaker_partitions(assigned)

        except Exception as e:
            self.logger.error("Error handling partition assignment", error=str(e), service="eventbridge", exc_info=True)

    def on_partitions_revoked(self, revoked):
        """
        Called when partitions are revoked from the consumer.

        Args:
            revoked: List of TopicPartition objects revoked from consumer
        """
        try:
            partition_info = [f"{tp.topic}:{tp.partition}" for tp in revoked]
            self.logger.info(
                "Kafka partitions revoked",
                partitions_count=len(revoked),
                partitions=partition_info,
                service="eventbridge",
            )

            # Circuit breaker will be updated with new assignment in on_partitions_assigned
            # No specific action needed here as we don't want to lose state during rebalance

        except Exception as e:
            self.logger.error("Error handling partition revocation", error=str(e), service="eventbridge", exc_info=True)


class _AIOKafkaRebalanceAdapter(ConsumerRebalanceListener):
    """Adapter to conform to aiokafka's ConsumerRebalanceListener interface.

    Wraps our internal listener and forwards events, supporting both sync and async handlers.
    """

    def __init__(self, inner: EventBridgeRebalanceListener, logger):
        self._inner = inner
        self._logger = logger

    async def on_partitions_assigned(self, assigned):  # type: ignore[override]
        try:
            self._inner.on_partitions_assigned(assigned)
        except Exception as e:  # pragma: no cover - defensive logging
            self._logger.error("Adapter error on partitions assigned", error=str(e))

    async def on_partitions_revoked(self, revoked):  # type: ignore[override]
        try:
            self._inner.on_partitions_revoked(revoked)
        except Exception as e:  # pragma: no cover - defensive logging
            self._logger.error("Adapter error on partitions revoked", error=str(e))


class EventBridgeApplication:
    """
    EventBridge application with lifecycle management.

    Implements the Command pattern for application lifecycle and provides
    proper signal handling and graceful shutdown capabilities.

    Features:
    - Signal handling (SIGTERM, SIGINT)
    - Graceful shutdown
    - Error handling and recovery
    - Health monitoring
    - Metrics logging
    """

    def __init__(self):
        """Initialize the EventBridge application."""
        self.is_running = False
        self.shutdown_requested = False
        self.factory = get_event_bridge_factory()
        self.bridge_service = None
        self.logger = get_logger(__name__)

        # Setup signal handlers
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum: int, frame) -> None:
            signame = signal.Signals(signum).name
            self.logger.info(f"Received {signame}, initiating graceful shutdown...")
            self.shutdown_requested = True

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        self.logger.debug("Signal handlers configured")

    async def start(self) -> None:
        """
        Start the EventBridge service.

        This is the main application entry point that initializes all components
        and starts the event processing loop.
        """
        self.logger.info("Starting EventBridge service...")

        try:
            # Initialize service
            await self._initialize_service()

            # Start main processing loop
            await self._run_main_loop()

        except Exception as e:
            self.logger.error(f"Fatal error in EventBridge service: {e}", exc_info=True)
            raise
        finally:
            # Ensure cleanup happens
            await self._cleanup()

    async def _initialize_service(self) -> None:
        """Initialize the EventBridge service and its dependencies."""
        self.logger.info("Initializing EventBridge service components...")

        # Create the main service
        self.bridge_service = self.factory.create_event_bridge_service()

        # Initialize Redis SSE service
        redis_sse_service = self.factory.get_redis_sse_service()
        await redis_sse_service.init_pubsub_client()

        self.logger.info("EventBridge service initialization complete")

    async def _run_main_loop(self) -> None:
        """
        Run the main event processing loop.

        This implements the main EventBridge processing logic:
        1. Create Kafka consumer
        2. Poll for messages
        3. Process messages through pipeline
        4. Commit offsets periodically
        5. Handle shutdown signals
        """
        self.logger.info("Starting EventBridge main processing loop...")

        # Setup consumer
        consumer = await self._setup_kafka_consumer()

        # Set consumer reference in bridge service for offset management
        if not self.bridge_service:
            raise RuntimeError("Bridge service not initialized")
        self.bridge_service.set_consumer(consumer)

        # Initialize loop state
        loop_state = self._initialize_loop_state()

        try:
            while self.is_running and not self.shutdown_requested:
                try:
                    # Poll and process messages
                    await self._process_message_batch(consumer, loop_state)

                    # Handle periodic tasks
                    await self._handle_periodic_tasks(loop_state)

                except Exception as e:
                    self._handle_loop_error(e)
                    await asyncio.sleep(1.0)

        finally:
            self.logger.info("Exiting main processing loop")

    async def _setup_kafka_consumer(self):
        """
        Setup Kafka consumer with topic subscription and rebalance listener.

        Returns:
            Configured Kafka consumer

        Raises:
            RuntimeError: If consumer creation fails
        """
        kafka_client_manager = self.factory.get_kafka_client_manager()

        # Create consumer (without subscribing yet)
        consumer = await kafka_client_manager.create_consumer()
        if not consumer:
            raise RuntimeError("Failed to create Kafka consumer")

        # Create rebalance listener for partition management
        if not self.bridge_service:
            raise RuntimeError("Bridge service not initialized")
        rebalance_listener = EventBridgeRebalanceListener(bridge_service=self.bridge_service, logger=self.logger)

        # Subscribe to topics with rebalance listener (aiokafka requires a specific ABC)
        kafka_client_manager.subscribe_consumer(listener=_AIOKafkaRebalanceAdapter(rebalance_listener, self.logger))

        consume_topics = self.factory.eventbridge_config.domain_topics
        self.logger.info(
            "Kafka consumer setup complete", topics=consume_topics, with_rebalance_listener=True, service="eventbridge"
        )
        return consumer

    def _initialize_loop_state(self) -> dict:
        """
        Initialize loop state for tracking processing metrics.

        Returns:
            Dictionary with loop state variables
        """
        self.is_running = True
        return {
            "messages_processed": 0,
            "last_commit_time": asyncio.get_event_loop().time(),
            "commit_interval": self.factory.eventbridge_config.commit_interval_ms / 1000.0,
        }

    async def _process_message_batch(self, consumer, loop_state: dict) -> None:
        """
        Poll for messages and process them through the pipeline.

        Args:
            consumer: Kafka consumer
            loop_state: Loop state tracking dictionary
        """
        message_batch = await consumer.getmany(timeout_ms=1000)

        if not message_batch:
            # No messages, brief sleep to avoid busy waiting
            await asyncio.sleep(0.1)
            return

        # Process all messages in the batch
        for _topic_partition, messages in message_batch.items():
            for message in messages:
                if await self._process_single_message(message):
                    loop_state["messages_processed"] += 1
                else:
                    # Processing indicated to stop
                    self.shutdown_requested = True
                    return

            if self.shutdown_requested:
                break

    async def _process_single_message(self, message) -> bool:
        """
        Process a single message and handle stop signals.

        Args:
            message: Kafka message to process

        Returns:
            True if processing should continue, False to stop
        """
        if not self.bridge_service:
            return False
        continue_processing = await self.bridge_service.process_event(message)

        if not continue_processing:
            self.logger.warning("Event processing indicated to stop")
            return False

        return True

    async def _handle_periodic_tasks(self, loop_state: dict) -> None:
        """
        Handle periodic tasks like offset commits and health checks.

        Args:
            loop_state: Loop state tracking dictionary
        """
        current_time = asyncio.get_event_loop().time()

        # Periodic offset commit
        if (current_time - loop_state["last_commit_time"]) >= loop_state["commit_interval"]:
            await self._commit_offsets_with_logging(loop_state)
            loop_state["last_commit_time"] = current_time

        # Periodic health check
        if loop_state["messages_processed"] > 0 and loop_state["messages_processed"] % 1000 == 0:
            self._check_service_health()

    async def _commit_offsets_with_logging(self, loop_state: dict) -> None:
        """
        Commit offsets with debug logging.

        Args:
            loop_state: Loop state tracking dictionary
        """
        if self.bridge_service:
            await self.bridge_service.commit_processed_offsets()
        self.logger.debug(f"Processed {loop_state['messages_processed']} messages, committed offsets")

    def _check_service_health(self) -> None:
        """
        Check service health and log warnings if degraded.
        """
        if self.bridge_service:
            health_status = self.bridge_service.get_health_status()
            if not health_status.get("healthy", True):
                self.logger.warning(f"Service health degraded: {health_status}")

    def _handle_loop_error(self, error: Exception) -> None:
        """
        Handle errors in the main processing loop.

        Args:
            error: Exception that occurred in the loop
        """
        self.logger.error(f"Error in main processing loop: {error}", exc_info=True)

    async def _cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        self.logger.info("Starting EventBridge cleanup...")

        try:
            # Stop processing
            self.is_running = False

            # Shutdown services in order
            await self._shutdown_services()

            self.logger.info("EventBridge cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}", exc_info=True)

    async def _shutdown_services(self) -> None:
        """
        Shutdown services in the correct order.
        """
        # Shutdown bridge service first
        if self.bridge_service:
            await self.bridge_service.shutdown()

        # Cleanup factory resources
        await self.factory.cleanup()

    async def stop(self) -> None:
        """Stop the EventBridge service."""
        self.logger.info("Stopping EventBridge service...")
        self.shutdown_requested = True

        # Wait a bit for graceful shutdown
        for _ in range(10):  # Wait up to 10 seconds
            if not self.is_running:
                break
            await asyncio.sleep(1.0)

        if self.is_running:
            self.logger.warning("Force stopping EventBridge service")
            self.is_running = False


def setup_logging() -> None:
    """Setup logging configuration for EventBridge."""
    # Note: Logging configuration is handled by src.core.logging
    # This function is kept for compatibility but does nothing
    pass


async def main() -> None:
    """Main application entry point."""
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    logger.info("EventBridge service starting up...")

    try:
        # Create and start application
        app = EventBridgeApplication()
        await app.start()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"EventBridge service failed: {e}", exc_info=True)
        sys.exit(1)

    logger.info("EventBridge service shut down complete")


if __name__ == "__main__":
    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nEventBridge service interrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
