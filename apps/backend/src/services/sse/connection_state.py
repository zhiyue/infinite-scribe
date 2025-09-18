"""SSE Connection State Manager for tracking connection state."""

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any
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

        # Monitoring and statistics
        self._cleanup_stats = {
            "total_cleanups": 0,
            "total_connections_cleaned": 0,
            "cleanup_errors": 0,  # cleanup runs that reported errors
            "failed_connections": 0,
            "last_cleanup_duration_ms": 0,
            "last_cleanup_at": None,
            "shutdown_cleanups": 0,
            "shutdown_connections_cleaned": 0,
            "last_shutdown_cleanup_summary": None,
        }

        # Validate configuration on startup
        self._validate_config()

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

        # Update cleanup statistics
        self._cleanup_stats["total_connections_cleaned"] += 1

    async def cleanup_stale_connections(self, batch_size: int | None = None) -> int:
        """
        Garbage collection for zombie connections based on last activity time.

        This method only cleans up connections that have been inactive for longer
        than the threshold. It uses last_activity_at instead of connected_at to
        avoid mistakenly cleaning active long-lived connections.

        Args:
            batch_size: Maximum number of connections to clean in one batch.
                       Defaults to CLEANUP_BATCH_SIZE from config.
                       Set to None for unlimited batch size (useful for shutdown).

        Returns:
            int: Number of stale connections cleaned up
        """
        self._cleanup_stats["total_cleanups"] += 1
        start_time = time.time()
        unlimited_batch = batch_size is None
        if batch_size is None:
            batch_size = len(self.connections)  # Process all connections if unlimited
        elif batch_size <= 0:
            batch_size = sse_config.CLEANUP_BATCH_SIZE

        total_connections_before = len(self.connections)
        stale_count = 0
        failed_cleanups = 0
        cutoff_time = datetime.now(UTC).timestamp() - sse_config.STALE_CONNECTION_THRESHOLD_SECONDS

        # Collect connection age statistics for monitoring
        connection_ages = self._analyze_connection_ages(cutoff_time)

        # Identify potentially stale connections based on last activity
        stale_connection_ids = []
        for connection_id, connection_state in self.connections.items():
            if connection_state.last_activity_at.timestamp() < cutoff_time:
                stale_connection_ids.append(connection_id)
                if not unlimited_batch and len(stale_connection_ids) >= batch_size:
                    break

        # Clean up stale connections with error tracking
        for connection_id in stale_connection_ids:
            connection_state = self.connections.get(connection_id)
            if connection_state:
                try:
                    await self.cleanup_connection(connection_id, connection_state.user_id)
                    stale_count += 1
                except Exception as e:
                    failed_cleanups += 1
                    logger.error(f"Failed to cleanup connection {connection_id}: {e}", exc_info=True)

        # Calculate monitoring metrics
        end_time = time.time()
        cleanup_duration_ms = (end_time - start_time) * 1000
        total_connections_after = len(self.connections)
        if stale_connection_ids:
            cleanup_efficiency = (stale_count / len(stale_connection_ids)) * 100
        else:
            cleanup_efficiency = 100 if stale_count == 0 else 0

        # Update cleanup statistics
        if failed_cleanups > 0:
            self._cleanup_stats["cleanup_errors"] += 1
        self._cleanup_stats["failed_connections"] += failed_cleanups
        self._cleanup_stats["last_cleanup_duration_ms"] = cleanup_duration_ms
        self._cleanup_stats["last_cleanup_at"] = datetime.now(UTC)

        # Enhanced logging with monitoring metrics
        if stale_count > 0 or failed_cleanups > 0:
            logger.info(
                "SSE cleanup completed: cleaned=%d, failed=%d, total_before=%d, total_after=%d, "
                "duration_ms=%.2f, efficiency=%.1f%%, batch_size=%s, threshold_seconds=%d, "
                "stale_connections=%d, active_connections=%d, long_lived_connections=%d",
                stale_count,
                failed_cleanups,
                total_connections_before,
                total_connections_after,
                cleanup_duration_ms,
                cleanup_efficiency,
                "unlimited" if unlimited_batch else str(batch_size),
                sse_config.STALE_CONNECTION_THRESHOLD_SECONDS,
                connection_ages["stale"],
                connection_ages["active"],
                connection_ages["long_lived"],
            )
        else:
            logger.debug(
                "SSE cleanup completed: no stale connections found, "
                "total_connections=%d, duration_ms=%.2f, active_connections=%d, long_lived_connections=%d",
                total_connections_before,
                cleanup_duration_ms,
                connection_ages["active"],
                connection_ages["long_lived"],
            )

        return stale_count

    async def cleanup_all_stale_connections(self, max_iterations: int = 10) -> dict[str, Any]:
        """
        Complete cleanup of all stale connections during service shutdown.

        This method performs iterative cleanup until no more stale connections remain,
        ensuring complete cleanup during service shutdown to prevent Redis counter drift.

        Args:
            max_iterations: Maximum cleanup iterations to prevent infinite loops.
                           Defaults to 10 iterations.

        Returns:
            dict: Cleanup summary with total cleaned, iterations, and final counts
        """
        logger.info("Starting complete SSE cleanup for service shutdown")
        start_time = time.time()

        total_cleaned = 0
        iterations = 0
        connections_before = len(self.connections)

        # Iteratively clean until no more stale connections or max iterations reached
        while iterations < max_iterations:
            iterations += 1

            # Clean with unlimited batch size
            cleaned = await self.cleanup_stale_connections(batch_size=None)

            if cleaned == 0:
                logger.debug(f"Complete cleanup finished after {iterations} iteration(s)")
                break

            total_cleaned += cleaned
            logger.info(
                f"Shutdown cleanup iteration {iterations}: cleaned {cleaned} connections, "
                f"total cleaned: {total_cleaned}, remaining: {len(self.connections)}"
            )

            # Short delay between iterations to prevent overwhelming the system
            if cleaned > 0 and iterations < max_iterations:
                await asyncio.sleep(0.1)

        # Calculate final statistics
        connections_after = len(self.connections)
        cleanup_duration = (time.time() - start_time) * 1000

        summary = {
            "total_cleaned": total_cleaned,
            "iterations": iterations,
            "connections_before": connections_before,
            "connections_after": connections_after,
            "cleanup_duration_ms": cleanup_duration,
            "max_iterations_reached": iterations >= max_iterations,
        }

        # Log final summary
        if total_cleaned > 0:
            logger.info(
                "Shutdown cleanup completed: cleaned=%d connections, iterations=%d, "
                "before=%d, after=%d, duration=%.2fms, max_iterations_reached=%s",
                total_cleaned,
                iterations,
                connections_before,
                connections_after,
                cleanup_duration,
                summary["max_iterations_reached"],
            )

            # Warn if max iterations reached with remaining connections
            if summary["max_iterations_reached"] and connections_after > 0:
                logger.warning(
                    "Shutdown cleanup reached max iterations (%d) with %d connections remaining. "
                    "Consider increasing max_iterations or investigating connection cleanup issues.",
                    max_iterations,
                    connections_after,
                )
        else:
            logger.info("Shutdown cleanup completed: no stale connections found")

        # Update shutdown cleanup statistics
        self._cleanup_stats["shutdown_cleanups"] += 1
        self._cleanup_stats["shutdown_connections_cleaned"] += total_cleaned
        self._cleanup_stats["last_shutdown_cleanup_summary"] = summary

        return summary

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
        logger.info(
            "Periodic SSE cleanup worker started: interval=%ds, batch_size=%d, threshold=%ds",
            sse_config.CLEANUP_INTERVAL_SECONDS,
            sse_config.CLEANUP_BATCH_SIZE,
            sse_config.STALE_CONNECTION_THRESHOLD_SECONDS,
        )

        consecutive_errors = 0
        max_consecutive_errors = 5

        try:
            while self._cleanup_running:
                try:
                    # Run cleanup with batch size limit
                    start_time = time.time()
                    cleaned = await self.cleanup_stale_connections()
                    cycle_duration = (time.time() - start_time) * 1000

                    # Reset error counter on successful cleanup
                    consecutive_errors = 0

                    # Log periodic summary with enhanced metrics
                    current_stats = await self.get_cleanup_statistics()
                    if cleaned > 0:
                        logger.info(
                            "Periodic cleanup cycle: cleaned=%d connections, cycle_duration_ms=%.2f, "
                            "total_cleanups=%d, total_cleaned=%d, error_rate=%.2f%%",
                            cleaned,
                            cycle_duration,
                            current_stats["total_cleanups"],
                            current_stats["total_connections_cleaned"],
                            current_stats["error_rate"],
                        )
                    else:
                        logger.debug(
                            "Periodic cleanup cycle: no stale connections, cycle_duration_ms=%.2f, "
                            "active_connections=%d",
                            cycle_duration,
                            len(self.connections),
                        )

                except Exception as e:
                    consecutive_errors += 1
                    self._cleanup_stats["cleanup_errors"] += 1

                    logger.error(
                        "Periodic SSE cleanup error (attempt %d/%d): %s",
                        consecutive_errors,
                        max_consecutive_errors,
                        e,
                        exc_info=True,
                    )

                    # Stop periodic cleanup if too many consecutive errors
                    if consecutive_errors >= max_consecutive_errors:
                        logger.critical(
                            "Stopping periodic cleanup due to %d consecutive errors. " "Manual intervention required.",
                            consecutive_errors,
                        )
                        self._cleanup_running = False
                        break

                # Wait for next cleanup interval
                await asyncio.sleep(sse_config.CLEANUP_INTERVAL_SECONDS)

        except asyncio.CancelledError:
            logger.info(
                "Periodic SSE cleanup worker stopped gracefully. "
                "Total cleanups performed: %d, total connections cleaned: %d",
                self._cleanup_stats["total_cleanups"],
                self._cleanup_stats["total_connections_cleaned"],
            )
            raise
        except Exception as e:
            logger.error(f"Periodic SSE cleanup worker failed critically: {e}", exc_info=True)
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

    async def get_cleanup_statistics(self) -> dict[str, Any]:
        """
        Get detailed cleanup statistics for monitoring and alerting.

        Returns:
            dict: Cleanup statistics including:
                - total_cleanups: Total number of cleanup operations executed
                - total_connections_cleaned: Total connections cleaned across all operations
                - cleanup_errors: Cleanup operations that reported errors
                - failed_connections: Total failed connection-level cleanup attempts
                - last_cleanup_duration_ms: Duration of last cleanup operation in milliseconds
                - last_cleanup_at: Timestamp of last cleanup operation
                - error_rate: Percentage of cleanup operations that encountered errors
                - connection_failure_rate: Percentage of per-connection cleanup attempts that failed
                - avg_cleanup_duration_ms: Average cleanup duration (estimated)
                - connections_per_cleanup: Average connections cleaned per operation
        """
        stats = self._cleanup_stats.copy()

        # Calculate derived metrics
        total_cleanups = stats["total_cleanups"]
        if total_cleanups > 0:
            stats["error_rate"] = (stats["cleanup_errors"] / total_cleanups) * 100
            stats["connections_per_cleanup"] = stats["total_connections_cleaned"] / total_cleanups
        else:
            stats["error_rate"] = 0.0
            stats["connections_per_cleanup"] = 0.0

        connection_attempts = stats["total_connections_cleaned"] + stats["failed_connections"]
        if connection_attempts > 0:
            stats["connection_failure_rate"] = (stats["failed_connections"] / connection_attempts) * 100
        else:
            stats["connection_failure_rate"] = 0.0

        # Add current connection analysis
        now = datetime.now(UTC).timestamp()
        cutoff_time = now - sse_config.STALE_CONNECTION_THRESHOLD_SECONDS
        connection_ages = self._analyze_connection_ages(cutoff_time)
        stats.update(connection_ages)

        return stats

    def _analyze_connection_ages(self, cutoff_time: float) -> dict[str, int]:
        """
        Analyze connection ages for monitoring insights.

        Args:
            cutoff_time: Timestamp cutoff for determining stale connections

        Returns:
            dict: Connection age analysis with counts for different categories
        """
        now = datetime.now(UTC)
        age_categories = {
            "stale": 0,  # Connections past cutoff_time
            "active": 0,  # Recent activity within threshold
            "long_lived": 0,  # Connected for >1 hour but still active
            "very_old": 0,  # Connected for >6 hours
        }

        one_hour_ago = (now - timedelta(hours=1)).timestamp()
        six_hours_ago = (now - timedelta(hours=6)).timestamp()

        for connection_state in self.connections.values():
            last_activity = connection_state.last_activity_at.timestamp()
            connected_at = connection_state.connected_at.timestamp()

            if last_activity < cutoff_time:
                age_categories["stale"] += 1
            else:
                age_categories["active"] += 1

                if connected_at < one_hour_ago:
                    age_categories["long_lived"] += 1

                if connected_at < six_hours_ago:
                    age_categories["very_old"] += 1

        return age_categories

    def _validate_config(self) -> None:
        """
        Validate SSE configuration for optimal performance and warn about potential issues.
        """
        warnings = []

        # Check cleanup interval
        if sse_config.CLEANUP_INTERVAL_SECONDS < 10:
            warnings.append(
                f"Cleanup interval ({sse_config.CLEANUP_INTERVAL_SECONDS}s) is very short, " "may impact performance"
            )
        elif sse_config.CLEANUP_INTERVAL_SECONDS > 300:
            warnings.append(
                f"Cleanup interval ({sse_config.CLEANUP_INTERVAL_SECONDS}s) is very long, "
                "stale connections may accumulate"
            )

        # Check batch size
        if sse_config.CLEANUP_BATCH_SIZE < 1:
            warnings.append("Cleanup batch size must be at least 1")
        elif sse_config.CLEANUP_BATCH_SIZE > 100:
            warnings.append(
                f"Cleanup batch size ({sse_config.CLEANUP_BATCH_SIZE}) is very large, " "may cause cleanup delays"
            )

        # Check stale threshold vs cleanup interval
        if sse_config.STALE_CONNECTION_THRESHOLD_SECONDS < sse_config.CLEANUP_INTERVAL_SECONDS * 2:
            warnings.append(
                f"Stale threshold ({sse_config.STALE_CONNECTION_THRESHOLD_SECONDS}s) should be "
                f"at least 2x cleanup interval ({sse_config.CLEANUP_INTERVAL_SECONDS}s) "
                "to avoid premature cleanup"
            )

        # Check ping interval vs stale threshold
        if sse_config.PING_INTERVAL_SECONDS * 3 > sse_config.STALE_CONNECTION_THRESHOLD_SECONDS:
            warnings.append(
                f"Stale threshold ({sse_config.STALE_CONNECTION_THRESHOLD_SECONDS}s) should be "
                f"at least 3x ping interval ({sse_config.PING_INTERVAL_SECONDS}s) "
                "to account for network delays"
            )

        # Log configuration warnings
        if warnings:
            logger.warning("SSE configuration validation warnings: %s", "; ".join(warnings))
        else:
            logger.info(
                "SSE configuration validated successfully: cleanup_interval=%ds, batch_size=%d, "
                "stale_threshold=%ds, ping_interval=%ds",
                sse_config.CLEANUP_INTERVAL_SECONDS,
                sse_config.CLEANUP_BATCH_SIZE,
                sse_config.STALE_CONNECTION_THRESHOLD_SECONDS,
                sse_config.PING_INTERVAL_SECONDS,
            )
