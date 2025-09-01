"""SSE Connection State Manager for tracking connection state."""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .config import sse_config
from .redis_counter import RedisCounterService

logger = logging.getLogger(__name__)


class SSEConnectionState(BaseModel):
    """SSE connection state model for tracking active connections."""

    connection_id: str = Field(..., description="Unique connection identifier")
    user_id: str = Field(..., description="User ID associated with connection")
    connected_at: datetime = Field(..., description="Connection timestamp")
    last_event_id: str | None = Field(None, description="Last processed event ID for reconnection")
    channel_subscriptions: list[str] = Field(default_factory=list, description="Subscribed channels")


class SSEConnectionStateManager:
    """Service for managing SSE connection state and cleanup operations."""

    def __init__(self, redis_counter_service: RedisCounterService):
        """Initialize with Redis counter service."""
        self.redis_counter_service = redis_counter_service
        self.connections: dict[str, SSEConnectionState] = {}

    def create_connection_state(self, user_id: str, last_event_id: str | None = None) -> tuple[str, SSEConnectionState]:
        """Create and store a new connection state."""
        connection_id = str(uuid4())
        connection_state = SSEConnectionState(
            connection_id=connection_id,
            user_id=user_id,
            connected_at=datetime.now(UTC),
            last_event_id=last_event_id,
        )
        self.connections[connection_id] = connection_state
        return connection_id, connection_state

    def get_connection_state(self, connection_id: str) -> SSEConnectionState | None:
        """Get connection state by connection ID."""
        return self.connections.get(connection_id)

    async def cleanup_connection(self, connection_id: str, user_id: str) -> None:
        """
        Clean up connection resources and Redis counters.

        This method ensures proper resource cleanup:
        1. Removes connection from memory tracking
        2. Decrements Redis connection counter (with negative protection)
        3. sse-starlette handles heartbeat/ping cleanup automatically

        Args:
            connection_id: Connection ID to clean up
            user_id: User ID associated with connection
        """
        # Clean up memory connection record
        self.connections.pop(connection_id, None)

        # Decrement Redis connection counter (with negative protection)
        await self.redis_counter_service.safe_decr_counter(user_id)

        logger.debug(f"Cleaned up SSE connection {connection_id} for user {user_id}")

    async def cleanup_stale_connections(self) -> int:
        """
        Garbage collection for zombie connections.

        With sse-starlette, client disconnections are detected automatically via
        request.is_disconnected(), so this method primarily cleans up memory-only
        connection tracking for connections that may have been missed.

        Returns:
            int: Number of stale connections cleaned up
        """
        stale_count = 0
        cutoff_time = datetime.now(UTC).timestamp() - sse_config.STALE_CONNECTION_THRESHOLD_SECONDS

        # Identify stale connections
        stale_connection_ids = [
            connection_id
            for connection_id, connection_state in self.connections.items()
            if connection_state.connected_at.timestamp() < cutoff_time
        ]

        # Clean up stale connections
        for connection_id in stale_connection_ids:
            connection_state = self.connections.get(connection_id)
            if connection_state:
                await self.cleanup_connection(connection_id, connection_state.user_id)
                stale_count += 1

        if stale_count > 0:
            logger.info(f"Cleaned up {stale_count} stale SSE connections from memory")

        return stale_count

    async def get_connection_count(self) -> dict[str, int]:
        """
        Get connection statistics for monitoring.

        Returns connection counts from both in-memory tracking and Redis counters
        for comprehensive monitoring and debugging.

        Returns:
            dict: Connection statistics with keys:
                - active_connections: In-memory tracked connections
                - redis_connection_counters: Sum of all Redis connection counters
        """
        active_conns = len(self.connections)
        total_redis_conns = await self.redis_counter_service.get_total_redis_connections()

        return {"active_connections": active_conns, "redis_connection_counters": total_redis_conns}
