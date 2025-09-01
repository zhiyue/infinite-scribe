"""Unit tests for Redis SSE service."""

import json
from contextlib import asynccontextmanager, suppress
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.common.services.redis_service import RedisService
from src.core.config import settings
from src.schemas.sse import EventScope, SSEMessage
from src.services.sse.redis_client import RedisSSEService


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
    async def redis_sse_service(self, redis_service):
        """Create Redis SSE service instance with proper cleanup."""
        service = RedisSSEService(redis_service)
        yield service
        # Cleanup any connections to prevent memory leaks
        with suppress(Exception):
            await service.close()

    @pytest.fixture
    def sample_sse_message(self):
        """Create sample SSE message for testing."""
        return SSEMessage(
            event="task.progress-updated",
            data={"task_id": "test-task-123", "progress": 50},
            id=None,
            retry=None,
            scope=EventScope.USER,
            version="1.0",
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
    @patch("src.services.sse.redis_client.redis.from_url")
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
            # Keep yielding non-message events to prevent hanging if break doesn't work
            while True:
                yield {"type": "subscribe"}

        mock_pubsub.listen.return_value = mock_listen()

        # Mock XRANGE response on RedisService client - returns exact entry by ID
        xrange_items = [
            (stream_id, {"event": "task.progress-updated", "data": json.dumps({"task_id": "test-123", "progress": 75})})
        ]
        mock_redis_client.xrange.return_value = xrange_items

        # Act - Use timeout to prevent hanging
        import asyncio

        events = []

        async def collect_events():
            async for event in redis_sse_service.subscribe_user_events(user_id):
                events.append(event)
                break  # Only process first event for test

        task = asyncio.create_task(collect_events())
        try:
            await asyncio.wait_for(task, timeout=0.5)
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

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

        # Verify XREAD was called correctly on RedisService client (batch processing)
        expected_streams = {f"events:user:{user_id}": since_id}
        mock_redis_client.xread.assert_called_once_with(expected_streams, count=50)  # BATCH_SIZE

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

        # Mock XREVRANGE response with corrupted data (since since_id="-" uses xrevrange)
        stream_items = [
            (
                "1693507300000-0",
                {"event": "task.progress-updated", "data": json.dumps({"task_id": "test-123", "progress": 50})},
            ),
            ("1693507200000-0", {"event": "task.progress-updated", "data": "invalid-json"}),
        ]
        mock_redis_client.xrevrange.return_value = stream_items

        # Act
        events = await redis_sse_service.get_recent_events("user-123", "-")

        # Assert - Should skip corrupted event and return valid one
        assert len(events) == 1
        assert events[0].data == {"task_id": "test-123", "progress": 50}

    @pytest.mark.asyncio
    async def test_subscribe_user_events_invalid_pointer_message(self, redis_sse_service):
        """Test subscription handles invalid pointer messages gracefully."""
        # Test the _process_pointer_message method directly to avoid async for loop issues
        invalid_message = {"data": "invalid-json"}

        # Act - This should not raise an exception
        result = await redis_sse_service._process_pointer_message(invalid_message, "user-123")

        # Assert - Should return None for invalid messages
        assert result is None

    @pytest.mark.asyncio
    async def test_subscribe_user_events_cleanup_resources(self, redis_sse_service):
        """Test that subscription properly cleans up resources."""
        # Test the _safe_cleanup method directly instead of the full subscription flow
        # This avoids the retry logic that can cause hanging

        # Arrange - Create mock pubsub objects
        from unittest.mock import AsyncMock, MagicMock

        mock_pubsub = MagicMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()

        channel = "sse:user:test-user"
        user_id = "test-user"

        # Act - Call the cleanup method directly
        await redis_sse_service._safe_cleanup(mock_pubsub, channel, user_id)

        # Assert - Should cleanup resources
        mock_pubsub.unsubscribe.assert_called_once_with(channel)
        mock_pubsub.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_user_events_trimmed_absent_entries(self, redis_sse_service, mock_redis_acquire):
        """Test subscription handles trimmed/absent stream entries gracefully."""
        # Test the _process_pointer_message method directly with empty xrange result
        # This avoids the async for loop + retry logic that causes hanging

        mock_redis_client = AsyncMock()
        redis_sse_service.redis_service.acquire = mock_redis_acquire(mock_redis_client)

        user_id = "user-123"
        stream_id = "1693507200000-0"

        # Mock XRANGE returning empty list (entry was trimmed or doesn't exist)
        mock_redis_client.xrange.return_value = []

        # Mock pointer message with reference to trimmed/absent entry
        pointer_message = {"data": json.dumps({"stream_key": f"events:user:{user_id}", "stream_id": stream_id})}

        # Act - This should handle the absent entry gracefully
        result = await redis_sse_service._process_pointer_message(pointer_message, user_id)

        # Assert - Should return None for absent entries
        assert result is None

        # Verify XRANGE was called to attempt fetch
        stream_key = f"events:user:{user_id}"
        mock_redis_client.xrange.assert_called_once_with(stream_key, stream_id, stream_id, count=1)

    @pytest.mark.asyncio
    async def test_publish_and_subscribe_minimal_interaction(
        self, redis_sse_service, mock_redis_acquire, sample_sse_message
    ):
        """Minimal end-to-end: publish then receive via subscribe."""
        # Arrange
        user_id = "user-xyz"
        stream_id = "1700000000000-0"

        # Async queue to simulate Pub/Sub pointer delivery
        import asyncio

        queue: asyncio.Queue[dict] = asyncio.Queue()

        # Mock Pub/Sub client and its pubsub() listener
        mock_pubsub_client = AsyncMock()
        redis_sse_service._pubsub_client = mock_pubsub_client

        subscribed = asyncio.Event()

        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock(side_effect=lambda channel: subscribed.set())
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_pubsub_client.pubsub = MagicMock(return_value=mock_pubsub)

        async def listen_gen():
            # Initial subscribe event ignored by service
            yield {"type": "subscribe"}
            # Wait until a pointer is published, then forward it
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=0.1)
                yield msg
                # Keep yielding subscribe messages to keep the generator alive
                # until the task is cancelled
                while True:
                    yield {"type": "subscribe"}
            except TimeoutError:
                # If no message comes, keep yielding subscribe messages
                while True:
                    yield {"type": "subscribe"}

        mock_pubsub.listen.return_value = listen_gen()

        async def mock_publish(channel: str, data: str):
            await queue.put({"type": "message", "data": data})
            return 1

        mock_pubsub_client.publish.side_effect = mock_publish

        # Mock Redis stream client used by RedisService.acquire()
        mock_redis_client = AsyncMock()
        redis_sse_service.redis_service.acquire = mock_redis_acquire(mock_redis_client)

        # xadd returns a predictable stream id
        mock_redis_client.xadd.return_value = stream_id

        # XRANGE returns the event stored at that id
        mock_redis_client.xrange.return_value = [
            (
                stream_id,
                {
                    "event": sample_sse_message.event,
                    "data": json.dumps(sample_sse_message.data),
                },
            )
        ]

        # Act: start subscriber task first
        async def get_one_event():
            async for ev in redis_sse_service.subscribe_user_events(user_id):
                return ev
            return None

        sub_task = asyncio.create_task(get_one_event())

        try:
            # Ensure subscription set up before publishing (reduced timeout)
            await asyncio.wait_for(subscribed.wait(), timeout=0.1)

            # Publish one event
            pub_stream_id = await redis_sse_service.publish_event(user_id, sample_sse_message)

            # Await receipt (reduced timeout)
            received = await asyncio.wait_for(sub_task, timeout=0.5)

            # Assert
            assert pub_stream_id == stream_id
            assert received is not None
            assert received.event == sample_sse_message.event
            assert received.data == sample_sse_message.data
            assert received.id == stream_id

        finally:
            # Ensure task is always cleaned up
            if not sub_task.done():
                sub_task.cancel()
                with suppress(asyncio.CancelledError):
                    await sub_task

        # Give a moment for cleanup to complete
        await asyncio.sleep(0.01)

        # Cleanup assertions
        mock_pubsub.unsubscribe.assert_called_once()
        mock_pubsub.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_user_events_redis_connection_error_retry(self, redis_sse_service):
        """Test that subscribe_user_events properly handles RedisConnectionError with retry."""
        from redis.exceptions import ConnectionError as RedisConnectionError

        mock_client = MagicMock()
        redis_sse_service._pubsub_client = mock_client
        redis_sse_service.init_pubsub_client = AsyncMock()

        # Mock pubsub to always raise RedisConnectionError to test retry behavior
        def mock_pubsub():
            raise RedisConnectionError("Connection failed")

        mock_client.pubsub.side_effect = mock_pubsub

        # Act & Assert - Should retry and eventually raise after max retries
        with pytest.raises(RedisConnectionError, match="Connection failed"):
            async for _ in redis_sse_service.subscribe_user_events("user-123"):
                break

        # Verify init_pubsub_client was called during retry attempts
        redis_sse_service.init_pubsub_client.assert_called()

    @pytest.mark.asyncio
    async def test_subscribe_user_events_redis_error_no_retry(self, redis_sse_service):
        """Test that subscribe_user_events doesn't retry on RedisError."""
        import asyncio

        from redis.exceptions import RedisError

        # Arrange
        mock_client = MagicMock()  # Use MagicMock instead of AsyncMock
        redis_sse_service._pubsub_client = mock_client

        # Mock pubsub to raise RedisError - use a callable side effect
        def mock_pubsub():
            raise RedisError("Redis error")

        mock_client.pubsub.side_effect = mock_pubsub

        # Act & Assert - Should raise RedisError without retry
        with pytest.raises(RedisError, match="Redis error"):
            # Use timeout to prevent hanging if exception handling fails
            async def run_subscription():
                async for event in redis_sse_service.subscribe_user_events("user-123"):
                    break

            await asyncio.wait_for(run_subscription(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_get_recent_events_initial_connection_uses_xrevrange(self, redis_sse_service, mock_redis_acquire):
        """Test that initial connections (since_id='-') use XREVRANGE for recent events."""
        # Arrange
        mock_redis_client = AsyncMock()
        redis_sse_service.redis_service.acquire = mock_redis_acquire(mock_redis_client)

        # Mock XREVRANGE response (returns most recent events in reverse order)
        stream_items = [
            ("1693507400000-0", {"event": "task.completed", "data": json.dumps({"task_id": "test-123"})}),
            (
                "1693507300000-0",
                {"event": "task.progress", "data": json.dumps({"task_id": "test-123", "progress": 75})},
            ),
            ("1693507200000-0", {"event": "task.started", "data": json.dumps({"task_id": "test-123"})}),
        ]
        mock_redis_client.xrevrange.return_value = stream_items

        # Act
        events = await redis_sse_service.get_recent_events("user-123", "-")

        # Assert
        assert len(events) == 3
        # Events should be in chronological order (oldest first)
        assert events[0].event == "task.started"
        assert events[1].event == "task.progress"
        assert events[2].event == "task.completed"

        # Verify XREVRANGE was called correctly
        mock_redis_client.xrevrange.assert_called_once_with(
            "events:user:user-123",
            "+",
            "-",
            count=50,  # DEFAULT_HISTORY_LIMIT
        )
        # XREAD should not be called for initial connections
        mock_redis_client.xread.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_recent_events_reconnection_uses_batch_processing(self, redis_sse_service, mock_redis_acquire):
        """Test that reconnections use batch processing with XREAD."""
        # Arrange
        mock_redis_client = AsyncMock()
        redis_sse_service.redis_service.acquire = mock_redis_acquire(mock_redis_client)

        # Mock XREAD responses for batch processing - need full batch size to trigger second call
        # Create exactly BATCH_SIZE (50) items for first batch to continue processing
        from src.services.sse.redis_client import BATCH_SIZE

        first_batch_items = []
        for i in range(BATCH_SIZE):
            first_batch_items.append(
                (
                    f"1693507{200+i:03d}000-0",
                    {"event": f"task.event{i}", "data": json.dumps({"task_id": "test-123", "event_num": i})},
                )
            )

        batch1 = [("events:user:user-123", first_batch_items)]

        # Second batch with fewer items (will trigger exit condition)
        batch2 = [
            (
                "events:user:user-123",
                [
                    ("1693507400000-0", {"event": "task.started", "data": json.dumps({"task_id": "test-123"})}),
                    (
                        "1693507500000-0",
                        {"event": "task.progress", "data": json.dumps({"task_id": "test-123", "progress": 50})},
                    ),
                    ("1693507600000-0", {"event": "task.completed", "data": json.dumps({"task_id": "test-123"})}),
                ],
            )
        ]

        # First call returns full batch, second returns partial batch (indicating end)
        mock_redis_client.xread.side_effect = [batch1, batch2]

        # Act
        events = await redis_sse_service.get_recent_events("user-123", "1693507100000-0")

        # Assert - Should have BATCH_SIZE + 3 events total
        assert len(events) == BATCH_SIZE + 3

        # Verify some events from first batch
        assert events[0].event == "task.event0"
        assert events[1].event == "task.event1"

        # Verify events from second batch (last 3 events)
        assert events[-3].event == "task.started"
        assert events[-2].event == "task.progress"
        assert events[-1].event == "task.completed"

        # Verify XREAD was called twice with correct parameters
        assert mock_redis_client.xread.call_count == 2

        # First call
        mock_redis_client.xread.assert_any_call(
            {"events:user:user-123": "1693507100000-0"},
            count=50,  # BATCH_SIZE
        )

        # Second call with updated since_id (last item from first batch)
        expected_last_id = f"1693507{200+(BATCH_SIZE-1):03d}000-0"
        mock_redis_client.xread.assert_any_call(
            {"events:user:user-123": expected_last_id},
            count=50,  # BATCH_SIZE
        )

        # XREVRANGE should not be called for reconnections
        mock_redis_client.xrevrange.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_health_with_ping_success(self, redis_sse_service):
        """Test check_health returns True when ping succeeds."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        redis_sse_service._pubsub_client = mock_client

        # Act
        result = await redis_sse_service.check_health()

        # Assert
        assert result is True
        mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_health_with_ping_failure(self, redis_sse_service):
        """Test check_health returns False when ping fails."""
        from redis.exceptions import ConnectionError as RedisConnectionError

        # Arrange
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(side_effect=RedisConnectionError("Connection failed"))
        redis_sse_service._pubsub_client = mock_client

        # Act
        result = await redis_sse_service.check_health()

        # Assert
        assert result is False
        mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_health_no_client(self, redis_sse_service):
        """Test check_health returns False when no client is initialized."""
        # Arrange - no client set
        redis_sse_service._pubsub_client = None

        # Act
        result = await redis_sse_service.check_health()

        # Assert
        assert result is False
