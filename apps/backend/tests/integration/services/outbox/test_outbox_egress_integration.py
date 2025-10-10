"""
Integration test for OutboxEgress store_event fix.

Tests the complete outbox storage functionality using real database
to ensure the data structure compatibility issue is resolved.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.workflow import EventOutbox
from src.services.outbox.egress import OutboxEgress


@pytest.mark.integration
class TestOutboxEgressIntegration:
    """Integration test for OutboxEgress store_event fix."""

    @pytest.mark.asyncio
    async def test_store_event_creates_eventbridge_compatible_structure_in_db(self, db_session: AsyncSession):
        """Test that store_event creates EventBridge-compatible structure in real database."""
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

        # Store event using OutboxEgress
        egress = OutboxEgress()
        result = await egress.store_event(event_data)
        assert result is True

        # Verify event was stored in database with correct structure
        stmt = select(EventOutbox).order_by(EventOutbox.created_at.desc()).limit(1)
        result = await db_session.execute(stmt)
        outbox_row = result.scalar_one_or_none()

        assert outbox_row is not None, "Event should be stored in outbox"
        assert outbox_row.topic == "genesis.session.events"

        # Verify the payload has EventBridge-compatible structure
        payload = outbox_row.payload
        assert isinstance(payload, dict), "Payload should be a dict"

        # Check required EventBridge fields are at top level
        assert "event_id" in payload, "event_id should be at top level"
        assert "event_type" in payload, "event_type should be at top level"
        assert "aggregate_id" in payload, "aggregate_id should be at top level"
        assert "correlation_id" in payload, "correlation_id should be at top level"
        assert "payload" in payload, "payload should be at top level"

        # Verify it's NOT the old nested Envelope structure
        assert "data" not in payload, "Should not have Envelope 'data' field"
        assert "id" not in payload, "Should not have Envelope 'id' field"
        assert "ts" not in payload, "Should not have Envelope 'ts' field"
        assert "type" not in payload, "Should not have Envelope 'type' field"

        # Verify values are correct
        assert payload["event_id"] == event_data["event_id"]
        assert payload["event_type"] == event_data["event_type"]
        assert payload["aggregate_id"] == event_data["aggregate_id"]
        # correlation_id can come from top level or metadata
        assert payload["correlation_id"] in [
            event_data["correlation_id"],
            event_data["metadata"]["correlation_id"]
        ]
        assert payload["payload"] == event_data["payload"]

        print(f"✓ OutboxEgress stored event with correct structure: {list(payload.keys())}")

    @pytest.mark.asyncio
    async def test_store_event_handles_none_aggregate_id_in_db(self, db_session: AsyncSession):
        """Test that store_event properly handles None aggregate_id in real database."""
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

        # Store event using OutboxEgress
        egress = OutboxEgress()
        result = await egress.store_event(event_data)
        assert result is True

        # Verify in database
        stmt = select(EventOutbox).order_by(EventOutbox.created_at.desc()).limit(1)
        result = await db_session.execute(stmt)
        outbox_row = result.scalar_one_or_none()

        assert outbox_row is not None
        assert outbox_row.key is None, "Key should be None, not string 'None'"
        assert outbox_row.partition_key is None, "Partition key should be None, not string 'None'"
        assert outbox_row.payload["aggregate_id"] is None, "Payload aggregate_id should be None"

        print("✓ Aggregate ID None handling verified in database - no string conversion")

    @pytest.mark.asyncio
    async def test_multiple_events_storage(self, db_session: AsyncSession):
        """Test storing multiple events to verify consistency."""
        events = []
        for i in range(3):
            event_data = {
                "event_id": str(uuid4()),
                "event_type": f"Genesis.Session.Event{i}",
                "aggregate_id": str(uuid4()) if i % 2 == 0 else None,  # Mix of None and non-None
                "correlation_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "source": "api-gateway",
                "payload": {"index": i, "user_id": str(uuid4())},
                "metadata": {"topic": "genesis.session.events"},
            }
            events.append(event_data)

        # Store all events
        egress = OutboxEgress()
        for event_data in events:
            result = await egress.store_event(event_data)
            assert result is True

        # Verify all events were stored correctly
        stmt = select(EventOutbox).order_by(EventOutbox.created_at.desc()).limit(3)
        result = await db_session.execute(stmt)
        stored_rows = result.scalars().all()

        assert len(stored_rows) == 3

        # Verify structure for each stored event
        for i, row in enumerate(reversed(stored_rows)):  # Reverse to match original order
            payload = row.payload

            # All should have EventBridge-compatible structure
            assert "event_id" in payload
            assert "event_type" in payload
            assert "aggregate_id" in payload
            assert "correlation_id" in payload
            assert "payload" in payload

            # Verify values match original events
            original_event = events[i]
            assert payload["event_id"] == original_event["event_id"]
            assert payload["event_type"] == original_event["event_type"]
            assert payload["aggregate_id"] == original_event["aggregate_id"]
            assert payload["payload"]["index"] == i

            # Check partition key handling
            if original_event["aggregate_id"] is None:
                assert row.key is None
                assert row.partition_key is None
            else:
                assert row.key == str(original_event["aggregate_id"])
                assert row.partition_key == str(original_event["aggregate_id"])

        print(f"✓ Successfully stored and verified {len(events)} events with correct structure")