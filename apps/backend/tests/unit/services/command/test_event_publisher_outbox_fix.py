"""Unit tests for EventBridgePublisher outbox configuration fix."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.services.command.event_publisher import EventBridgePublisher
from src.services.outbox.egress import OutboxEgress


class TestEventBridgePublisherOutboxFix:
    """Test EventBridgePublisher outbox service configuration fix."""

    @pytest.fixture
    def mock_outbox_service(self):
        """Create mock outbox service."""
        outbox = Mock(spec=OutboxEgress)
        outbox.store_event = AsyncMock(return_value=True)
        return outbox

    async def test_publisher_with_outbox_service_calls_store_event(self, mock_outbox_service):
        """Test that publisher with outbox service calls store_event method."""
        publisher = EventBridgePublisher(event_outbox_service=mock_outbox_service)

        event = {
            "event_id": "test-event-123",
            "event_type": "Command.Completed",
            "aggregate_id": "session-456",
            "aggregate_type": "Session",
            "source": "api-gateway",
            "metadata": {
                "correlation_id": "corr-789",
                "topic": "genesis.session.events"
            },
            "payload": {"status": "completed"}
        }

        result = await publisher.publish_event(event)

        assert result is True
        mock_outbox_service.store_event.assert_called_once()

        # Verify the event passed contains our original data plus enrichment
        called_event = mock_outbox_service.store_event.call_args[0][0]
        assert called_event["event_id"] == event["event_id"]
        assert called_event["event_type"] == event["event_type"]
        assert called_event["aggregate_id"] == event["aggregate_id"]
        assert called_event["source"] == event["source"]
        assert called_event["payload"] == event["payload"]
        # Verify enrichment happened
        assert "timestamp" in called_event
        assert "version" in called_event

    async def test_publisher_without_outbox_service_uses_direct_publish(self):
        """Test that publisher without outbox service uses direct publish (fallback)."""
        publisher = EventBridgePublisher()  # No outbox service provided

        event = {
            "event_id": "test-event-123",
            "event_type": "Command.Completed",
            "aggregate_id": "session-456",
            "source": "api-gateway"
        }

        # Since direct publish only logs, we just verify it doesn't fail
        result = await publisher.publish_event(event)

        # Direct publish should succeed (it's just logging)
        assert result is True

    async def test_outbox_service_store_event_handles_event_data(self):
        """Test that OutboxEgress.store_event properly handles event data."""
        outbox = OutboxEgress()

        # Mock the enqueue_envelope method
        with patch.object(outbox, 'enqueue_envelope', new_callable=AsyncMock) as mock_enqueue:
            mock_enqueue.return_value = "outbox-id-123"

            event = {
                "event_id": "test-event-123",
                "event_type": "Command.Completed",
                "aggregate_id": "session-456",
                "aggregate_type": "Session",
                "source": "api-gateway",
                "metadata": {
                    "correlation_id": "corr-789",
                    "topic": "genesis.session.events"
                },
                "payload": {"status": "completed"}
            }

            result = await outbox.store_event(event)

            assert result is True
            mock_enqueue.assert_called_once()

            # Verify the enqueue_envelope was called with correct parameters
            call_args = mock_enqueue.call_args[1]
            assert call_args["agent"] == "api-gateway"
            assert call_args["topic"] == "genesis.session.events"
            assert call_args["key"] == "session-456"
            assert call_args["correlation_id"] == "corr-789"

            # Verify result structure
            result_data = call_args["result"]
            assert result_data["type"] == "Command.Completed"  # Required for encode_message
            assert result_data["event_id"] == "test-event-123"
            assert result_data["event_type"] == "Command.Completed"
            assert result_data["aggregate_id"] == "session-456"

    async def test_outbox_service_store_event_with_defaults(self):
        """Test OutboxEgress.store_event with minimal event data."""
        outbox = OutboxEgress()

        with patch.object(outbox, 'enqueue_envelope', new_callable=AsyncMock) as mock_enqueue:
            mock_enqueue.return_value = "outbox-id-456"

            event = {
                "event_id": "minimal-event",
                "event_type": "Command.Started",
                "aggregate_id": "session-123"
            }

            result = await outbox.store_event(event)

            assert result is True
            mock_enqueue.assert_called_once()

            call_args = mock_enqueue.call_args[1]
            assert call_args["agent"] == "api-gateway"  # Default
            assert call_args["topic"] == "genesis.session.events"  # Default
            assert call_args["key"] == "session-123"
            assert call_args["correlation_id"] is None

    async def test_outbox_service_store_event_handles_exception(self):
        """Test OutboxEgress.store_event error handling."""
        outbox = OutboxEgress()

        with patch.object(outbox, 'enqueue_envelope', new_callable=AsyncMock) as mock_enqueue:
            mock_enqueue.side_effect = Exception("Database error")

            event = {
                "event_id": "error-event",
                "event_type": "Command.Failed",
                "aggregate_id": "session-error"
            }

            result = await outbox.store_event(event)

            assert result is False
            mock_enqueue.assert_called_once()

    async def test_publisher_fallback_to_direct_outbox_write(self):
        """Test publisher fallback when outbox service is None but _publish_via_outbox is called."""
        publisher = EventBridgePublisher(event_outbox_service=None)

        event = {
            "event_id": "fallback-event",
            "event_type": "Command.Progress",
            "aggregate_id": "session-fallback",
            "metadata": {"correlation_id": "fallback-corr"}
        }

        # Mock the direct outbox creation
        with patch('src.services.command.event_publisher.create_sql_session') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            with patch('src.services.command.event_publisher.EventOutbox') as mock_outbox_model:
                mock_outbox_instance = Mock()
                mock_outbox_instance.id = "direct-outbox-id"
                mock_outbox_model.return_value = mock_outbox_instance

                result = await publisher._publish_via_outbox(event)

                assert result is True
                mock_db.add.assert_called_once_with(mock_outbox_instance)
                mock_db.flush.assert_called_once()

    def test_publisher_initialization_with_outbox_service(self, mock_outbox_service):
        """Test EventBridgePublisher initialization with outbox service."""
        publisher = EventBridgePublisher(event_outbox_service=mock_outbox_service)

        assert publisher.event_outbox is mock_outbox_service

    def test_publisher_initialization_without_outbox_service(self):
        """Test EventBridgePublisher initialization without outbox service."""
        publisher = EventBridgePublisher()

        assert publisher.event_outbox is None

    async def test_publisher_with_outbox_service_handles_store_failure(self, mock_outbox_service):
        """Test that publisher properly handles store_event returning False."""
        mock_outbox_service.store_event = AsyncMock(return_value=False)
        publisher = EventBridgePublisher(event_outbox_service=mock_outbox_service)

        event = {
            "event_id": "failing-event-123",
            "event_type": "Command.Failed",
            "aggregate_id": "session-789",
            "source": "test-agent"
        }

        result = await publisher.publish_event(event)

        assert result is False
        mock_outbox_service.store_event.assert_called_once()

        # Verify the event passed contains our original data plus enrichment
        called_event = mock_outbox_service.store_event.call_args[0][0]
        assert called_event["event_id"] == event["event_id"]
        assert called_event["event_type"] == event["event_type"]
        assert called_event["aggregate_id"] == event["aggregate_id"]
        assert called_event["source"] == event["source"]