"""
Unit tests for Publisher component.

Tests the event publishing and transformation logic for EventBridge.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from src.schemas.sse import EventScope, SSEMessage
from src.services.eventbridge.publisher import Publisher


class TestPublisher:
    """Test Publisher component for transforming and publishing events."""

    def setup_method(self):
        """Setup test fixtures."""
        self.redis_sse_service = Mock()
        self.redis_sse_service.publish_event = AsyncMock()
        self.publisher = Publisher(self.redis_sse_service)

    @pytest.mark.asyncio
    async def test_publisher_transforms_envelope_to_sse_message(self):
        """Test Publisher transforms Kafka envelope to SSEMessage format."""
        envelope = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Theme.Proposed",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "metadata": {"trace_id": str(uuid4())},
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "novel_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "content": {"theme": "Fantasy Adventure", "summary": "Epic quest"},
            },
        }

        # Mock successful Redis publish
        self.redis_sse_service.publish_event.return_value = "stream-id-123"

        result = await self.publisher.publish(envelope)

        # Verify publish was called
        assert self.redis_sse_service.publish_event.called
        args = self.redis_sse_service.publish_event.call_args

        user_id = args[0][0]
        sse_message = args[0][1]

        # Verify user_id extraction
        assert user_id == envelope["payload"]["user_id"]

        # Verify SSEMessage structure
        assert isinstance(sse_message, SSEMessage)
        assert sse_message.event == envelope["event_type"]
        assert sse_message.scope == EventScope.USER
        assert result == "stream-id-123"

    @pytest.mark.asyncio
    async def test_publisher_trims_data_for_minimal_set(self):
        """Test Publisher creates minimal data set for SSE transmission."""
        large_envelope = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Character.Confirmed",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "metadata": {"trace_id": str(uuid4()), "extra_field": "should_be_excluded"},
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "novel_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "content": {
                    "character": {"name": "Hero", "age": 25, "background": "...long text..."},
                    "large_data": "x" * 10000,  # Large data that should be trimmed
                },
                "internal_processing_data": "should_not_be_in_sse",
            },
        }

        self.redis_sse_service.publish_event.return_value = "stream-id-456"

        await self.publisher.publish(large_envelope)

        # Get the SSEMessage that was published
        sse_message = self.redis_sse_service.publish_event.call_args[0][1]

        # Verify minimal data set contains required fields
        required_fields = {
            "event_id",
            "event_type",
            "session_id",
            "novel_id",
            "correlation_id",
            "timestamp",
        }

        for field in required_fields:
            assert field in sse_message.data

        # Verify trace_id is included if present
        assert "trace_id" in sse_message.data

        # Verify payload content is preserved but might be summarized
        assert "payload" in sse_message.data

    @pytest.mark.asyncio
    async def test_publisher_routes_by_user_id(self):
        """Test Publisher routes events to correct user_id."""
        user_id_1 = str(uuid4())
        user_id_2 = str(uuid4())

        envelope_1 = self._create_test_envelope(user_id_1)
        envelope_2 = self._create_test_envelope(user_id_2)

        self.redis_sse_service.publish_event.return_value = "stream-id"

        await self.publisher.publish(envelope_1)
        await self.publisher.publish(envelope_2)

        # Verify both publishes happened with correct user_ids
        assert self.redis_sse_service.publish_event.call_count == 2

        calls = self.redis_sse_service.publish_event.call_args_list
        published_user_ids = [call[0][0] for call in calls]

        assert user_id_1 in published_user_ids
        assert user_id_2 in published_user_ids

    @pytest.mark.asyncio
    async def test_publisher_handles_redis_failures(self):
        """Test Publisher handles Redis publishing failures gracefully."""
        envelope = self._create_test_envelope()

        # Mock Redis failure
        self.redis_sse_service.publish_event.side_effect = ConnectionError("Redis connection failed")

        with pytest.raises(ConnectionError) as exc_info:
            await self.publisher.publish(envelope)

        assert "Redis connection failed" in str(exc_info.value)
        assert self.redis_sse_service.publish_event.called

    @pytest.mark.asyncio
    async def test_publisher_handles_missing_user_id(self):
        """Test Publisher handles missing user_id in payload."""
        envelope = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": {
                "session_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                # Missing user_id
            },
        }

        with pytest.raises(ValueError) as exc_info:
            await self.publisher.publish(envelope)

        assert "user_id is required" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_publisher_preserves_correlation_and_trace_ids(self):
        """Test Publisher preserves correlation_id and trace_id for tracking."""
        correlation_id = str(uuid4())
        trace_id = str(uuid4())

        envelope = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Plot.Updated",
            "aggregate_id": str(uuid4()),
            "correlation_id": correlation_id,
            "metadata": {"trace_id": trace_id},
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "content": {"plot": "Updated plot points"},
            },
        }

        self.redis_sse_service.publish_event.return_value = "stream-id"

        await self.publisher.publish(envelope)

        sse_message = self.redis_sse_service.publish_event.call_args[0][1]

        assert sse_message.data["correlation_id"] == correlation_id
        assert sse_message.data["trace_id"] == trace_id

    @pytest.mark.asyncio
    async def test_publisher_handles_optional_fields(self):
        """Test Publisher handles optional fields gracefully."""
        # Envelope without novel_id and trace_id
        envelope = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                # novel_id is optional
            },
        }

        self.redis_sse_service.publish_event.return_value = "stream-id"

        await self.publisher.publish(envelope)

        sse_message = self.redis_sse_service.publish_event.call_args[0][1]

        # Should not have novel_id since it wasn't provided
        assert "novel_id" not in sse_message.data or sse_message.data["novel_id"] is None
        # Should not have trace_id since metadata wasn't provided
        assert "trace_id" not in sse_message.data or sse_message.data["trace_id"] is None

    @pytest.mark.asyncio
    async def test_publisher_returns_stream_id(self):
        """Test Publisher returns the stream ID from Redis."""
        envelope = self._create_test_envelope()
        expected_stream_id = "test-stream-123"

        self.redis_sse_service.publish_event.return_value = expected_stream_id

        result = await self.publisher.publish(envelope)

        assert result == expected_stream_id

    def _create_test_envelope(self, user_id: str | None = None) -> dict:
        """Helper to create test envelope."""
        return {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Test.Event",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "metadata": {"trace_id": str(uuid4())},
            "payload": {
                "user_id": user_id or str(uuid4()),
                "session_id": str(uuid4()),
                "novel_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "content": {"test": "data"},
            },
        }
