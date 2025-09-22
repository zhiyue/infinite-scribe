"""
Unit tests for OutboxEgress store_event fix.

Tests that the data structure compatibility issue between OutboxEgress and EventBridge is resolved.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.services.outbox.egress import OutboxEgress


class TestOutboxEgressFix:
    """Test OutboxEgress store_event fix for EventBridge compatibility."""

    @pytest.mark.asyncio
    async def test_store_event_creates_eventbridge_compatible_structure(self):
        """Test that store_event creates EventBridge-compatible flat structure."""
        # Create test event
        event_data = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "timestamp": datetime.now().isoformat(),
            "source": "api-gateway",
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "content": {"action": "session_started"},
            },
            "metadata": {
                "topic": "genesis.session.events",
                "correlation_id": str(uuid4()),
            },
        }

        # Mock database operations
        mock_outbox = AsyncMock()
        mock_session = AsyncMock()
        mock_session.add = AsyncMock()
        mock_session.flush = AsyncMock()

        with (
            patch('src.services.outbox.egress.create_sql_session') as mock_create_session,
            patch('src.services.outbox.egress.EventOutbox') as mock_outbox_class,
        ):
            mock_create_session.return_value.__aenter__.return_value = mock_session
            mock_outbox_class.return_value = mock_outbox
            mock_outbox.id = "test-id"

            egress = OutboxEgress()
            result = await egress.store_event(event_data)

            assert result is True

            # Verify EventOutbox was called with correct arguments
            mock_outbox_class.assert_called_once()
            call_kwargs = mock_outbox_class.call_args.kwargs

            # Check payload structure
            payload = call_kwargs["payload"]
            assert isinstance(payload, dict)

            # Verify EventBridge-compatible flat structure
            assert "event_id" in payload
            assert "event_type" in payload
            assert "aggregate_id" in payload
            assert "correlation_id" in payload
            assert "payload" in payload

            # Verify it's NOT the old nested Envelope structure
            assert "data" not in payload, "Should not have Envelope 'data' field"
            assert "id" not in payload, "Should not have Envelope 'id' field"
            assert "ts" not in payload, "Should not have Envelope 'ts' field"
            assert "type" not in payload, "Should not have Envelope 'type' field"
            assert "version" not in payload, "Should not have Envelope 'version' field"
            assert "agent" not in payload, "Should not have Envelope 'agent' field"
            assert "retries" not in payload, "Should not have Envelope 'retries' field"
            assert "status" not in payload, "Should not have Envelope 'status' field"

            # Verify values are correct
            assert payload["event_id"] == event_data["event_id"]
            assert payload["event_type"] == event_data["event_type"]
            assert payload["aggregate_id"] == event_data["aggregate_id"]
            assert payload["correlation_id"] == event_data["correlation_id"]
            assert payload["payload"] == event_data["payload"]

    @pytest.mark.asyncio
    async def test_store_event_handles_none_aggregate_id(self):
        """Test that store_event properly handles None aggregate_id without string conversion."""
        # Create test event with None aggregate_id
        event_data = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": None,  # None value
            "correlation_id": str(uuid4()),
            "timestamp": datetime.now().isoformat(),
            "source": "api-gateway",
            "payload": {"user_id": str(uuid4())},
            "metadata": {"topic": "genesis.session.events"},
        }

        # Mock database operations
        mock_outbox = AsyncMock()
        mock_session = AsyncMock()

        with (
            patch('src.services.outbox.egress.create_sql_session') as mock_create_session,
            patch('src.services.outbox.egress.EventOutbox') as mock_outbox_class,
        ):
            mock_create_session.return_value.__aenter__.return_value = mock_session
            mock_outbox_class.return_value = mock_outbox
            mock_outbox.id = "test-id"

            egress = OutboxEgress()
            result = await egress.store_event(event_data)

            assert result is True

            # Verify EventOutbox was called with correct arguments
            call_kwargs = mock_outbox_class.call_args.kwargs

            # Check that key and partition_key are None, not string "None"
            assert call_kwargs["key"] is None, "Key should be None, not string 'None'"
            assert call_kwargs["partition_key"] is None, "Partition key should be None, not string 'None'"

            # Check that payload aggregate_id is None
            payload = call_kwargs["payload"]
            assert payload["aggregate_id"] is None, "Payload aggregate_id should be None"

    @pytest.mark.asyncio
    async def test_store_event_does_not_use_encode_message(self):
        """Test that store_event no longer uses encode_message which creates Envelope structure."""
        event_data = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": {"user_id": str(uuid4())},
            "metadata": {"topic": "genesis.session.events"},
        }

        # Mock database operations
        mock_session = AsyncMock()

        with (
            patch('src.services.outbox.egress.create_sql_session') as mock_create_session,
            patch('src.services.outbox.egress.EventOutbox') as mock_outbox_class,
            patch('src.services.outbox.egress.encode_message') as mock_encode_message,
        ):
            mock_create_session.return_value.__aenter__.return_value = mock_session
            mock_outbox_class.return_value.id = "test-id"

            egress = OutboxEgress()
            await egress.store_event(event_data)

            # Verify encode_message was NOT called
            mock_encode_message.assert_not_called()

            # Verify we create EventBridge-compatible structure directly
            call_kwargs = mock_outbox_class.call_args.kwargs
            payload = call_kwargs["payload"]

            # Should have EventBridge required fields at top level
            required_fields = ["event_id", "event_type", "aggregate_id", "correlation_id", "payload"]
            for field in required_fields:
                assert field in payload, f"Required field '{field}' should be at top level"