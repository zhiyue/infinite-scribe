"""SSE Connection State Manager for tracking connection state."""

import asyncio
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
    last_activity_at: datetime = Field(..., description="Last activity timestamp (events, heartbeat)")
    last_event_id: str | None = Field(None, description="Last processed event ID for reconnection")
    channel_subscriptions: list[str] = Field(default_factory=list, description="Subscribed channels")

    def update_activity(self) -> None:
        """Update the last activity timestamp to current time."""
        self.last_activity_at = datetime.now(UTC)


class SSEConnectionStateManager:
    """Service for managing SSE connection state and cleanup operations."""

    def __init__(self, redis_counter_service: RedisCounterService):
        """Initialize with Redis counter service."""
        self.redis_counter_service = redis_counter_service
        self.connections: dict[str, SSEConnectionState] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._cleanup_running = False

    def create_connection_state(self, user_id: str, last_event_id: str | None = None) -> tuple[str, SSEConnectionState]:
        """Create and store a new connection state."""
        connection_id = str(uuid4())
        now = datetime.now(UTC)
        connection_state = SSEConnectionState(
            connection_id=connection_id,
            user_id=user_id,
            connected_at=now,
            last_activity_at=now,  # Initialize with current time
            last_event_id=last_event_id,
        )
        self.connections[connection_id] = connection_state
        return connection_id, connection_state

    def get_connection_state(self, connection_id: str) -> SSEConnectionState | None:
        """Get connection state by connection ID."""
        return self.connections.get(connection_id)

    def update_connection_activity(self, connection_id: str) -> bool:
        """
        Update the last activity timestamp for a connection.

        Args:
            connection_id: Connection ID to update

        Returns:
            bool: True if connection was found and updated, False otherwise
        """
        connection_state = self.connections.get(connection_id)
        if connection_state:
            connection_state.update_activity()
            return True
        return False

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

    async def cleanup_stale_connections(self, batch_size: int | None = None) -> int:
        """
        Garbage collection for zombie connections based on last activity time.

        This method only cleans up connections that have been inactive for longer
        than the threshold. It uses last_activity_at instead of connected_at to
        avoid mistakenly cleaning active long-lived connections.

        Args:
            batch_size: Maximum number of connections to clean in one batch.
                       Defaults to CLEANUP_BATCH_SIZE from config.

        Returns:
            int: Number of stale connections cleaned up
        """
        if batch_size is None:
            batch_size = sse_config.CLEANUP_BATCH_SIZE

        stale_count = 0
        cutoff_time = datetime.now(UTC).timestamp() - sse_config.STALE_CONNECTION_THRESHOLD_SECONDS

        # Identify potentially stale connections based on last activity
        stale_connection_ids = []
        for connection_id, connection_state in self.connections.items():
            if connection_state.last_activity_at.timestamp() < cutoff_time:
                stale_connection_ids.append(connection_id)
                if len(stale_connection_ids) >= batch_size:
                    break

        # Clean up stale connections
        for connection_id in stale_connection_ids:
            connection_state = self.connections.get(connection_id)
            if connection_state:
                await self.cleanup_connection(connection_id, connection_state.user_id)
                stale_count += 1

        if stale_count > 0:
            logger.info(
                "Cleaned up %s inactive SSE connections (no activity for >%ss)",
                stale_count,
                sse_config.STALE_CONNECTION_THRESHOLD_SECONDS,
            )

        return stale_count

    async def start_periodic_cleanup(self) -> None:
        """Start the periodic cleanup background task."""
        if not sse_config.ENABLE_PERIODIC_CLEANUP:
            logger.info("Periodic SSE cleanup is disabled by configuration")
            return

        if self._cleanup_task is not None and not self._cleanup_task.done():
            logger.warning("Periodic cleanup already running")
            return

        logger.info(f"Starting periodic SSE cleanup every {sse_config.CLEANUP_INTERVAL_SECONDS} seconds")
        self._cleanup_running = True
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup_worker())

    async def stop_periodic_cleanup(self) -> None:
        """Stop the periodic cleanup background task."""
        if self._cleanup_task is None:
            return

        logger.info("Stopping periodic SSE cleanup")
        self._cleanup_running = False

        if not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                logger.debug("Periodic cleanup task cancelled successfully")

        self._cleanup_task = None

    async def _periodic_cleanup_worker(self) -> None:
        """Background worker for periodic cleanup of stale connections."""
        logger.info("Periodic SSE cleanup worker started")

        try:
            while self._cleanup_running:
                try:
                    # Run cleanup with batch size limit
                    cleaned = await self.cleanup_stale_connections()

                    if cleaned > 0:
                        logger.info(f"Periodic cleanup removed {cleaned} stale SSE connections")
                    else:
                        logger.debug("No stale SSE connections found during periodic cleanup")

                except Exception as e:
                    logger.error(f"Error during periodic SSE cleanup: {e}", exc_info=True)

                # Wait for next cleanup interval
                await asyncio.sleep(sse_config.CLEANUP_INTERVAL_SECONDS)

        except asyncio.CancelledError:
            logger.info("Periodic SSE cleanup worker stopped")
            raise
        except Exception as e:
            logger.error(f"Periodic SSE cleanup worker failed: {e}", exc_info=True)
            raise

    async def get_connection_count(self) -> dict[str, int]:
        """
        Get connection statistics for monitoring.

        Returns connection counts from both in-memory tracking and Redis counters
        for comprehensive monitoring and debugging.

        Returns:
            dict: Connection statistics with keys:
                - active_connections: In-memory tracked connections
                - redis_connection_counters: Sum of all Redis connection counters
                - cleanup_task_running: Whether periodic cleanup is active
        """
        active_conns = len(self.connections)
        total_redis_conns = await self.redis_counter_service.get_total_redis_connections()
        cleanup_running = self._cleanup_task is not None and not self._cleanup_task.done()

        return {
            "active_connections": active_conns,
            "redis_connection_counters": total_redis_conns,
            "cleanup_task_running": cleanup_running,
        }
