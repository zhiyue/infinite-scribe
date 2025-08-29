"""Unit tests for SSE Connection Manager."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request
from src.common.services.redis_service import RedisService
from src.common.services.redis_sse_service import RedisSSEService
from src.schemas.sse import EventScope, SSEMessage
from src.services.sse_connection_manager import SSEConnectionManager, SSEConnectionState
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
        # Verify Redis counter incremented with expected key
        expected_key = sse_manager._get_connection_key(sample_user_id)
        sse_manager.redis_sse._pubsub_client.incr.assert_called_once_with(expected_key)
        sse_manager.redis_sse._pubsub_client.expire.assert_called_once_with(
            expected_key, sse_manager.CONNECTION_EXPIRY_SECONDS
        )

    async def test_add_connection_enforces_concurrency_limit(self, sse_manager, sample_user_id, mock_request):
        """Test that max connections per user limit is enforced using constants."""
        # Mock Redis to return over the limit
        over_limit_count = sse_manager.MAX_CONNECTIONS_PER_USER + 1
        sse_manager.redis_sse._pubsub_client.incr.return_value = over_limit_count

        with pytest.raises(HTTPException) as exc_info:
            await sse_manager.add_connection(mock_request, sample_user_id)

        assert exc_info.value.status_code == 429
        assert "Too many concurrent SSE connections" in str(exc_info.value.detail)
        # Verify counter was rolled back
        expected_key = sse_manager._get_connection_key(sample_user_id)
        sse_manager.redis_sse._pubsub_client.decr.assert_called_once_with(expected_key)

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
        sse_manager.connections[connection_id] = SSEConnectionState(
            connection_id=connection_id,
            user_id=sample_user_id,
            connected_at=datetime.now(UTC),
        )

        # Call cleanup
        await sse_manager._cleanup_connection(connection_id, sample_user_id)

        # Verify memory cleanup
        assert connection_id not in sse_manager.connections

        # Verify Redis counter decremented using helper method
        expected_key = sse_manager._get_connection_key(sample_user_id)
        sse_manager.redis_sse._pubsub_client.decr.assert_called_once_with(expected_key)

    async def test_cleanup_stale_connections_uses_constants(self, sse_manager):
        """Test zombie connection GC uses configured threshold constants."""
        # Add connections older than the threshold
        threshold_exceeded = sse_manager.STALE_CONNECTION_THRESHOLD_SECONDS + 100
        old_time = datetime.now(UTC).timestamp() - threshold_exceeded

        stale_connections_count = 2
        for i in range(stale_connections_count):
            conn_id = f"stale-conn-{i}"
            connection_state = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=datetime.fromtimestamp(old_time, tz=UTC),
            )
            sse_manager.connections[conn_id] = connection_state

        # Run cleanup
        stale_count = await sse_manager.cleanup_stale_connections()

        assert stale_count == stale_connections_count

    async def test_get_connection_count_with_helper_methods(self, sse_manager):
        """Test connection count reporting using helper methods."""
        memory_connections_count = 3
        # Add some connections to memory
        for i in range(memory_connections_count):
            conn_id = f"conn-{i}"
            sse_manager.connections[conn_id] = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=datetime.now(UTC),
            )

        # Mock Redis scan for connection counters
        redis_keys = ["user:user1:sse_conns", "user:user2:sse_conns"]
        redis_total = 3

        async def mock_scan_iter(match=None):
            for key in redis_keys:
                yield key

        sse_manager.redis_sse._pubsub_client.scan_iter = mock_scan_iter
        sse_manager.redis_sse._pubsub_client.get.side_effect = ["2", "1"]  # Total Redis connections

        stats = await sse_manager.get_connection_count()

        assert stats["active_connections"] == memory_connections_count
        assert stats["redis_connection_counters"] == redis_total

    async def test_redis_counter_negative_protection_with_helper(self, sse_manager, sample_user_id):
        """Test that Redis counters don't go negative using safe helper method."""
        # Mock decr to return negative value
        sse_manager.redis_sse._pubsub_client.decr.return_value = -1

        connection_id = "test-conn"
        await sse_manager._cleanup_connection(connection_id, sample_user_id)

        # Verify that safe decr helper was used and counter reset to 0
        expected_key = sse_manager._get_connection_key(sample_user_id)
        sse_manager.redis_sse._pubsub_client.set.assert_called_with(expected_key, 0)

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
        assert manager.RECENT_EVENTS_LIMIT == 10
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

        # Call _send_historical_events with specific since_id
        events = []
        async for event in sse_manager._send_historical_events(mock_request, sample_user_id, since_id="event-0"):
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
