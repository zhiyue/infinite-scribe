"""Unit tests for SSE Connection Manager."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request
from src.db.redis import RedisService
from src.schemas.sse import EventScope, SSEMessage
from src.services.sse.config import sse_config
from src.services.sse.connection_manager import SSEConnectionManager
from src.services.sse.connection_state import SSEConnectionState
from src.services.sse.redis_client import RedisSSEService
from sse_starlette import EventSourceResponse


class TestSSEConnectionManager:
    """Test cases for SSEConnectionManager with optimized fixture setup."""

    @pytest.fixture
    def redis_service(self):
        """Create Redis service instance."""
        return RedisService()

    @pytest.fixture
    def mock_redis_client(self):
        """Create comprehensive mock Redis client with all operations."""
        client = AsyncMock()
        # Default Redis counter operations for concurrency limiting
        client.incr.return_value = 1  # First connection
        client.decr.return_value = 0  # After cleanup
        client.set.return_value = True
        client.expire.return_value = True
        client.delete.return_value = 1
        client.get.return_value = None
        client.setex.return_value = True

        # Mock eval method to simulate Lua script failure (falls back to non-atomic)
        client.eval = AsyncMock(side_effect=AttributeError("eval not supported"))

        # Mock scan_iter to return empty async iterator by default
        async def empty_async_iter(match=None):
            return
            yield  # unreachable, but makes it an async generator

        client.scan_iter = empty_async_iter
        return client

    @pytest.fixture
    def configured_redis_sse_service(self, redis_service, mock_redis_client):
        """Create Redis SSE service with pre-configured mock client."""
        service = RedisSSEService(redis_service)
        service._pubsub_client = mock_redis_client
        # Default mock behaviors for SSE operations
        service.get_recent_events = AsyncMock(return_value=[])
        service.subscribe_user_events = AsyncMock()
        return service

    @pytest.fixture
    def sse_manager(self, configured_redis_sse_service):
        """Create SSE Connection Manager with configured dependencies."""
        return SSEConnectionManager(configured_redis_sse_service)

    @pytest.fixture
    def sample_user_id(self):
        """Create sample user ID for testing."""
        return str(uuid4())

    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI Request object."""
        request = AsyncMock(spec=Request)
        request.is_disconnected.return_value = False
        request.headers = {}
        return request

    @pytest.fixture
    def sample_sse_messages(self):
        """Create reusable SSE messages for testing."""
        return [
            SSEMessage(event="task.progress-updated", data={"progress": 25}, id="msg-1", scope=EventScope.USER),
            SSEMessage(event="task.progress-updated", data={"progress": 50}, id="msg-2", scope=EventScope.USER),
        ]

    async def test_add_connection_creates_event_source_response(self, sse_manager, sample_user_id, mock_request):
        """Test that add_connection returns EventSourceResponse."""
        response = await sse_manager.add_connection(mock_request, sample_user_id)

        assert isinstance(response, EventSourceResponse)
        # Verify Redis counter incremented with both user and global keys (fallback mode)
        expected_user_key = sse_manager._get_connection_key(sample_user_id)
        expected_global_key = "global:sse_connections_count"

        # Verify both incr calls were made (user counter + global counter)
        assert sse_manager.redis_sse._pubsub_client.incr.call_count == 2
        sse_manager.redis_sse._pubsub_client.incr.assert_any_call(expected_user_key)
        sse_manager.redis_sse._pubsub_client.incr.assert_any_call(expected_global_key)

        # Verify expire was called on user key
        sse_manager.redis_sse._pubsub_client.expire.assert_called_once_with(
            expected_user_key, sse_manager.CONNECTION_EXPIRY_SECONDS
        )

    async def test_add_connection_enforces_concurrency_limit(self, sse_manager, sample_user_id, mock_request):
        """Test that max connections per user limit is enforced using constants."""
        # Mock Redis to return over the limit on first incr (user counter)
        over_limit_count = sse_manager.MAX_CONNECTIONS_PER_USER + 1
        sse_manager.redis_sse._pubsub_client.incr.side_effect = [
            over_limit_count,
            1,
        ]  # User counter over limit, global counter normal

        with pytest.raises(HTTPException) as exc_info:
            await sse_manager.add_connection(mock_request, sample_user_id)

        assert exc_info.value.status_code == 429
        assert "Too many concurrent SSE connections" in str(exc_info.value.detail)

        # Verify both counters were incremented initially
        expected_user_key = sse_manager._get_connection_key(sample_user_id)
        expected_global_key = "global:sse_connections_count"
        assert sse_manager.redis_sse._pubsub_client.incr.call_count == 2

        # Verify both counters were rolled back (safe_decr_counter decrements both)
        assert sse_manager.redis_sse._pubsub_client.decr.call_count == 2
        sse_manager.redis_sse._pubsub_client.decr.assert_any_call(expected_user_key)
        sse_manager.redis_sse._pubsub_client.decr.assert_any_call(expected_global_key)

    async def test_connection_state_tracking(self, sse_manager, sample_user_id, mock_request):
        """Test that connections are properly tracked in memory."""
        initial_count = len(sse_manager.connections)

        # Add connection
        response = await sse_manager.add_connection(mock_request, sample_user_id)

        # Verify response type and connection count
        assert isinstance(response, EventSourceResponse)
        assert len(sse_manager.connections) == initial_count + 1

        # Verify connection state properties
        connection_states = list(sse_manager.connections.values())
        new_connection = connection_states[-1]  # Last added connection

        assert isinstance(new_connection, SSEConnectionState)
        assert new_connection.user_id == sample_user_id
        assert isinstance(new_connection.connected_at, datetime)

    async def test_event_source_response_configuration(self, sse_manager, sample_user_id, mock_request):
        """Test EventSourceResponse is created with correct configuration constants."""
        response = await sse_manager.add_connection(mock_request, sample_user_id)

        assert isinstance(response, EventSourceResponse)
        # Verify manager uses the defined constants
        assert sse_manager.ping_interval == sse_manager.PING_INTERVAL_SECONDS

    async def test_cleanup_connection_removes_resources(self, sse_manager, sample_user_id):
        """Test that connection cleanup removes all resources using helper methods."""
        connection_id = "test-conn-123"

        # Add connection to memory first
        now = datetime.now(UTC)
        sse_manager.connections[connection_id] = SSEConnectionState(
            connection_id=connection_id,
            user_id=sample_user_id,
            connected_at=now,
            last_activity_at=now,
        )

        # Call cleanup
        await sse_manager._cleanup_connection(connection_id, sample_user_id)

        # Verify memory cleanup
        assert connection_id not in sse_manager.connections

        # Verify both Redis counters decremented using safe helper method
        expected_user_key = sse_manager._get_connection_key(sample_user_id)
        expected_global_key = "global:sse_connections_count"
        assert sse_manager.redis_sse._pubsub_client.decr.call_count == 2
        sse_manager.redis_sse._pubsub_client.decr.assert_any_call(expected_user_key)
        sse_manager.redis_sse._pubsub_client.decr.assert_any_call(expected_global_key)

    async def test_cleanup_stale_connections_uses_constants(self, sse_manager):
        """Test zombie connection GC uses configured threshold constants."""
        # Add connections older than the threshold
        threshold_exceeded = sse_manager.STALE_CONNECTION_THRESHOLD_SECONDS + 100
        old_time = datetime.now(UTC).timestamp() - threshold_exceeded

        stale_connections_count = 2
        for i in range(stale_connections_count):
            conn_id = f"stale-conn-{i}"
            old_datetime = datetime.fromtimestamp(old_time, tz=UTC)
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=old_datetime,
                last_activity_at=old_datetime,
                last_event_id=None,
            )
            sse_manager.connections[conn_id] = connection_state

        # Run cleanup
        stale_count = await sse_manager.cleanup_stale_connections()

        assert stale_count == stale_connections_count

    async def test_cleanup_skips_recent_activity_connections(self, sse_manager):
        """Connections with recent activity should not be cleaned even if long-lived."""
        threshold = sse_manager.STALE_CONNECTION_THRESHOLD_SECONDS
        old_connected_at = datetime.now(UTC) - timedelta(seconds=threshold + 300)
        recent_activity = datetime.now(UTC)

        conn_id = "long-lived-conn"
        connection_state = SSEConnectionState(
            connection_id=conn_id,
            user_id="user-keep",
            connected_at=old_connected_at,
            last_activity_at=recent_activity,
            last_event_id=None,
        )
        sse_manager.connections[conn_id] = connection_state

        cleaned = await sse_manager.cleanup_stale_connections()

        assert cleaned == 0
        assert conn_id in sse_manager.connections

    async def test_get_connection_count_with_helper_methods(self, sse_manager):
        """Test connection count reporting using helper methods."""
        memory_connections_count = 3
        # Add some connections to memory
        for i in range(memory_connections_count):
            conn_id = f"conn-{i}"
            now = datetime.now(UTC)
            sse_manager.connections[conn_id] = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=now,
                last_activity_at=now,
                last_event_id=None,
            )

        # Mock Redis scan for connection counters
        redis_keys = ["user:user1:sse_conns", "user:user2:sse_conns"]
        redis_total = 3

        async def mock_scan_iter(match=None):
            for key in redis_keys:
                yield key

        sse_manager.redis_sse._pubsub_client.scan_iter = mock_scan_iter
        # First call gets global counter (None), then individual counter calls get "2" and "1"
        sse_manager.redis_sse._pubsub_client.get.side_effect = [None, "2", "1"]

        stats = await sse_manager.get_connection_count()

        assert stats["active_connections"] == memory_connections_count
        assert stats["redis_connection_counters"] == redis_total

    async def test_redis_counter_negative_protection_with_helper(self, sse_manager, sample_user_id):
        """Test that Redis counters don't go negative using safe helper method."""
        # Mock decr to return negative value for both user and global counters
        sse_manager.redis_sse._pubsub_client.decr.return_value = -1

        connection_id = "test-conn"
        await sse_manager._cleanup_connection(connection_id, sample_user_id)

        # Verify that both counters were reset to 0 when they went negative
        expected_user_key = sse_manager._get_connection_key(sample_user_id)
        expected_global_key = "global:sse_connections_count"
        assert sse_manager.redis_sse._pubsub_client.set.call_count == 2
        sse_manager.redis_sse._pubsub_client.set.assert_any_call(expected_user_key, 0)
        sse_manager.redis_sse._pubsub_client.set.assert_any_call(expected_global_key, 0)

    async def test_connection_manager_initialization_with_constants(self, configured_redis_sse_service):
        """Test that SSEConnectionManager initializes with correct constants and dependencies."""
        manager = SSEConnectionManager(configured_redis_sse_service)

        # Verify dependency injection
        assert manager.redis_sse == configured_redis_sse_service
        assert manager.connections == {}

        # Verify constants are properly set
        assert manager.ping_interval == manager.PING_INTERVAL_SECONDS
        assert manager.MAX_CONNECTIONS_PER_USER == 2
        assert manager.CONNECTION_EXPIRY_SECONDS == 300
        assert manager.RECENT_EVENTS_LIMIT == 50  # Updated to match DEFAULT_HISTORY_LIMIT
        assert manager.STALE_CONNECTION_THRESHOLD_SECONDS == 300

        # Verify all public methods exist
        required_methods = ["add_connection", "cleanup_stale_connections", "get_connection_count"]
        for method_name in required_methods:
            assert hasattr(manager, method_name)

        # Verify helper methods exist (private but testable)
        helper_methods = [
            "_get_connection_key",
            "_safe_decr_counter",
            "_check_connection_limit",
            "_cleanup_connection",
            "_get_total_redis_connections",
        ]
        for method_name in helper_methods:
            assert hasattr(manager, method_name)

    async def test_last_event_id_support_from_headers(self, sse_manager, sample_user_id):
        """Test that Last-Event-ID is read from request headers for reconnection."""
        # Create mock request with Last-Event-ID header
        mock_request = AsyncMock(spec=Request)
        mock_request.is_disconnected.return_value = False
        mock_request.headers = {"last-event-id": "event-123"}

        # Add connection
        await sse_manager.add_connection(mock_request, sample_user_id)

        # Verify connection state includes last_event_id
        connection_states = list(sse_manager.connections.values())
        new_connection = connection_states[-1]
        assert new_connection.last_event_id == "event-123"

    async def test_historical_events_with_since_id(self, sse_manager, sample_user_id, sample_sse_messages):
        """Test that historical events are filtered by since_id parameter."""
        mock_request = AsyncMock(spec=Request)
        mock_request.is_disconnected.return_value = False

        # Mock recent events to return sample messages
        sse_manager.redis_sse.get_recent_events.return_value = sample_sse_messages

        # Call _send_historical_events on the event_streamer with specific since_id
        events = []
        async for event in sse_manager.event_streamer._send_historical_events(
            mock_request, sample_user_id, since_id="event-0"
        ):
            events.append(event)

        # Verify get_recent_events was called with since_id
        sse_manager.redis_sse.get_recent_events.assert_called_once_with(sample_user_id, since_id="event-0")

    async def test_add_connection_without_last_event_id_header(self, sse_manager, sample_user_id, mock_request):
        """Test that connection works without Last-Event-ID header (new connection)."""
        # Ensure no Last-Event-ID header
        mock_request.headers = {}

        await sse_manager.add_connection(mock_request, sample_user_id)

        # Verify connection state has None for last_event_id
        connection_states = list(sse_manager.connections.values())
        new_connection = connection_states[-1]
        assert new_connection.last_event_id is None

    async def test_http_429_includes_retry_after_header(self, sse_manager, sample_user_id, mock_request):
        """Test that HTTP 429 response includes Retry-After header for client recovery."""
        # Mock Redis to return over the limit
        over_limit_count = sse_manager.MAX_CONNECTIONS_PER_USER + 1
        sse_manager.redis_sse._pubsub_client.incr.return_value = over_limit_count

        with pytest.raises(HTTPException) as exc_info:
            await sse_manager.add_connection(mock_request, sample_user_id)

        assert exc_info.value.status_code == 429
        assert "Too many concurrent SSE connections" in str(exc_info.value.detail)

        # Verify Retry-After header is present
        assert "Retry-After" in exc_info.value.headers
        assert exc_info.value.headers["Retry-After"] == str(sse_manager.RETRY_AFTER_SECONDS)

    @pytest.mark.asyncio
    async def test_get_total_redis_connections_global_counter_success(self, sse_manager, mock_redis_client):
        """Test _get_total_redis_connections returns global counter when available."""
        # Arrange
        mock_redis_client.get.return_value = "42"

        # Act
        result = await sse_manager._get_total_redis_connections()

        # Assert
        assert result == 42
        mock_redis_client.get.assert_called_once_with("global:sse_connections_count")

    @pytest.mark.asyncio
    async def test_get_total_redis_connections_negative_counter_fallback(self, sse_manager, mock_redis_client):
        """Test _get_total_redis_connections rebuilds when global counter is negative."""

        # Arrange
        # Mock scan_iter for fallback
        async def mock_scan_iter(match):
            yield "user:123:sse_conns"
            yield "user:456:sse_conns"

        mock_redis_client.scan_iter = mock_scan_iter
        # Configure side_effect properly: global counter (-5), then individual counters (2, 3)
        mock_redis_client.get.side_effect = ["-5", "2", "3"]
        mock_redis_client.setex = AsyncMock()

        # Act
        result = await sse_manager._get_total_redis_connections()

        # Assert
        assert result == 5  # 2 + 3 from individual counters
        mock_redis_client.setex.assert_called_once_with("global:sse_connections_count", 3600, 5)

    @pytest.mark.asyncio
    async def test_get_total_redis_connections_missing_counter_fallback(self, sse_manager, mock_redis_client):
        """Test _get_total_redis_connections rebuilds when global counter is missing."""
        # Arrange
        mock_redis_client.get.side_effect = [None, "10", "15"]  # No global counter, then individual counters

        # Mock scan_iter for fallback
        async def mock_scan_iter(match):
            yield "user:123:sse_conns"
            yield "user:456:sse_conns"

        mock_redis_client.scan_iter = mock_scan_iter
        mock_redis_client.setex = AsyncMock()

        # Act
        result = await sse_manager._get_total_redis_connections()

        # Assert
        assert result == 25  # 10 + 15 from individual counters
        mock_redis_client.setex.assert_called_once_with("global:sse_connections_count", 3600, 25)

    @pytest.mark.asyncio
    async def test_rebuild_global_counter_success(self, sse_manager, mock_redis_client):
        """Test _rebuild_global_counter correctly aggregates individual counters."""
        # Arrange
        global_key = "global:sse_connections_count"

        # Mock scan_iter to return connection keys
        async def mock_scan_iter(match):
            yield "user:123:sse_conns"
            yield "user:456:sse_conns"
            yield "user:789:sse_conns"

        mock_redis_client.scan_iter = mock_scan_iter
        mock_redis_client.get.side_effect = ["5", "3", "7"]  # Individual counter values
        mock_redis_client.setex = AsyncMock()

        # Act
        result = await sse_manager._rebuild_global_counter(global_key)

        # Assert
        assert result == 15  # 5 + 3 + 7
        mock_redis_client.setex.assert_called_once_with(global_key, 3600, 15)

    @pytest.mark.asyncio
    async def test_rebuild_global_counter_handles_corrupted_individual_counters(self, sse_manager, mock_redis_client):
        """Test _rebuild_global_counter skips corrupted individual counters."""
        # Arrange
        global_key = "global:sse_connections_count"

        # Mock scan_iter to return connection keys
        async def mock_scan_iter(match):
            yield "user:123:sse_conns"
            yield "user:456:sse_conns"
            yield "user:789:sse_conns"

        mock_redis_client.scan_iter = mock_scan_iter
        mock_redis_client.get.side_effect = ["5", "invalid", "7"]  # One corrupted value
        mock_redis_client.setex = AsyncMock()

        # Act
        result = await sse_manager._rebuild_global_counter(global_key)

        # Assert
        assert result == 12  # 5 + 7, skipping the invalid one
        mock_redis_client.setex.assert_called_once_with(global_key, 3600, 12)

    @pytest.mark.asyncio
    async def test_scan_total_connections_success(self, sse_manager, mock_redis_client):
        """Test _scan_total_connections correctly sums individual counters."""

        # Arrange
        async def mock_scan_iter(match):
            yield "user:123:sse_conns"
            yield "user:456:sse_conns"

        mock_redis_client.scan_iter = mock_scan_iter
        mock_redis_client.get.side_effect = ["10", "20"]

        # Act
        result = await sse_manager._scan_total_connections()

        # Assert
        assert result == 30
        assert mock_redis_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_scan_total_connections_no_client(self, sse_manager):
        """Test _scan_total_connections returns 0 when no Redis client."""
        # Arrange
        sse_manager.redis_sse._pubsub_client = None

        # Act
        result = await sse_manager._scan_total_connections()

        # Assert
        assert result == 0

    @pytest.mark.asyncio
    async def test_check_connection_limit_lua_script_success(self, sse_manager, mock_redis_client, sample_user_id):
        """Test _check_connection_limit succeeds with Lua script."""
        # Arrange
        mock_redis_client.eval = AsyncMock(return_value=[1, 1])  # new_count=1, success=1

        # Act - Should not raise exception
        await sse_manager._check_connection_limit(sample_user_id)

        # Assert
        mock_redis_client.eval.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_limit_lua_script_over_limit(self, sse_manager, mock_redis_client, sample_user_id):
        """Test _check_connection_limit raises 429 when over limit."""
        from fastapi import HTTPException

        # Arrange
        mock_redis_client.eval = AsyncMock(return_value=[2, 0])  # current=2, success=0 (over limit)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await sse_manager._check_connection_limit(sample_user_id)

        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers

    @pytest.mark.asyncio
    async def test_check_connection_limit_lua_script_invalid_result(
        self, sse_manager, mock_redis_client, sample_user_id
    ):
        """Test _check_connection_limit handles invalid Lua script results."""
        # Arrange
        mock_redis_client.eval = AsyncMock(return_value=["invalid", "result"])  # Invalid types
        mock_redis_client.incr = AsyncMock(return_value=1)
        mock_redis_client.expire = AsyncMock()

        # Act - Should fallback to non-atomic implementation
        await sse_manager._check_connection_limit(sample_user_id)

        # Assert - Fallback methods were called
        assert mock_redis_client.incr.call_count == 2  # User and global counters
        mock_redis_client.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_limit_lua_script_empty_result(self, sse_manager, mock_redis_client, sample_user_id):
        """Test _check_connection_limit handles empty Lua script results."""
        # Arrange
        mock_redis_client.eval = AsyncMock(return_value=[])  # Empty result
        mock_redis_client.incr = AsyncMock(return_value=1)
        mock_redis_client.expire = AsyncMock()

        # Act - Should fallback to non-atomic implementation
        await sse_manager._check_connection_limit(sample_user_id)

        # Assert - Fallback methods were called
        assert mock_redis_client.incr.call_count == 2  # User and global counters
        mock_redis_client.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_limit_fallback_over_limit(self, sse_manager, mock_redis_client, sample_user_id):
        """Test _check_connection_limit fallback raises 429 when over limit."""
        from fastapi import HTTPException

        # Arrange
        mock_redis_client.eval = AsyncMock(side_effect=AttributeError("eval not supported"))
        mock_redis_client.incr = AsyncMock(side_effect=[3, 42])  # User counter over limit
        mock_redis_client.expire = AsyncMock()

        # Mock safe_decr_counter on the redis_counter_service for rollback
        sse_manager.redis_counter_service.safe_decr_counter = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await sse_manager._check_connection_limit(sample_user_id)

        assert exc_info.value.status_code == 429
        sse_manager.redis_counter_service.safe_decr_counter.assert_called_once_with(sample_user_id)

    @pytest.mark.asyncio
    async def test_periodic_cleanup_start_and_stop(self, sse_manager):
        """Test that periodic cleanup can be started and stopped correctly."""
        # Initially not running
        assert not await sse_manager.is_periodic_cleanup_running()

        # Start periodic cleanup
        await sse_manager.start_periodic_cleanup()
        assert await sse_manager.is_periodic_cleanup_running()

        # Try to start again (should not error, just log warning)
        await sse_manager.start_periodic_cleanup()
        assert await sse_manager.is_periodic_cleanup_running()

        # Stop periodic cleanup
        await sse_manager.stop_periodic_cleanup()
        assert not await sse_manager.is_periodic_cleanup_running()

        # Stop again (should not error)
        await sse_manager.stop_periodic_cleanup()
        assert not await sse_manager.is_periodic_cleanup_running()

    @pytest.mark.asyncio
    async def test_periodic_cleanup_disabled_by_config(self, configured_redis_sse_service):
        """Test that periodic cleanup respects configuration disable flag."""
        from src.services.sse.config import sse_config

        # Temporarily disable periodic cleanup
        original_enabled = sse_config.ENABLE_PERIODIC_CLEANUP
        sse_config.ENABLE_PERIODIC_CLEANUP = False

        try:
            manager = SSEConnectionManager(configured_redis_sse_service)
            await manager.start_periodic_cleanup()

            # Should not be running when disabled
            assert not await manager.is_periodic_cleanup_running()
        finally:
            # Restore original setting
            sse_config.ENABLE_PERIODIC_CLEANUP = original_enabled

    @pytest.mark.asyncio
    async def test_cleanup_stale_connections_with_batch_size(self, sse_manager, sample_user_id):
        """Test that cleanup respects batch size limits."""
        from datetime import UTC, datetime

        # Create multiple stale connections beyond batch size
        batch_size = 3
        total_stale = 5

        # Create old timestamp beyond threshold
        old_time = datetime.now(UTC).timestamp() - (sse_config.STALE_CONNECTION_THRESHOLD_SECONDS + 100)

        for i in range(total_stale):
            conn_id = f"stale-conn-{i}"
            old_datetime = datetime.fromtimestamp(old_time, tz=UTC)
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=old_datetime,
                last_activity_at=old_datetime,  # Set as stale (old activity time)
                last_event_id=None,
            )
            sse_manager.connections[conn_id] = connection_state

        # Run cleanup with batch size limit
        cleaned = await sse_manager.cleanup_stale_connections(batch_size=batch_size)

        # Should only clean up batch_size connections
        assert cleaned == batch_size
        assert len(sse_manager.connections) == total_stale - batch_size

    @pytest.mark.asyncio
    async def test_periodic_cleanup_worker_handles_errors(self, sse_manager, caplog):
        """Test that periodic cleanup worker handles errors gracefully."""
        import asyncio
        from unittest.mock import AsyncMock

        # Mock cleanup to raise an error once, then succeed
        original_cleanup = sse_manager.cleanup_stale_connections
        call_count = 0

        async def mock_cleanup(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Test error during cleanup")
            return 0

        sse_manager.cleanup_stale_connections = AsyncMock(side_effect=mock_cleanup)

        # Start cleanup and let it run briefly
        await sse_manager.start_periodic_cleanup()

        # Let it run for a short time to trigger the error
        await asyncio.sleep(0.1)

        # Stop cleanup
        await sse_manager.stop_periodic_cleanup()

        # Restore original method
        sse_manager.cleanup_stale_connections = original_cleanup

        # Verify error was logged but cleanup continued
        assert "Error during periodic SSE cleanup" in caplog.text
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_get_connection_count_includes_cleanup_status(self, sse_manager):
        """Test that connection count includes cleanup task status."""
        # Initially not running
        stats = await sse_manager.get_connection_count()
        assert "cleanup_task_running" in stats
        assert stats["cleanup_task_running"] is False

        # Start cleanup
        await sse_manager.start_periodic_cleanup()
        stats = await sse_manager.get_connection_count()
        assert stats["cleanup_task_running"] is True

        # Stop cleanup
        await sse_manager.stop_periodic_cleanup()
        stats = await sse_manager.get_connection_count()
        assert stats["cleanup_task_running"] is False

    @pytest.mark.asyncio
    async def test_get_cleanup_statistics(self, sse_manager):
        """Test that cleanup statistics are properly tracked and reported."""
        # Initially no cleanup stats
        stats = await sse_manager.state_manager.get_cleanup_statistics()
        assert stats["total_cleanups"] == 0
        assert stats["total_connections_cleaned"] == 0
        assert stats["error_rate"] == 0.0
        assert stats["failed_connections"] == 0
        assert stats["connection_failure_rate"] == 0.0

        # Add some stale connections and run cleanup
        from datetime import UTC, datetime

        old_time = datetime.now(UTC).timestamp() - (sse_config.STALE_CONNECTION_THRESHOLD_SECONDS + 100)

        for i in range(3):
            conn_id = f"stale-conn-{i}"
            old_datetime = datetime.fromtimestamp(old_time, tz=UTC)
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=old_datetime,
                last_activity_at=old_datetime,
                last_event_id=None,
            )
            sse_manager.connections[conn_id] = connection_state

        # Run cleanup
        cleaned = await sse_manager.cleanup_stale_connections()
        assert cleaned == 3

        # Verify stats are updated
        stats = await sse_manager.state_manager.get_cleanup_statistics()
        assert stats["total_cleanups"] == 1
        assert stats["total_connections_cleaned"] == 3
        assert stats["cleanup_errors"] == 0
        assert stats["failed_connections"] == 0
        assert stats["connection_failure_rate"] == 0.0
        assert stats["connections_per_cleanup"] == 3.0
        assert stats["last_cleanup_duration_ms"] > 0
        assert stats["last_cleanup_at"] is not None

    @pytest.mark.asyncio
    async def test_detailed_monitoring_stats(self, sse_manager):
        """Test comprehensive monitoring statistics for dashboard integration."""
        # Add some connections with different ages
        now = datetime.now(UTC)
        connections_data = [
            ("conn-1", "user-1", now, now),  # Fresh connection
            ("conn-2", "user-2", now - timedelta(hours=2), now - timedelta(minutes=5)),  # Long-lived, recent activity
            ("conn-3", "user-3", now - timedelta(hours=8), now - timedelta(hours=7)),  # Very old, stale
        ]

        for conn_id, user_id, connected_at, last_activity in connections_data:
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=user_id,
                connected_at=connected_at,
                last_activity_at=last_activity,
                last_event_id=None,
            )
            sse_manager.connections[conn_id] = connection_state

        # Get detailed monitoring stats
        detailed_stats = await sse_manager.get_detailed_monitoring_stats()

        # Verify structure
        assert "timestamp" in detailed_stats
        assert "service_name" in detailed_stats
        assert "connection_stats" in detailed_stats
        assert "cleanup_stats" in detailed_stats
        assert "health_indicators" in detailed_stats
        assert "performance_metrics" in detailed_stats
        assert "configuration" in detailed_stats

        # Verify connection stats
        connection_stats = detailed_stats["connection_stats"]
        assert connection_stats["active_connections"] == 3

        # Verify cleanup stats include age analysis
        cleanup_stats = detailed_stats["cleanup_stats"]
        assert "stale" in cleanup_stats
        assert "active" in cleanup_stats
        assert "long_lived" in cleanup_stats
        assert "very_old" in cleanup_stats
        assert "failed_connections" in cleanup_stats
        assert "connection_failure_rate" in cleanup_stats

        # Verify health indicators
        health_indicators = detailed_stats["health_indicators"]
        assert "overall_health" in health_indicators
        assert "alerts" in health_indicators
        assert "warnings" in health_indicators

        # Verify performance metrics surface success/error rates
        performance_metrics = detailed_stats["performance_metrics"]
        assert "cleanup_efficiency_rate" in performance_metrics
        assert "cleanup_error_rate" in performance_metrics

        # Verify configuration is included
        config = detailed_stats["configuration"]
        assert config["cleanup_interval_seconds"] == sse_config.CLEANUP_INTERVAL_SECONDS
        assert config["periodic_cleanup_enabled"] == sse_config.ENABLE_PERIODIC_CLEANUP

    @pytest.mark.asyncio
    async def test_health_indicators_alerts(self, sse_manager):
        """Test that health indicators properly detect alert conditions."""
        # Mock Redis connection count mismatch
        sse_manager.redis_counter_service.get_total_redis_connections = AsyncMock(return_value=0)

        # Add only 10 active connections (40 connection mismatch)
        for i in range(10):
            conn_id = f"conn-{i}"
            now = datetime.now(UTC)
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=now,
                last_activity_at=now,
                last_event_id=None,
            )
            sse_manager.connections[conn_id] = connection_state

        # Set high error rate in cleanup stats
        sse_manager.state_manager._cleanup_stats["total_cleanups"] = 10
        sse_manager.state_manager._cleanup_stats["cleanup_errors"] = 2  # 20% error rate

        # Get health indicators
        detailed_stats = await sse_manager.get_detailed_monitoring_stats()
        health_indicators = detailed_stats["health_indicators"]

        # Should detect connection mismatch alert
        alerts = health_indicators["alerts"]
        alert_types = [alert["type"] for alert in alerts]
        assert "redis_counter_underreporting" in alert_types

        # Should detect high cleanup error rate alert
        assert "high_cleanup_error_rate" in alert_types

        # Overall health should be degraded or unhealthy
        assert health_indicators["overall_health"] in ["degraded", "unhealthy"]

    @pytest.mark.asyncio
    async def test_connection_age_analysis(self, sse_manager):
        """Test connection age analysis for monitoring insights."""
        now = datetime.now(UTC)
        cutoff_time = now.timestamp() - sse_config.STALE_CONNECTION_THRESHOLD_SECONDS

        # Create connections with different ages
        connections = [
            # Stale connection (old activity)
            SSEConnectionState(
                connection_id="stale-1",
                user_id="user-1",
                connected_at=now - timedelta(hours=1),
                last_activity_at=now - timedelta(seconds=sse_config.STALE_CONNECTION_THRESHOLD_SECONDS + 60),
                last_event_id=None,
            ),
            # Active connection (recent activity)
            SSEConnectionState(
                connection_id="active-1",
                user_id="user-2",
                connected_at=now - timedelta(minutes=30),
                last_activity_at=now - timedelta(minutes=1),
                last_event_id=None,
            ),
            # Long-lived active connection
            SSEConnectionState(
                connection_id="long-lived-1",
                user_id="user-3",
                connected_at=now - timedelta(hours=2),
                last_activity_at=now - timedelta(minutes=5),
                last_event_id=None,
            ),
            # Very old connection (6+ hours)
            SSEConnectionState(
                connection_id="very-old-1",
                user_id="user-4",
                connected_at=now - timedelta(hours=8),
                last_activity_at=now - timedelta(minutes=2),
                last_event_id=None,
            ),
        ]

        # Add connections to manager
        for conn in connections:
            sse_manager.connections[conn.connection_id] = conn

        # Analyze connection ages
        age_analysis = sse_manager.state_manager._analyze_connection_ages(cutoff_time)

        # Verify categorization
        assert age_analysis["stale"] == 1
        assert age_analysis["active"] == 3  # active-1, long-lived-1, very-old-1
        assert age_analysis["long_lived"] == 2  # long-lived-1, very-old-1
        assert age_analysis["very_old"] == 1  # very-old-1

    @pytest.mark.asyncio
    async def test_config_validation_warnings(self, sse_manager, caplog):
        """Test that configuration validation properly warns about suboptimal settings."""
        # The validation happens during initialization, so we need to create a new manager
        # with modified config to test warnings

        original_cleanup_interval = sse_config.CLEANUP_INTERVAL_SECONDS
        original_batch_size = sse_config.CLEANUP_BATCH_SIZE

        try:
            # Test very short cleanup interval warning
            sse_config.CLEANUP_INTERVAL_SECONDS = 5  # Less than 10
            sse_config.CLEANUP_BATCH_SIZE = 150  # Greater than 100

            # Create new manager to trigger validation
            from src.services.sse.redis_counter import RedisCounterService
            from src.services.sse.connection_state import SSEConnectionStateManager

            test_counter_service = RedisCounterService(sse_manager.redis_counter_service._pubsub_client)
            test_state_manager = SSEConnectionStateManager(test_counter_service)
            # Trigger validation by accessing a method
            _ = test_state_manager

            # Check that warnings were logged
            assert "very short" in caplog.text or "very large" in caplog.text

        finally:
            # Restore original config
            sse_config.CLEANUP_INTERVAL_SECONDS = original_cleanup_interval
            sse_config.CLEANUP_BATCH_SIZE = original_batch_size

    @pytest.mark.asyncio
    async def test_cleanup_unlimited_batch_size(self, sse_manager):
        """Test that unlimited batch size cleans all stale connections."""
        from datetime import UTC, datetime

        # Create many stale connections (more than default batch size)
        stale_count = 15  # More than default batch size of 10
        old_time = datetime.now(UTC).timestamp() - (sse_config.STALE_CONNECTION_THRESHOLD_SECONDS + 100)

        for i in range(stale_count):
            conn_id = f"stale-conn-{i}"
            old_datetime = datetime.fromtimestamp(old_time, tz=UTC)
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=old_datetime,
                last_activity_at=old_datetime,
                last_event_id=None,
            )
            sse_manager.connections[conn_id] = connection_state

        # Test limited batch size first
        cleaned_limited = await sse_manager.cleanup_stale_connections(batch_size=5)
        assert cleaned_limited == 5
        assert len(sse_manager.connections) == stale_count - 5

        # Test unlimited batch size
        cleaned_unlimited = await sse_manager.cleanup_stale_connections(batch_size=None)
        assert cleaned_unlimited == stale_count - 5  # Remaining connections
        assert len(sse_manager.connections) == 0

    @pytest.mark.asyncio
    async def test_complete_shutdown_cleanup(self, sse_manager):
        """Test complete shutdown cleanup for all stale connections."""
        from datetime import UTC, datetime

        # Create many stale connections that would require multiple iterations
        # if using batch size, but should be cleaned in one iteration with unlimited batch
        total_stale = 25
        old_time = datetime.now(UTC).timestamp() - (sse_config.STALE_CONNECTION_THRESHOLD_SECONDS + 100)

        for i in range(total_stale):
            conn_id = f"stale-conn-{i}"
            old_datetime = datetime.fromtimestamp(old_time, tz=UTC)
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=old_datetime,
                last_activity_at=old_datetime,
                last_event_id=None,
            )
            sse_manager.connections[conn_id] = connection_state

        # Run complete shutdown cleanup
        summary = await sse_manager.cleanup_all_stale_connections_for_shutdown()

        # Verify all connections were cleaned
        assert summary["total_cleaned"] == total_stale
        assert summary["connections_before"] == total_stale
        assert summary["connections_after"] == 0
        assert summary["iterations"] >= 1
        assert not summary["max_iterations_reached"]
        assert summary["cleanup_duration_ms"] > 0

        # Verify no connections remain
        assert len(sse_manager.connections) == 0

    @pytest.mark.asyncio
    async def test_shutdown_cleanup_with_active_connections(self, sse_manager):
        """Test that shutdown cleanup only removes stale connections, not active ones."""
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        old_time = now.timestamp() - (sse_config.STALE_CONNECTION_THRESHOLD_SECONDS + 100)

        # Create mix of stale and active connections
        stale_count = 10
        active_count = 5

        # Add stale connections
        for i in range(stale_count):
            conn_id = f"stale-conn-{i}"
            old_datetime = datetime.fromtimestamp(old_time, tz=UTC)
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"stale-user-{i}",
                connected_at=old_datetime,
                last_activity_at=old_datetime,
                last_event_id=None,
            )
            sse_manager.connections[conn_id] = connection_state

        # Add active connections
        for i in range(active_count):
            conn_id = f"active-conn-{i}"
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"active-user-{i}",
                connected_at=now,
                last_activity_at=now,
                last_event_id=None,
            )
            sse_manager.connections[conn_id] = connection_state

        # Run shutdown cleanup
        summary = await sse_manager.cleanup_all_stale_connections_for_shutdown()

        # Verify only stale connections were cleaned
        assert summary["total_cleaned"] == stale_count
        assert summary["connections_after"] == active_count
        assert len(sse_manager.connections) == active_count

        # Verify remaining connections are the active ones
        remaining_ids = set(sse_manager.connections.keys())
        expected_active_ids = {f"active-conn-{i}" for i in range(active_count)}
        assert remaining_ids == expected_active_ids

    @pytest.mark.asyncio
    async def test_shutdown_cleanup_max_iterations_protection(self, sse_manager):
        """Test that shutdown cleanup respects max iterations limit."""
        from unittest.mock import AsyncMock

        # Mock cleanup_stale_connections to always return 1 (simulating persistent connections)
        original_cleanup = sse_manager.state_manager.cleanup_stale_connections

        call_count = 0

        async def mock_cleanup(**kwargs):
            nonlocal call_count
            call_count += 1
            # Return 1 for first few calls, then 0 to eventually stop
            return 1 if call_count <= 3 else 0

        sse_manager.state_manager.cleanup_stale_connections = AsyncMock(side_effect=mock_cleanup)

        # Run with low max_iterations
        summary = await sse_manager.cleanup_all_stale_connections_for_shutdown(max_iterations=2)

        # Should stop at max iterations
        assert summary["iterations"] == 2
        assert summary["max_iterations_reached"] is True
        assert summary["total_cleaned"] == 2  # Called twice, returned 1 each time

        # Restore original method
        sse_manager.state_manager.cleanup_stale_connections = original_cleanup

    @pytest.mark.asyncio
    async def test_shutdown_cleanup_no_stale_connections(self, sse_manager):
        """Test shutdown cleanup when no stale connections exist."""
        from datetime import UTC, datetime

        # Add only active connections
        now = datetime.now(UTC)
        for i in range(3):
            conn_id = f"active-conn-{i}"
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=now,
                last_activity_at=now,
                last_event_id=None,
            )
            sse_manager.connections[conn_id] = connection_state

        # Run shutdown cleanup
        summary = await sse_manager.cleanup_all_stale_connections_for_shutdown()

        # Should complete immediately with no cleanups
        assert summary["total_cleaned"] == 0
        assert summary["iterations"] == 1
        assert summary["connections_before"] == 3
        assert summary["connections_after"] == 3
        assert not summary["max_iterations_reached"]

    @pytest.mark.asyncio
    async def test_cleanup_stale_connections_zero_batch_size(self, sse_manager):
        """Test that zero or negative batch size falls back to default."""
        from datetime import UTC, datetime

        # Create some stale connections
        old_time = datetime.now(UTC).timestamp() - (sse_config.STALE_CONNECTION_THRESHOLD_SECONDS + 100)

        for i in range(5):
            conn_id = f"stale-conn-{i}"
            old_datetime = datetime.fromtimestamp(old_time, tz=UTC)
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=old_datetime,
                last_activity_at=old_datetime,
                last_event_id=None,
            )
            sse_manager.connections[conn_id] = connection_state

        # Test with zero batch size (should use default)
        cleaned = await sse_manager.cleanup_stale_connections(batch_size=0)
        assert cleaned == min(5, sse_config.CLEANUP_BATCH_SIZE)  # Should respect default batch size

        # Add more connections for negative test
        for i in range(5, 10):
            conn_id = f"stale-conn-{i}"
            old_datetime = datetime.fromtimestamp(old_time, tz=UTC)
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=old_datetime,
                last_activity_at=old_datetime,
                last_event_id=None,
            )
            sse_manager.connections[conn_id] = connection_state

        # Test with negative batch size (should use default)
        remaining_before_cleanup = len(sse_manager.connections)  # Get count BEFORE cleanup
        cleaned = await sse_manager.cleanup_stale_connections(batch_size=-1)
        expected_cleaned = min(remaining_before_cleanup, sse_config.CLEANUP_BATCH_SIZE)
        assert cleaned == expected_cleaned

    @pytest.mark.asyncio
    async def test_shutdown_cleanup_monitoring_stats(self, sse_manager):
        """Test that shutdown cleanup updates monitoring statistics correctly."""
        from datetime import UTC, datetime

        # Get initial stats
        initial_stats = await sse_manager.state_manager.get_cleanup_statistics()
        initial_shutdown_cleanups = initial_stats["shutdown_cleanups"]
        initial_shutdown_connections_cleaned = initial_stats["shutdown_connections_cleaned"]

        # Create stale connections
        old_time = datetime.now(UTC).timestamp() - (sse_config.STALE_CONNECTION_THRESHOLD_SECONDS + 100)
        stale_count = 8

        for i in range(stale_count):
            conn_id = f"stale-conn-{i}"
            old_datetime = datetime.fromtimestamp(old_time, tz=UTC)
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=old_datetime,
                last_activity_at=old_datetime,
                last_event_id=None,
            )
            sse_manager.connections[conn_id] = connection_state

        # Run shutdown cleanup
        summary = await sse_manager.cleanup_all_stale_connections_for_shutdown()

        # Verify statistics were updated
        updated_stats = await sse_manager.state_manager.get_cleanup_statistics()

        assert updated_stats["shutdown_cleanups"] == initial_shutdown_cleanups + 1
        assert updated_stats["shutdown_connections_cleaned"] == initial_shutdown_connections_cleaned + stale_count
        assert updated_stats["last_shutdown_cleanup_summary"] == summary

        # Verify summary details are preserved in stats
        assert updated_stats["last_shutdown_cleanup_summary"]["total_cleaned"] == stale_count
        assert updated_stats["last_shutdown_cleanup_summary"]["connections_before"] == stale_count
        assert updated_stats["last_shutdown_cleanup_summary"]["connections_after"] == 0
