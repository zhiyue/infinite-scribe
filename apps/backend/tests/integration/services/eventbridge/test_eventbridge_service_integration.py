"""
Integration tests for EventBridge service.

Tests the full EventBridge service integration and startup process.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.core.config import get_settings
from src.services.eventbridge import create_event_bridge_service, get_event_bridge_factory
from src.services.eventbridge.factory import EventBridgeServiceFactory
from src.services.eventbridge.main import EventBridgeApplication


class TestEventBridgeIntegration:
    """Test EventBridge service integration."""

    def test_service_factory_creation(self):
        """Test EventBridge service can be created through factory."""
        # This test verifies the dependency injection works correctly
        service = create_event_bridge_service()

        assert service is not None
        assert hasattr(service, "kafka_client_manager")
        assert hasattr(service, "offset_manager")
        assert hasattr(service, "redis_sse_service")
        assert hasattr(service, "event_filter")
        assert hasattr(service, "circuit_breaker")
        assert hasattr(service, "publisher")

    def test_factory_configuration(self):
        """Test factory uses proper configuration."""
        get_event_bridge_factory()
        settings = get_settings()
        config = settings.eventbridge

        assert config is not None
        assert "genesis.session.events" in config.domain_topics
        assert config.cb_fail_rate_threshold == 0.5

    def test_factory_health_status(self):
        """Test factory health status reporting."""
        # Create a new factory to avoid pollution from other tests
        from src.services.eventbridge.factory import EventBridgeServiceFactory

        factory = EventBridgeServiceFactory()

        # Before creating service
        health = factory.get_health_status()
        assert health["factory_initialized"] is True
        assert health["services"] == {}

        # After creating service
        factory.create_event_bridge_service()
        health = factory.get_health_status()
        assert "bridge" in health["services"]

    @pytest.mark.asyncio
    async def test_application_initialization(self):
        """Test EventBridge application can initialize without external dependencies."""
        # Mock external dependencies to avoid requiring Kafka/Redis for unit tests

        with (
            patch("src.services.eventbridge.factory.KafkaClientManager") as mock_kafka,
            patch("src.services.eventbridge.factory.RedisService") as mock_redis,
            patch("src.services.sse.redis_client.RedisSSEService") as mock_sse,
        ):
            # Setup mocks
            mock_consumer = Mock()
            mock_kafka.return_value.create_consumer.return_value = mock_consumer
            mock_redis.return_value = Mock()
            mock_sse.return_value.init_pubsub_client = AsyncMock()

            # Create application
            app = EventBridgeApplication()

            # Test initialization
            await app._initialize_service()

            # Verify service was created
            assert app.bridge_service is not None

            # Test cleanup
            await app._cleanup()

    def test_eventbridge_config_integration(self):
        """Test EventBridge config integrates with settings."""
        settings = get_settings()
        config = settings.eventbridge

        # Test default values exist
        assert "genesis.session.events" in config.domain_topics
        assert config.cb_fail_rate_threshold == 0.5
        assert config.commit_interval_ms == 5000
        assert config.commit_batch_size == 100

    def test_all_components_are_importable(self):
        """Test all EventBridge components can be imported successfully."""
        # This test ensures all components are properly structured and dependencies are met

        from src.services.eventbridge import create_event_bridge_service, get_event_bridge_factory
        from src.services.eventbridge.bridge import DomainEventBridgeService
        from src.services.eventbridge.circuit_breaker import CircuitBreaker, CircuitState
        from src.services.eventbridge.filter import EventFilter
        from src.services.eventbridge.publisher import Publisher

        # Verify classes can be instantiated (with proper dependencies)
        assert DomainEventBridgeService is not None
        assert EventFilter is not None
        assert CircuitBreaker is not None
        assert CircuitState is not None
        assert Publisher is not None

        # Verify factory functions work
        assert callable(create_event_bridge_service)
        assert callable(get_event_bridge_factory)

    @pytest.mark.asyncio
    async def test_service_shutdown_sequence(self):
        """Test the complete service shutdown sequence works correctly."""

        with (
            patch("src.services.eventbridge.factory.KafkaClientManager") as mock_kafka,
            patch("src.services.eventbridge.factory.RedisService") as mock_redis,
        ):
            # Setup mocks
            mock_kafka_instance = Mock()
            mock_kafka_instance.stop_consumer = AsyncMock()
            mock_kafka_instance.stop_all = Mock()
            mock_kafka.return_value = mock_kafka_instance

            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance

            # Create factory and service
            factory = EventBridgeServiceFactory()
            service = factory.create_event_bridge_service()

            # Test shutdown sequence
            await service.shutdown()
            await factory.cleanup()

            # Verify cleanup methods were called
            # stop_consumer may be called multiple times (bridge shutdown + factory cleanup)
            assert mock_kafka_instance.stop_consumer.call_count >= 1
            mock_kafka_instance.stop_all.assert_called_once()

    def test_service_component_integration(self):
        """Test all service components integrate correctly."""
        service = create_event_bridge_service()

        # Test that all components are properly injected
        assert service.event_filter is not None
        assert service.circuit_breaker is not None
        assert service.publisher is not None
        assert service.kafka_client_manager is not None
        assert service.offset_manager is not None
        assert service.redis_sse_service is not None

        # Test health status works
        health = service.get_health_status()
        assert "healthy" in health
        assert "circuit_state" in health
        assert "failure_rate" in health
        assert "events_consumed" in health
