"""Unit tests for Redis SSE service."""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.common.services.redis_sse_service import RedisSSEService
from src.common.services.redis_service import RedisService
from src.core.config import settings
from src.schemas.sse import SSEMessage, EventScope


class TestRedisSSEService:
    """Test cases for RedisSSEService."""

    @pytest.fixture
    def redis_service(self):
        """Create Redis service instance."""
        return RedisService()

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def redis_sse_service(self, redis_service):
        """Create Redis SSE service instance."""
        return RedisSSEService(redis_service)

    @pytest.fixture
    def sample_sse_message(self):
        """Create sample SSE message for testing."""
        return SSEMessage(
            event="task.progress-updated",
            data={"task_id": "test-task-123", "progress": 50},
            id=None,
            retry=None,
            scope=EventScope.USER,
            version="1.0"
        )

    @pytest.fixture
    def mock_redis_acquire(self):
        """Create proper async context manager mock for RedisService.acquire()."""
        def create_mock_acquire(mock_redis_client):
            @asynccontextmanager
            async def mock_acquire():
                yield mock_redis_client
            return mock_acquire
        return create_mock_acquire

    @pytest.mark.asyncio
    @patch("src.common.services.redis_sse_service.redis.from_url")
    async def test_init_pubsub_client(self, mock_from_url, redis_sse_service):
        """Test Pub/Sub client initialization."""
        # Arrange
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client

        # Act
        await redis_sse_service.init_pubsub_client()

        # Assert
        assert redis_sse_service._pubsub_client == mock_client
        mock_from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_client(self, redis_sse_service):
        """Test closing Pub/Sub client."""
        # Arrange
        mock_client = AsyncMock()
        redis_sse_service._pubsub_client = mock_client

        # Act
        await redis_sse_service.close()

        # Assert
        assert redis_sse_service._pubsub_client is None
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_client(self, redis_sse_service):
        """Test close when no client exists."""
        # Act & Assert - Should not raise error
        await redis_sse_service.close()
        assert redis_sse_service._pubsub_client is None

    @pytest.mark.asyncio
    async def test_publish_event_success(self, redis_sse_service, sample_sse_message, mock_redis_acquire):
        """Test successful event publishing to Stream and Pub/Sub."""
        # Arrange
        mock_pubsub_client = AsyncMock()
        redis_sse_service._pubsub_client = mock_pubsub_client
        
        mock_redis_client = AsyncMock()
        redis_sse_service.redis_service.acquire = mock_redis_acquire(mock_redis_client)

        user_id = "user-123"
        stream_id = "1693507200000-0"

        # Mock XADD to return stream ID
        mock_redis_client.xadd.return_value = stream_id

        # Act
        result = await redis_sse_service.publish_event(user_id, sample_sse_message)

        # Assert
        assert result == stream_id
        assert sample_sse_message.id == stream_id

        # Verify XADD was called on RedisService client with correct parameters
        stream_key = f"events:user:{user_id}"
        expected_data = {
            "event": "task.progress-updated",
            "data": json.dumps({"task_id": "test-task-123", "progress": 50}, ensure_ascii=False, default=str),
        }
        # Verify XADD was called on RedisService client with correct parameters
        mock_redis_client.xadd.assert_called_once_with(
            stream_key, expected_data, maxlen=settings.database.redis_sse_stream_maxlen, approximate=True
        )

        # Verify Pub/Sub publish was called on dedicated Pub/Sub client
        channel = f"sse:user:{user_id}"
        expected_pointer = json.dumps({"stream_key": stream_key, "stream_id": stream_id})
        mock_pubsub_client.publish.assert_called_once_with(channel, expected_pointer)

    @pytest.mark.asyncio
    async def test_publish_event_no_client(self, redis_sse_service, sample_sse_message):
        """Test publish event without Pub/Sub client."""
        # Act & Assert
        with pytest.raises(RuntimeError, match="Pub/Sub client not initialized"):
            await redis_sse_service.publish_event("user-123", sample_sse_message)

    @pytest.mark.asyncio
    async def test_subscribe_user_events_success(self, redis_sse_service, mock_redis_acquire):
        """Test successful subscription to user events."""
        # Arrange
        mock_pubsub_client = AsyncMock()
        redis_sse_service._pubsub_client = mock_pubsub_client
        
        mock_redis_client = AsyncMock()
        redis_sse_service.redis_service.acquire = mock_redis_acquire(mock_redis_client)

        user_id = "user-123"
        stream_id = "1693507200000-0"

        # Mock Pub/Sub subscription - pubsub() is sync method returning sync mock with async methods
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        # Make pubsub() a sync method that returns the mock
        mock_pubsub_client.pubsub = MagicMock(return_value=mock_pubsub)

        # Mock pub/sub messages
        pointer_message = {
            "type": "message",
            "data": json.dumps({"stream_key": f"events:user:{user_id}", "stream_id": stream_id}),
        }

        async def mock_listen():
            yield {"type": "subscribe"}
            yield pointer_message

        mock_pubsub.listen.return_value = mock_listen()

        # Mock XRANGE response on RedisService client - returns exact entry by ID
        xrange_items = [
            (stream_id, {"event": "task.progress-updated", "data": json.dumps({"task_id": "test-123", "progress": 75})})
        ]
        mock_redis_client.xrange.return_value = xrange_items

        # Act
        events = []
        async for event in redis_sse_service.subscribe_user_events(user_id):
            events.append(event)
            break  # Only process first event for test

        # Assert
        assert len(events) == 1
        event = events[0]
        assert event.event == "task.progress-updated"
        assert event.data == {"task_id": "test-123", "progress": 75}
        assert event.id == stream_id
        assert event.scope == EventScope.USER
        
        # Verify XRANGE was called on RedisService client with correct parameters for exact ID lookup
        stream_key = f"events:user:{user_id}"
        mock_redis_client.xrange.assert_called_once_with(stream_key, stream_id, stream_id, count=1)

    @pytest.mark.asyncio
    async def test_get_recent_events_success(self, redis_sse_service, mock_redis_acquire):
        """Test successful retrieval of recent events from Stream."""
        # Arrange
        mock_pubsub_client = AsyncMock()
        redis_sse_service._pubsub_client = mock_pubsub_client
        
        mock_redis_client = AsyncMock()
        redis_sse_service.redis_service.acquire = mock_redis_acquire(mock_redis_client)

        user_id = "user-123"
        since_id = "1693507100000-0"

        # Mock XREAD response on RedisService client with multiple events
        stream_entries = [
            (
                f"events:user:{user_id}",
                [
                    (
                        "1693507200000-0",
                        {"event": "task.progress-updated", "data": json.dumps({"task_id": "test-123", "progress": 25})},
                    ),
                    (
                        "1693507300000-0",
                        {"event": "task.progress-updated", "data": json.dumps({"task_id": "test-123", "progress": 50})},
                    ),
                    (
                        "1693507400000-0",
                        {
                            "event": "task.progress-completed",
                            "data": json.dumps({"task_id": "test-123", "result": "success"}),
                        },
                    ),
                ],
            )
        ]
        mock_redis_client.xread.return_value = stream_entries

        # Act
        events = await redis_sse_service.get_recent_events(user_id, since_id)

        # Assert
        assert len(events) == 3

        # Verify first event
        assert events[0].event == "task.progress-updated"
        assert events[0].data == {"task_id": "test-123", "progress": 25}
        assert events[0].id == "1693507200000-0"
        assert events[0].scope == EventScope.USER

        # Verify XREAD was called correctly on RedisService client
        expected_streams = {f"events:user:{user_id}": since_id}
        mock_redis_client.xread.assert_called_once_with(expected_streams, count=100)

    @pytest.mark.asyncio
    async def test_get_recent_events_no_events(self, redis_sse_service, mock_redis_acquire):
        """Test get_recent_events when no events exist."""
        # Arrange
        mock_pubsub_client = AsyncMock()
        redis_sse_service._pubsub_client = mock_pubsub_client
        
        mock_redis_client = AsyncMock()
        redis_sse_service.redis_service.acquire = mock_redis_acquire(mock_redis_client)
        
        mock_redis_client.xread.return_value = []

        # Act
        events = await redis_sse_service.get_recent_events("user-123", "-")

        # Assert
        assert events == []

    @pytest.mark.asyncio
    async def test_get_recent_events_corrupted_data(self, redis_sse_service, mock_redis_acquire):
        """Test get_recent_events handles corrupted event data gracefully."""
        # Arrange
        mock_pubsub_client = AsyncMock()
        redis_sse_service._pubsub_client = mock_pubsub_client
        
        mock_redis_client = AsyncMock()
        redis_sse_service.redis_service.acquire = mock_redis_acquire(mock_redis_client)

        # Mock XREAD response with corrupted data
        stream_entries = [
            (
                "events:user:user-123",
                [
                    ("1693507200000-0", {"event": "task.progress-updated", "data": "invalid-json"}),
                    (
                        "1693507300000-0",
                        {"event": "task.progress-updated", "data": json.dumps({"task_id": "test-123", "progress": 50})},
                    ),
                ],
            )
        ]
        mock_redis_client.xread.return_value = stream_entries

        # Act
        events = await redis_sse_service.get_recent_events("user-123", "-")

        # Assert - Should skip corrupted event and return valid one
        assert len(events) == 1
        assert events[0].data == {"task_id": "test-123", "progress": 50}

    @pytest.mark.asyncio
    async def test_subscribe_user_events_invalid_pointer_message(self, redis_sse_service):
        """Test subscription handles invalid pointer messages gracefully."""
        # Arrange
        mock_client = AsyncMock()
        redis_sse_service._pubsub_client = mock_client

        # Mock Pub/Sub subscription - pubsub() is sync method returning sync mock with async methods
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        # Make pubsub() a sync method that returns the mock
        mock_client.pubsub = MagicMock(return_value=mock_pubsub)

        # Mock invalid pointer message
        invalid_message = {"type": "message", "data": "invalid-json"}

        async def mock_listen():
            yield invalid_message

        mock_pubsub.listen.return_value = mock_listen()

        # Act - Should not raise exception
        events = []
        async for event in redis_sse_service.subscribe_user_events("user-123"):
            events.append(event)
            break

        # Assert - Should handle gracefully
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_subscribe_user_events_cleanup_resources(self, redis_sse_service):
        """Test that subscription properly cleans up resources."""
        # Arrange
        mock_client = AsyncMock()
        redis_sse_service._pubsub_client = mock_client

        # Mock Pub/Sub subscription - pubsub() is sync method returning sync mock with async methods
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        # Make pubsub() a sync method that returns the mock
        mock_client.pubsub = MagicMock(return_value=mock_pubsub)

        async def mock_listen():
            return
            yield  # Make it an async generator that ends immediately

        mock_pubsub.listen.return_value = mock_listen()

        # Act
        events = []
        async for event in redis_sse_service.subscribe_user_events("user-123"):
            events.append(event)

        # Assert - Should cleanup resources
        mock_pubsub.unsubscribe.assert_called_once()
        mock_pubsub.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_user_events_trimmed_absent_entries(self, redis_sse_service, mock_redis_acquire):
        """Test subscription handles trimmed/absent stream entries gracefully."""
        # Arrange
        mock_pubsub_client = AsyncMock()
        redis_sse_service._pubsub_client = mock_pubsub_client
        
        mock_redis_client = AsyncMock()
        redis_sse_service.redis_service.acquire = mock_redis_acquire(mock_redis_client)

        user_id = "user-123"
        stream_id = "1693507200000-0"

        # Mock Pub/Sub subscription
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_pubsub_client.pubsub = MagicMock(return_value=mock_pubsub)

        # Mock Pub/Sub message with pointer to trimmed/absent entry
        pointer_message = {
            "type": "message",
            "data": json.dumps({"stream_key": f"events:user:{user_id}", "stream_id": stream_id}),
        }

        async def mock_listen():
            yield {"type": "subscribe"}
            yield pointer_message

        mock_pubsub.listen.return_value = mock_listen()

        # Mock XRANGE returning empty list (entry was trimmed or doesn't exist)
        mock_redis_client.xrange.return_value = []

        # Act
        events = []
        async for event in redis_sse_service.subscribe_user_events(user_id):
            events.append(event)
            break  # Should not yield any events, so this won't be reached

        # Assert - Should handle gracefully and yield no events
        assert len(events) == 0
        
        # Verify XRANGE was called to attempt fetch
        stream_key = f"events:user:{user_id}"
        mock_redis_client.xrange.assert_called_once_with(stream_key, stream_id, stream_id, count=1)
        
        # Verify cleanup still occurs
        mock_pubsub.unsubscribe.assert_called_once()
        mock_pubsub.close.assert_called_once()
