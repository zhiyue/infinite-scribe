"""Unit tests for event publisher service."""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.common.services.event_publisher import EventPublisherService
from src.models.db import OutboxStatus


@pytest.fixture
def event_publisher():
    """Create event publisher instance."""
    return EventPublisherService()


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock()


class TestEventPayloadValidation:
    """Test event payload validation."""
    
    def test_validate_event_payload_valid(self, event_publisher):
        """Test validation of valid event payload."""
        valid_payload = {
            'event_id': str(uuid4()),
            'correlation_id': str(uuid4()),
            'causation_id': str(uuid4()),
            'event_type': 'Genesis.Session.Created',
            'aggregate_type': 'GENESIS_SESSION',
            'aggregate_id': str(uuid4()),
            'payload': {'test': 'data'},
            'metadata': {'user_id': 'test-user'}
        }
        
        # Should not raise any exception
        event_publisher._validate_event_payload(valid_payload)
    
    def test_validate_event_payload_missing_fields(self, event_publisher):
        """Test validation with missing required fields."""
        invalid_payload = {
            'event_id': str(uuid4()),
            # missing other required fields
        }
        
        with pytest.raises(ValueError) as exc_info:
            event_publisher._validate_event_payload(invalid_payload)
        
        assert "missing required fields" in str(exc_info.value)
    
    def test_validate_event_payload_invalid_type(self, event_publisher):
        """Test validation with invalid payload type."""
        with pytest.raises(ValueError) as exc_info:
            event_publisher._validate_event_payload("not a dict")
        
        assert "must be a dictionary" in str(exc_info.value)
    
    def test_validate_event_payload_invalid_event_id_type(self, event_publisher):
        """Test validation with invalid event_id type."""
        invalid_payload = {
            'event_id': 123,  # should be string
            'correlation_id': str(uuid4()),
            'causation_id': str(uuid4()),
            'event_type': 'Test.Event',
            'aggregate_type': 'TEST',
            'aggregate_id': str(uuid4()),
        }
        
        with pytest.raises(ValueError) as exc_info:
            event_publisher._validate_event_payload(invalid_payload)
        
        assert "event_id must be a string" in str(exc_info.value)
    
    def test_validate_event_payload_invalid_correlation_id_type(self, event_publisher):
        """Test validation with invalid correlation_id type."""
        invalid_payload = {
            'event_id': str(uuid4()),
            'correlation_id': 123,  # should be string or None
            'causation_id': str(uuid4()),
            'event_type': 'Test.Event',
            'aggregate_type': 'TEST',
            'aggregate_id': str(uuid4()),
        }
        
        with pytest.raises(ValueError) as exc_info:
            event_publisher._validate_event_payload(invalid_payload)
        
        assert "correlation_id must be a string or None" in str(exc_info.value)
    
    def test_validate_event_payload_null_correlation_id(self, event_publisher):
        """Test validation with null correlation_id (should be valid)."""
        valid_payload = {
            'event_id': str(uuid4()),
            'correlation_id': None,  # this is valid
            'causation_id': str(uuid4()),
            'event_type': 'Test.Event',
            'aggregate_type': 'TEST',
            'aggregate_id': str(uuid4()),
        }
        
        # Should not raise any exception
        event_publisher._validate_event_payload(valid_payload)


class TestSaveToOutbox:
    """Test save_to_outbox functionality."""
    
    @pytest.mark.asyncio
    async def test_save_to_outbox_success(self, event_publisher, mock_db):
        """Test successful save to outbox."""
        # Setup
        topic = "domain-events"
        key = str(uuid4())
        payload = {
            'event_id': str(uuid4()),
            'correlation_id': str(uuid4()),
            'causation_id': str(uuid4()),
            'event_type': 'Genesis.Session.Created',
            'aggregate_type': 'GENESIS_SESSION',
            'aggregate_id': key,
        }
        headers = {'content-type': 'application/json'}
        
        # Execute
        outbox_id = await event_publisher.save_to_outbox(
            topic=topic,
            key=key,
            payload=payload,
            db=mock_db,
            headers=headers
        )
        
        # Verify
        assert outbox_id is not None
        mock_db.execute.assert_called_once()
        
        # Check database call
        call_args = mock_db.execute.call_args
        sql = str(call_args[0][0])
        assert "INSERT INTO event_outbox" in sql
        
        params = call_args[1]
        assert params['topic'] == topic
        assert params['key'] == key
        assert params['partition_key'] == key
        assert json.loads(params['payload']) == payload
        assert json.loads(params['headers']) == headers
        assert params['status'] == OutboxStatus.PENDING.value
    
    @pytest.mark.asyncio
    async def test_save_to_outbox_invalid_payload(self, event_publisher, mock_db):
        """Test save to outbox with invalid payload."""
        # Setup
        topic = "domain-events"
        key = str(uuid4())
        invalid_payload = {"missing": "required_fields"}
        
        # Execute and verify exception
        with pytest.raises(ValueError):
            await event_publisher.save_to_outbox(
                topic=topic,
                key=key,
                payload=invalid_payload,
                db=mock_db
            )
        
        # Verify database was not called
        mock_db.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_save_to_outbox_without_headers(self, event_publisher, mock_db):
        """Test save to outbox without headers."""
        # Setup
        topic = "domain-events"
        key = str(uuid4())
        payload = {
            'event_id': str(uuid4()),
            'correlation_id': str(uuid4()),
            'causation_id': str(uuid4()),
            'event_type': 'Genesis.Session.Created',
            'aggregate_type': 'GENESIS_SESSION',
            'aggregate_id': key,
        }
        
        # Execute
        outbox_id = await event_publisher.save_to_outbox(
            topic=topic,
            key=key,
            payload=payload,
            db=mock_db
        )
        
        # Verify
        assert outbox_id is not None
        
        # Check database call
        call_args = mock_db.execute.call_args
        params = call_args[1]
        assert params['headers'] is None


class TestPublishDomainEvent:
    """Test publish_domain_event functionality."""
    
    @pytest.mark.asyncio
    @patch.object(EventPublisherService, 'save_to_outbox')
    async def test_publish_domain_event_success(
        self, mock_save_to_outbox, event_publisher, mock_db
    ):
        """Test successful domain event publishing."""
        # Setup
        outbox_id = uuid4()
        mock_save_to_outbox.return_value = outbox_id
        
        event_type = "Genesis.Session.Created"
        aggregate_type = "GENESIS_SESSION"
        aggregate_id = str(uuid4())
        payload = {"session_data": "test"}
        correlation_id = str(uuid4())
        causation_id = str(uuid4())
        metadata = {"user_id": "test-user"}
        
        # Execute
        result = await event_publisher.publish_domain_event(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            correlation_id=correlation_id,
            causation_id=causation_id,
            metadata=metadata,
            db=mock_db
        )
        
        # Verify
        assert result == outbox_id
        mock_save_to_outbox.assert_called_once()
        
        # Check the constructed event payload
        call_args = mock_save_to_outbox.call_args
        event_payload = call_args[1]['payload']
        
        assert event_payload['event_type'] == event_type
        assert event_payload['aggregate_type'] == aggregate_type
        assert event_payload['aggregate_id'] == aggregate_id
        assert event_payload['payload'] == payload
        assert event_payload['correlation_id'] == correlation_id
        assert event_payload['causation_id'] == causation_id
        assert event_payload['metadata'] == metadata
        assert event_payload['event_version'] == 1
        assert 'event_id' in event_payload
        assert 'created_at' in event_payload
    
    @pytest.mark.asyncio
    @patch.object(EventPublisherService, 'save_to_outbox')
    async def test_publish_domain_event_minimal(
        self, mock_save_to_outbox, event_publisher, mock_db
    ):
        """Test domain event publishing with minimal parameters."""
        # Setup
        outbox_id = uuid4()
        mock_save_to_outbox.return_value = outbox_id
        
        event_type = "Genesis.Session.Created"
        aggregate_type = "GENESIS_SESSION"
        aggregate_id = str(uuid4())
        payload = {"session_data": "test"}
        
        # Execute
        result = await event_publisher.publish_domain_event(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            db=mock_db
        )
        
        # Verify
        assert result == outbox_id
        mock_save_to_outbox.assert_called_once()
        
        # Check the constructed event payload
        call_args = mock_save_to_outbox.call_args
        event_payload = call_args[1]['payload']
        
        assert event_payload['correlation_id'] is None
        assert event_payload['causation_id'] is None
        assert event_payload['metadata'] == {}
    
    @pytest.mark.asyncio
    @patch.object(EventPublisherService, 'save_to_outbox')
    async def test_publish_domain_event_uses_correct_topic(
        self, mock_save_to_outbox, event_publisher, mock_db
    ):
        """Test that domain event publishing uses the correct topic."""
        # Setup
        mock_save_to_outbox.return_value = uuid4()
        
        # Execute
        await event_publisher.publish_domain_event(
            event_type="Test.Event",
            aggregate_type="TEST",
            aggregate_id=str(uuid4()),
            payload={},
            db=mock_db
        )
        
        # Verify correct topic is used
        call_args = mock_save_to_outbox.call_args
        assert call_args[1]['topic'] == "domain-events"
        
        # Verify correct headers are set
        assert call_args[1]['headers'] == {'content-type': 'application/json'}