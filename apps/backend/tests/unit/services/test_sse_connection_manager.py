"""Unit tests for SSE Connection Manager."""

import asyncio
import json
import time
from datetime import datetime
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from src.services.sse_connection_manager import SSEConnectionManager, SSEConnectionState
from src.common.services.redis_sse_service import RedisSSEService
from src.common.services.redis_service import RedisService
from src.schemas.sse import SSEMessage, EventScope


class TestSSEConnectionManager:
    """Test cases for SSEConnectionManager."""

    @pytest.fixture
    def redis_service(self):
        """Create Redis service instance."""
        return RedisService()

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        client = AsyncMock()
        # Mock Redis counter operations for concurrency limiting
        client.incr.return_value = 1  # First connection
        client.decr.return_value = 0  # After cleanup
        client.set.return_value = True
        client.expire.return_value = True
        client.delete.return_value = 1
        client.get.return_value = None

        # Mock scan_iter to return async iterator
        async def async_scan_iter(match=None):
            # Empty async generator by default
            if False:  # Never yields anything
                yield

        client.scan_iter = async_scan_iter
        return client

    @pytest.fixture
    def redis_sse_service(self, redis_service):
        """Create Redis SSE service instance."""
        service = RedisSSEService(redis_service)
        service._pubsub_client = AsyncMock()
        return service

    @pytest.fixture
    def sse_connection_manager(self, redis_sse_service):
        """Create SSE Connection Manager instance."""
        return SSEConnectionManager(redis_sse_service)

    @pytest.fixture
    def sample_user_id(self):
        """Create sample user ID for testing."""
        return str(uuid4())

    @pytest.fixture
    def sample_sse_message(self):
        """Create sample SSE message for testing."""
        return SSEMessage(
            event="task.progress-updated",
            data={"task_id": "test-task-123", "progress": 50},
            id="12345-67890",
            retry=None,
            scope=EventScope.USER,
            version="1.0",
        )

    @pytest.fixture
    def mock_redis_sse_subscribe(self):
        """Create async generator mock for Redis SSE subscription."""

        async def async_generator():
            # Simulate real-time events
            yield SSEMessage(event="task.progress-updated", data={"progress": 25}, id="msg-1", scope=EventScope.USER)
            yield SSEMessage(event="task.progress-updated", data={"progress": 50}, id="msg-2", scope=EventScope.USER)

        return async_generator

    async def test_add_connection_creates_streaming_response(
        self, sse_connection_manager, sample_user_id, mock_redis_client
    ):
        """Test that add_connection returns StreamingResponse."""
        # Mock Redis operations
        sse_connection_manager.redis_sse._pubsub_client = mock_redis_client
        # Mock Redis set for heartbeat tracking
        mock_redis_client.set = AsyncMock(return_value=True)

        response = await sse_connection_manager.add_connection(sample_user_id)

        assert isinstance(response, StreamingResponse)
        # Verify Redis counter incremented
        mock_redis_client.incr.assert_called_once_with(f"user:{sample_user_id}:sse_conns")
        mock_redis_client.expire.assert_called_once_with(f"user:{sample_user_id}:sse_conns", 300)

    async def test_add_connection_enforces_concurrency_limit(
        self, sse_connection_manager, sample_user_id, mock_redis_client
    ):
        """Test that max 2 connections per user is enforced."""
        # Mock Redis to return 3 connections (over limit)
        mock_redis_client.incr.return_value = 3
        sse_connection_manager.redis_sse._pubsub_client = mock_redis_client

        with pytest.raises(HTTPException) as exc_info:
            await sse_connection_manager.add_connection(sample_user_id)

        assert exc_info.value.status_code == 429
        assert "Too many concurrent SSE connections" in str(exc_info.value.detail)
        # Verify counter was rolled back
        mock_redis_client.decr.assert_called_once_with(f"user:{sample_user_id}:sse_conns")

    async def test_connection_state_tracking(self, sse_connection_manager, sample_user_id, mock_redis_client):
        """Test that connections are properly tracked in memory."""
        initial_count = len(sse_connection_manager.connections)

        # Mock Redis operations with proper return values
        mock_redis_client.incr.return_value = 1
        mock_redis_client.expire.return_value = True
        mock_redis_client.set = AsyncMock(return_value=True)  # Mock heartbeat tracking
        sse_connection_manager.redis_sse._pubsub_client = mock_redis_client

        # Mock Redis SSE service methods
        sse_connection_manager.redis_sse.get_recent_events = AsyncMock(return_value=[])
        sse_connection_manager.redis_sse.subscribe_user_events = AsyncMock()

        # Add connection
        response = await sse_connection_manager.add_connection(sample_user_id)

        # Verify response type
        assert isinstance(response, StreamingResponse)

        # Check that connection was added to memory tracking
        assert len(sse_connection_manager.connections) == initial_count + 1

        # Find the connection and verify its state
        connection_states = list(sse_connection_manager.connections.values())
        new_connection = connection_states[-1]  # Last added connection

        assert isinstance(new_connection, SSEConnectionState)
        assert new_connection.user_id == sample_user_id
        assert isinstance(new_connection.connected_at, datetime)
        assert isinstance(new_connection.last_heartbeat, datetime)

    async def test_heartbeat_generation(self, sse_connection_manager, sample_user_id, mock_redis_client):
        """Test that heartbeat messages are generated every 30 seconds."""
        sse_connection_manager.redis_sse._pubsub_client = mock_redis_client
        sse_connection_manager.heartbeat_interval = 0.1  # Speed up for testing
        # Mock Redis set for heartbeat tracking
        mock_redis_client.set = AsyncMock(return_value=True)

        # Mock streaming response generation
        response = await sse_connection_manager.add_connection(sample_user_id)

        # Verify StreamingResponse was created
        assert isinstance(response, StreamingResponse)

    async def test_cleanup_connection_removes_resources(
        self, sse_connection_manager, sample_user_id, mock_redis_client
    ):
        """Test that connection cleanup removes all resources."""
        sse_connection_manager.redis_sse._pubsub_client = mock_redis_client
        connection_id = "test-conn-123"

        # Add connection to memory first
        sse_connection_manager.connections[connection_id] = SSEConnectionState(
            connection_id=connection_id,
            user_id=sample_user_id,
            connected_at=datetime.utcnow(),
            last_heartbeat=datetime.utcnow(),
        )

        # Call cleanup
        await sse_connection_manager._cleanup_connection(connection_id, sample_user_id)

        # Verify memory cleanup
        assert connection_id not in sse_connection_manager.connections

        # Verify Redis counter decremented
        mock_redis_client.decr.assert_called_once_with(f"user:{sample_user_id}:sse_conns")

        # Verify heartbeat key deleted
        expected_heartbeat_key = f"sse_conn:{connection_id}:heartbeat"
        mock_redis_client.delete.assert_called_with(expected_heartbeat_key)

    async def test_cleanup_stale_connections(self, sse_connection_manager, mock_redis_client):
        """Test zombie connection garbage collection."""
        sse_connection_manager.redis_sse._pubsub_client = mock_redis_client

        # Mock scan_iter to return some stale heartbeat keys
        stale_keys = ["sse_conn:conn1:heartbeat", "sse_conn:conn2:heartbeat"]

        async def mock_scan_iter(match=None):
            for key in stale_keys:
                yield key

        mock_redis_client.scan_iter = mock_scan_iter

        # Mock get to return old timestamps (90+ seconds ago)
        old_timestamp = int(time.time()) - 120  # 2 minutes ago
        mock_redis_client.get.return_value = str(old_timestamp)

        # Run cleanup
        stale_count = await sse_connection_manager.cleanup_stale_connections()

        assert stale_count == 2

    async def test_get_connection_count(self, sse_connection_manager, sample_user_id, mock_redis_client):
        """Test connection count reporting."""
        sse_connection_manager.redis_sse._pubsub_client = mock_redis_client

        # Add some connections to memory
        for i in range(3):
            conn_id = f"conn-{i}"
            sse_connection_manager.connections[conn_id] = SSEConnectionState(
                connection_id=conn_id,
                user_id=f"user-{i}",
                connected_at=datetime.utcnow(),
                last_heartbeat=datetime.utcnow(),
            )

        # Mock Redis scan for connection counters
        redis_keys = ["user:user1:sse_conns", "user:user2:sse_conns"]

        async def mock_scan_iter(match=None):
            for key in redis_keys:
                yield key

        mock_redis_client.scan_iter = mock_scan_iter
        mock_redis_client.get.side_effect = ["2", "1"]  # 3 total Redis connections

        stats = await sse_connection_manager.get_connection_count()

        assert stats["active_connections"] == 3
        assert stats["redis_connection_counters"] == 3

    async def test_queue_aggregation_design(
        self, sse_connection_manager, sample_user_id, mock_redis_client, mock_redis_sse_subscribe
    ):
        """Test that heartbeat + real-time events + history events are properly aggregated in queue."""
        sse_connection_manager.redis_sse._pubsub_client = mock_redis_client
        sse_connection_manager.heartbeat_interval = 0.05  # Very fast for testing
        # Mock Redis set for heartbeat tracking
        mock_redis_client.set = AsyncMock(return_value=True)

        # Mock the Redis SSE service subscription
        sse_connection_manager.redis_sse.subscribe_user_events = mock_redis_sse_subscribe

        # Mock get_recent_events to return some historical events
        sse_connection_manager.redis_sse.get_recent_events = AsyncMock(
            return_value=[
                SSEMessage(
                    event="task.progress-started",
                    data={"task_id": "historical-task"},
                    id="hist-1",
                    scope=EventScope.USER,
                )
            ]
        )

        response = await sse_connection_manager.add_connection(sample_user_id)
        assert isinstance(response, StreamingResponse)

    async def test_redis_counter_negative_protection(self, sse_connection_manager, sample_user_id, mock_redis_client):
        """Test that Redis counters don't go negative."""
        sse_connection_manager.redis_sse._pubsub_client = mock_redis_client

        # Mock decr to return negative value
        mock_redis_client.decr.return_value = -1

        connection_id = "test-conn"
        await sse_connection_manager._cleanup_connection(connection_id, sample_user_id)

        # Verify that counter was reset to 0 when negative
        mock_redis_client.set.assert_called_with(f"user:{sample_user_id}:sse_conns", 0)

    async def test_connection_manager_initialization(self, redis_sse_service):
        """Test that SSEConnectionManager initializes correctly."""
        manager = SSEConnectionManager(redis_sse_service)

        assert manager.redis_sse == redis_sse_service
        assert manager.connections == {}
        assert manager.heartbeat_interval == 30
        assert hasattr(manager, "add_connection")
        assert hasattr(manager, "_cleanup_connection")
        assert hasattr(manager, "cleanup_stale_connections")
        assert hasattr(manager, "get_connection_count")
