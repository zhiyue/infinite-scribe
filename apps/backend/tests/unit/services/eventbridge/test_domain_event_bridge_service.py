"""
Unit tests for DomainEventBridgeService.

Tests the main event bridge service that coordinates all components.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from src.services.eventbridge.bridge import DomainEventBridgeService
from src.services.eventbridge.circuit_breaker import CircuitBreaker, CircuitState
from src.services.eventbridge.filter import EventFilter
from src.services.eventbridge.metrics import EventBridgeMetricsCollector
from src.services.eventbridge.publisher import Publisher


class TestDomainEventBridgeService:
    """Test DomainEventBridgeService main coordination logic."""

    def setup_method(self):
        """Setup test fixtures with mocked dependencies."""
        # Mock dependencies
        self.kafka_client_manager = Mock()
        self.offset_manager = Mock()
        self.redis_sse_service = Mock()

        # Mock consumer
        self.consumer = Mock()
        self.partitions = [Mock(), Mock()]
        self.kafka_client_manager.create_consumer.return_value = self.consumer
        self.consumer.assignment.return_value = self.partitions

        # Create real components (will be tested through integration)
        self.event_filter = EventFilter()
        self.circuit_breaker = CircuitBreaker(
            window_seconds=1,
            failure_threshold=0.5,
            half_open_interval_seconds=2,
        )
        self.publisher = Publisher(self.redis_sse_service)

        # Create metrics collector
        self.metrics_collector = Mock(spec=EventBridgeMetricsCollector)
        self.metrics_collector.record_event_consumed = Mock()
        self.metrics_collector.maybe_log_periodic_metrics = Mock()
        self.metrics_collector.get_health_status = Mock(return_value={"healthy": True})

        # Mock async methods
        self.offset_manager.flush_pending_offsets = AsyncMock()
        self.offset_manager.record_offset_and_maybe_commit = AsyncMock()

        # Create service
        self.service = DomainEventBridgeService(
            kafka_client_manager=self.kafka_client_manager,
            offset_manager=self.offset_manager,
            redis_sse_service=self.redis_sse_service,
            event_filter=self.event_filter,
            circuit_breaker=self.circuit_breaker,
            publisher=self.publisher,
            metrics_collector=self.metrics_collector,
        )

    @pytest.mark.asyncio
    async def test_event_bridge_processes_valid_events(self):
        """Test event bridge processes valid Genesis events successfully."""
        # Create valid event message
        valid_message = Mock()
        valid_message.value = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
            },
        }
        valid_message.topic = "genesis.session.events"
        valid_message.partition = 0
        valid_message.offset = 123

        # Mock successful Redis publish
        self.redis_sse_service.publish_event = AsyncMock(return_value="stream-id-123")

        # Process the event
        result = await self.service._process_event(valid_message)

        assert result is True
        self.redis_sse_service.publish_event.assert_called_once()

        # Verify circuit breaker recorded success
        assert self.circuit_breaker.success_count == 1

    @pytest.mark.asyncio
    async def test_event_bridge_filters_invalid_events(self):
        """Test event bridge filters out invalid events."""
        # Create invalid event message (non-Genesis)
        invalid_message = Mock()
        invalid_message.value = {
            "event_id": str(uuid4()),
            "event_type": "Chapter.Session.Started",  # Not Genesis
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
            },
        }
        invalid_message.topic = "genesis.session.events"
        invalid_message.partition = 0
        invalid_message.offset = 124

        # Process the event
        result = await self.service._process_event(invalid_message)

        assert result is True  # Processed (filtered out) successfully
        self.redis_sse_service.publish_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_event_bridge_degrades_gracefully_on_redis_failure(self):
        """Test event bridge continues processing when Redis fails."""
        valid_message = Mock()
        valid_message.value = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
            },
        }
        valid_message.topic = "genesis.session.events"
        valid_message.partition = 0
        valid_message.offset = 125

        # Mock Redis failure
        self.redis_sse_service.publish_event = AsyncMock(side_effect=Exception("Redis connection failed"))

        # Process should continue (degraded mode)
        result = await self.service._process_event(valid_message)

        assert result is True  # Still returns True to continue processing

        # Verify circuit breaker recorded failure
        assert self.circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_event_bridge_commits_offsets_in_batches(self):
        """Test event bridge commits offsets in batches."""
        # Mock processed messages
        messages = []
        for i in range(5):
            msg = Mock()
            msg.topic = "genesis.session.events"
            msg.partition = 0
            msg.offset = 100 + i
            msg.value = self._create_valid_event_value()
            messages.append(msg)

        self.redis_sse_service.publish_event = AsyncMock(return_value="stream-id")

        # Process all messages
        for msg in messages:
            result = await self.service._process_event(msg)
            assert result is True

        # Manually trigger offset commit (normally done by main loop)
        await self.service._commit_processed_offsets()

        # Set consumer reference first
        self.service.set_consumer(self.consumer)

        # Manually trigger offset commit (normally done by main loop)
        await self.service._commit_processed_offsets()

        # Verify offset manager was called with consumer
        self.offset_manager.flush_pending_offsets.assert_called_with(self.consumer)

    @pytest.mark.asyncio
    async def test_event_bridge_pauses_consumer_when_circuit_open(self):
        """Test event bridge pauses consumer when circuit breaker opens."""
        # Register consumer with circuit breaker
        self.circuit_breaker.register_consumer(self.consumer, self.partitions)

        # Create messages that will cause circuit to open
        messages = []
        for i in range(3):  # 3 failures should open circuit (100% failure rate)
            msg = Mock()
            msg.value = self._create_valid_event_value()
            msg.topic = "genesis.session.events"
            msg.partition = 0
            msg.offset = 200 + i
            messages.append(msg)

        # Mock Redis failures
        self.redis_sse_service.publish_event = AsyncMock(side_effect=Exception("Redis connection failed"))

        # Process messages - should open circuit
        for msg in messages:
            await self.service._process_event(msg)

        # Verify circuit is open and consumer was paused
        assert self.circuit_breaker.state == CircuitState.OPEN
        self.consumer.pause.assert_called_with(self.partitions)

    @pytest.mark.asyncio
    async def test_event_bridge_handles_malformed_messages(self):
        """Test event bridge handles malformed Kafka messages."""
        malformed_message = Mock()
        malformed_message.value = "not-a-dict"  # Should be dict
        malformed_message.topic = "genesis.session.events"
        malformed_message.partition = 0
        malformed_message.offset = 300

        # Should handle gracefully and continue
        result = await self.service._process_event(malformed_message)

        assert result is True  # Continue processing
        self.redis_sse_service.publish_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_event_bridge_records_processing_metrics(self):
        """Test event bridge records processing metrics."""
        valid_message = Mock()
        valid_message.value = self._create_valid_event_value()
        valid_message.topic = "genesis.session.events"
        valid_message.partition = 0
        valid_message.offset = 400

        self.redis_sse_service.publish_event = AsyncMock(return_value="stream-id")

        # Verify metrics are recorded
        await self.service._process_event(valid_message)

        # Verify metrics collector was called
        self.metrics_collector.record_event_consumed.assert_called_once()
        self.metrics_collector.maybe_log_periodic_metrics.assert_called_once()

    def test_event_bridge_startup_initialization(self):
        """Test event bridge initializes dependencies correctly."""
        # Verify all dependencies are stored
        assert self.service.kafka_client_manager == self.kafka_client_manager
        assert self.service.offset_manager == self.offset_manager
        assert self.service.redis_sse_service == self.redis_sse_service
        assert self.service.event_filter == self.event_filter
        assert self.service.circuit_breaker == self.circuit_breaker
        assert self.service.publisher == self.publisher
        assert self.service.metrics_collector == self.metrics_collector
        assert self.service.consumer is None  # Initially no consumer

    def test_set_consumer_reference(self):
        """Test setting consumer reference for offset management."""
        # Initially no consumer
        assert self.service.consumer is None

        # Set consumer
        mock_consumer = Mock()
        self.service.set_consumer(mock_consumer)

        # Verify consumer is set
        assert self.service.consumer == mock_consumer

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration_on_first_message(self):
        """Test circuit breaker integrates with consumer on first message processing."""
        # Set up consumer with partitions
        mock_consumer = Mock()
        mock_partitions = [Mock(), Mock()]
        mock_consumer.assignment.return_value = mock_partitions

        self.service.set_consumer(mock_consumer)

        # Create valid message
        valid_message = Mock()
        valid_message.value = self._create_valid_event_value()
        valid_message.topic = "genesis.session.events"
        valid_message.partition = 0
        valid_message.offset = 123

        # Mock successful Redis publish
        self.redis_sse_service.publish_event = AsyncMock(return_value="stream-id-123")

        # Mock circuit breaker register method
        self.circuit_breaker.register_consumer = Mock()

        # Process first message - should trigger circuit breaker integration
        result = await self.service._process_event(valid_message)

        assert result is True
        # Verify circuit breaker was registered with consumer and partitions
        self.circuit_breaker.register_consumer.assert_called_once_with(mock_consumer, mock_partitions)

        # Process second message - should not register again
        await self.service._process_event(valid_message)
        # Still only called once
        assert self.circuit_breaker.register_consumer.call_count == 1

    @pytest.mark.asyncio
    async def test_offset_recording_on_successful_processing(self):
        """Test offset is recorded for successfully processed messages."""
        # Set consumer reference
        mock_consumer = Mock()
        self.service.set_consumer(mock_consumer)

        # Create valid message
        valid_message = Mock()
        valid_message.value = self._create_valid_event_value()
        valid_message.topic = "genesis.session.events"
        valid_message.partition = 0
        valid_message.offset = 123

        # Mock successful Redis publish
        self.redis_sse_service.publish_event = AsyncMock(return_value="stream-id-123")

        # Process message
        result = await self.service._process_event(valid_message)

        assert result is True
        # Verify offset was recorded
        self.offset_manager.record_offset_and_maybe_commit.assert_called_once_with(mock_consumer, valid_message)

    @pytest.mark.asyncio
    async def test_event_bridge_shutdown_cleanup(self):
        """Test event bridge cleans up resources on shutdown."""
        # Mock cleanup methods
        self.kafka_client_manager.stop_consumer = Mock()
        self.redis_sse_service.close = AsyncMock()

        await self.service.shutdown()

        # Set consumer reference for proper shutdown
        self.service.set_consumer(self.consumer)

        await self.service.shutdown()

        # Verify cleanup was called
        self.offset_manager.flush_pending_offsets.assert_called_with(
            self.consumer
        )  # Flush pending offsets with consumer
        self.kafka_client_manager.stop_consumer.assert_called()
        self.redis_sse_service.close.assert_called()

    def _create_valid_event_value(self) -> dict:
        """Helper to create valid event value."""
        return {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
            },
        }
