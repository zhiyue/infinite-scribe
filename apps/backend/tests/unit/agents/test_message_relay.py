"""Unit tests for Message Relay service."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.agents.message_relay.main import MessageRelayService


@pytest.fixture
def relay_service():
    """Create message relay service instance."""
    return MessageRelayService()


@pytest.fixture
def mock_kafka_manager():
    """Create mock Kafka manager."""
    return AsyncMock()


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock()


class TestMessageRelayStartStop:
    """Test service start and stop functionality."""
    
    @pytest.mark.asyncio
    @patch('src.agents.message_relay.main.kafka_manager')
    async def test_start_service_success(self, mock_kafka_manager, relay_service):
        """Test successful service start."""
        # Setup
        mock_kafka_manager.start = AsyncMock()
        relay_service._polling_loop = AsyncMock()
        
        # Execute
        await relay_service.start()
        
        # Verify
        mock_kafka_manager.start.assert_called_once()
        assert relay_service.running is True
        relay_service._polling_loop.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.agents.message_relay.main.kafka_manager')
    async def test_start_service_kafka_failure(self, mock_kafka_manager, relay_service):
        """Test service start with Kafka failure."""
        # Setup
        mock_kafka_manager.start = AsyncMock(side_effect=Exception("Kafka error"))
        
        # Execute and verify exception
        with pytest.raises(Exception) as exc_info:
            await relay_service.start()
        
        assert "Kafka error" in str(exc_info.value)
        assert relay_service.running is False
    
    @pytest.mark.asyncio
    @patch('src.agents.message_relay.main.kafka_manager')
    async def test_stop_service(self, mock_kafka_manager, relay_service):
        """Test service stop."""
        # Setup
        relay_service.running = True
        mock_kafka_manager.stop = AsyncMock()
        
        # Execute
        await relay_service.stop()
        
        # Verify
        assert relay_service.running is False
        mock_kafka_manager.stop.assert_called_once()


class TestEventProcessing:
    """Test event processing functionality."""
    
    @pytest.mark.asyncio
    @patch('src.agents.message_relay.main.get_async_session')
    async def test_process_pending_events_success(
        self, mock_get_session, relay_service
    ):
        """Test successful pending events processing."""
        # Setup
        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db
        
        test_events = [
            {
                'id': str(uuid4()),
                'topic': 'domain-events',
                'key': 'test-key',
                'payload': '{"event_type": "test"}',
                'headers': '{"content-type": "application/json"}',
                'retry_count': 0,
                'max_retries': 3
            }
        ]
        
        relay_service._get_pending_events = AsyncMock(return_value=test_events)
        relay_service._publish_event = AsyncMock(return_value=True)
        
        # Execute
        count = await relay_service._process_pending_events()
        
        # Verify
        assert count == 1
        relay_service._get_pending_events.assert_called_once_with(mock_db)
        relay_service._publish_event.assert_called_once_with(test_events[0], mock_db)
    
    @pytest.mark.asyncio
    @patch('src.agents.message_relay.main.get_async_session')
    async def test_process_pending_events_no_events(
        self, mock_get_session, relay_service
    ):
        """Test processing when no pending events."""
        # Setup
        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db
        
        relay_service._get_pending_events = AsyncMock(return_value=[])
        
        # Execute
        count = await relay_service._process_pending_events()
        
        # Verify
        assert count == 0
    
    @pytest.mark.asyncio
    @patch('src.agents.message_relay.main.get_async_session')
    async def test_process_pending_events_with_failure(
        self, mock_get_session, relay_service
    ):
        """Test processing with some event failures."""
        # Setup
        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db
        
        test_events = [
            {'id': str(uuid4()), 'topic': 'test1'},
            {'id': str(uuid4()), 'topic': 'test2'},
        ]
        
        relay_service._get_pending_events = AsyncMock(return_value=test_events)
        # First event succeeds, second fails
        relay_service._publish_event = AsyncMock(side_effect=[True, False])
        
        # Execute
        count = await relay_service._process_pending_events()
        
        # Verify
        assert count == 1  # Only one successful


class TestDatabaseOperations:
    """Test database operations."""
    
    @pytest.mark.asyncio
    async def test_get_pending_events(self, relay_service):
        """Test getting pending events from database."""
        # Setup
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        
        expected_events = [
            {
                'id': str(uuid4()),
                'topic': 'domain-events',
                'key': 'test-key',
                'payload': '{"test": "data"}',
                'headers': None,
                'retry_count': 0,
                'max_retries': 3
            }
        ]
        
        # Mock the database row mapping
        mock_rows = []
        for event in expected_events:
            mock_row = AsyncMock()
            mock_row._mapping = event
            mock_rows.append(mock_row)
        
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result
        
        # Execute
        events = await relay_service._get_pending_events(mock_db)
        
        # Verify
        assert len(events) == 1
        assert events[0]['id'] == expected_events[0]['id']
        assert events[0]['topic'] == expected_events[0]['topic']
        
        # Verify database query
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        sql = str(call_args[0][0])
        assert "SELECT id, topic, key, payload, headers, retry_count, max_retries" in sql
        assert "FROM event_outbox" in sql
        assert "WHERE status = 'PENDING'" in sql
    
    @pytest.mark.asyncio
    async def test_mark_event_sent(self, relay_service):
        """Test marking event as sent."""
        # Setup
        mock_db = AsyncMock()
        event_id = str(uuid4())
        
        # Execute
        await relay_service._mark_event_sent(event_id, mock_db)
        
        # Verify
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        
        call_args = mock_db.execute.call_args
        sql = str(call_args[0][0])
        assert "UPDATE event_outbox" in sql
        assert "SET status = 'SENT'" in sql
        
        params = call_args[1]
        assert params['event_id'] == event_id


class TestEventPublishing:
    """Test Kafka event publishing."""
    
    @pytest.mark.asyncio
    async def test_publish_event_success(self, relay_service):
        """Test successful event publishing."""
        # Setup
        mock_db = AsyncMock()
        relay_service.kafka_manager = AsyncMock()
        relay_service.kafka_manager.send_message.return_value = True
        relay_service._mark_event_sent = AsyncMock()
        
        event = {
            'id': str(uuid4()),
            'topic': 'domain-events',
            'key': 'test-key',
            'payload': '{"event_type": "test"}',
            'headers': '{"content-type": "application/json"}'
        }
        
        # Execute
        result = await relay_service._publish_event(event, mock_db)
        
        # Verify
        assert result is True
        relay_service.kafka_manager.send_message.assert_called_once()
        relay_service._mark_event_sent.assert_called_once_with(event['id'], mock_db)
    
    @pytest.mark.asyncio
    async def test_publish_event_failure(self, relay_service):
        """Test event publishing failure."""
        # Setup
        mock_db = AsyncMock()
        relay_service.kafka_manager = AsyncMock()
        relay_service.kafka_manager.send_message.return_value = False
        relay_service._handle_publish_failure = AsyncMock()
        
        event = {
            'id': str(uuid4()),
            'topic': 'domain-events',
            'key': 'test-key',
            'payload': '{"event_type": "test"}',
            'headers': None
        }
        
        # Execute
        result = await relay_service._publish_event(event, mock_db)
        
        # Verify
        assert result is False
        relay_service._handle_publish_failure.assert_called_once_with(event, mock_db)
    
    @pytest.mark.asyncio
    async def test_publish_event_with_json_payload(self, relay_service):
        """Test publishing event with JSON string payload."""
        # Setup
        mock_db = AsyncMock()
        relay_service.kafka_manager = AsyncMock()
        relay_service.kafka_manager.send_message.return_value = True
        relay_service._mark_event_sent = AsyncMock()
        
        payload_dict = {"event_type": "test", "data": "value"}
        event = {
            'id': str(uuid4()),
            'topic': 'domain-events',
            'key': 'test-key',
            'payload': json.dumps(payload_dict),
            'headers': None
        }
        
        # Execute
        result = await relay_service._publish_event(event, mock_db)
        
        # Verify
        assert result is True
        
        # Check that send_message was called with correct parameters
        call_args = relay_service.kafka_manager.send_message.call_args
        assert call_args[1]['topic'] == event['topic']
        assert call_args[1]['key'] == event['key']
        
        # Verify payload was properly serialized
        sent_payload = call_args[1]['value']
        assert json.loads(sent_payload) == payload_dict


class TestRetryLogic:
    """Test retry and failure handling logic."""
    
    @pytest.mark.asyncio
    async def test_handle_publish_failure_with_retries_left(self, relay_service):
        """Test failure handling when retries are available."""
        # Setup
        mock_db = AsyncMock()
        event = {
            'id': str(uuid4()),
            'retry_count': 1,
            'max_retries': 3
        }
        
        # Execute
        await relay_service._handle_publish_failure(event, mock_db)
        
        # Verify
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        
        call_args = mock_db.execute.call_args
        sql = str(call_args[0][0])
        assert "UPDATE event_outbox" in sql
        assert "SET retry_count" in sql
        assert "scheduled_at" in sql
        
        params = call_args[1]
        assert params['retry_count'] == 2  # incremented
        assert 'scheduled_at' in params
    
    @pytest.mark.asyncio
    async def test_handle_publish_failure_max_retries_reached(self, relay_service):
        """Test failure handling when max retries reached."""
        # Setup
        mock_db = AsyncMock()
        event = {
            'id': str(uuid4()),
            'retry_count': 3,
            'max_retries': 3
        }
        
        # Execute
        await relay_service._handle_publish_failure(event, mock_db)
        
        # Verify
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        
        call_args = mock_db.execute.call_args
        sql = str(call_args[0][0])
        assert "UPDATE event_outbox" in sql
        assert "SET status = 'FAILED'" in sql
        assert "last_error" in sql
        
        params = call_args[1]
        assert "Failed after 3 retry attempts" in params['error']