"""
SSE Connection Manager for managing Server-Sent Events connections.

This service manages SSE connections using sse-starlette with the following features:
- Queue aggregation design: real-time events + historical events + built-in ping
- User concurrency limits (max 2 connections per user, Redis counter)
- Connection cleanup and zombie connection GC
- Client disconnection detection and graceful cleanup
- Integration with RedisSSEService for event publishing/subscription

Architecture:
- Uses sse-starlette.EventSourceResponse with built-in ping/heartbeat
- Async generators yield ServerSentEvent objects or dicts
- Redis counters for connection limits and state tracking
- Built-in client disconnection detection via request.is_disconnected()
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request
from sse_starlette import EventSourceResponse

from .config import sse_config
from .connection_state import SSEConnectionState, SSEConnectionStateManager
from .event_streamer import SSEEventStreamer
from .redis_client import RedisSSEService
from .redis_counter import RedisCounterService

# Re-export for backward compatibility
__all__ = ["SSEConnectionManager", "SSEConnectionState"]

logger = logging.getLogger(__name__)


class SSEConnectionManager:
    """
    Service for managing SSE connections using sse-starlette with production-ready features.

    This service manages multiple SSE connections with the following features:

    - **Connection Limits**: Max 2 concurrent connections per user (Redis counters)
    - **Queue Aggregation**: Real-time events + historical events + built-in ping
    - **Client Disconnection**: Automatic detection via request.is_disconnected()
    - **Resource Cleanup**: Automatic cleanup and zombie connection GC
    - **State Tracking**: In-memory connection state with Redis backing
    - **Production Ready**: Timeout handling, graceful shutdown, error recovery

    Architecture Pattern:
    1. Events are queued from multiple sources (real-time, history)
    2. sse-starlette provides built-in ping/heartbeat functionality
    3. Client disconnection is detected automatically
    4. Connection state is tracked both in-memory and Redis for resilience

    Usage:
        manager = SSEConnectionManager(redis_sse_service)
        response = await manager.add_connection(request, user_id)
        # Returns EventSourceResponse with built-in ping and error handling
    """

    # Configuration constants (for backward compatibility with tests)
    MAX_CONNECTIONS_PER_USER = sse_config.MAX_CONNECTIONS_PER_USER
    CONNECTION_EXPIRY_SECONDS = sse_config.CONNECTION_EXPIRY_SECONDS
    PING_INTERVAL_SECONDS = sse_config.PING_INTERVAL_SECONDS
    SEND_TIMEOUT_SECONDS = sse_config.SEND_TIMEOUT_SECONDS
    DEFAULT_HISTORY_LIMIT = sse_config.DEFAULT_HISTORY_LIMIT
    STALE_CONNECTION_THRESHOLD_SECONDS = sse_config.STALE_CONNECTION_THRESHOLD_SECONDS
    RETRY_AFTER_SECONDS = sse_config.RETRY_AFTER_SECONDS
    RECENT_EVENTS_LIMIT = sse_config.DEFAULT_HISTORY_LIMIT  # For test compatibility

    def __init__(self, redis_sse_service: RedisSSEService):
        """Initialize SSE Connection Manager."""
        if not redis_sse_service._pubsub_client:
            raise RuntimeError("Redis Pub/Sub client not initialized")

        self.redis_sse = redis_sse_service

        # Initialize service components
        self.redis_counter_service = RedisCounterService(redis_sse_service._pubsub_client)
        self.state_manager = SSEConnectionStateManager(self.redis_counter_service)
        self.event_streamer = SSEEventStreamer(redis_sse_service, self.state_manager)

        # For backward compatibility with tests
        self.connections = self.state_manager.connections
        self.ping_interval = self.PING_INTERVAL_SECONDS

    # Delegate methods for backward compatibility with tests
    def _get_connection_key(self, user_id: str) -> str:
        """Get Redis key for user connection counter."""
        return self.redis_counter_service.get_connection_key(user_id)

    async def _safe_decr_counter(self, user_id: str) -> None:
        """Safely decrement Redis counter with negative protection."""
        await self.redis_counter_service.safe_decr_counter(user_id)

    async def _check_connection_limit(self, user_id: str) -> None:
        """Check and enforce user connection limits atomically."""
        await self.redis_counter_service.check_connection_limit(user_id)

    async def _get_total_redis_connections(self) -> int:
        """Get total connection count from global counter with fault tolerance."""
        return await self.redis_counter_service.get_total_redis_connections()

    async def _cleanup_connection(self, connection_id: str, user_id: str):
        """Clean up connection resources and Redis counters."""
        await self.state_manager.cleanup_connection(connection_id, user_id)

    async def add_connection(self, request: Request, user_id: str) -> EventSourceResponse:
        """
        Add new SSE connection with production-ready features and concurrency limits.

        This method implements the enhanced SSE design:
        1. Enforces user concurrency limits (max 2 connections via Redis)
        2. Reads Last-Event-ID from headers for reconnection support
        3. Creates connection state tracking with reconnection context
        4. Returns EventSourceResponse with built-in ping/heartbeat and error handling

        Args:
            request: FastAPI Request object for client disconnection detection and headers
            user_id: User ID for the connection

        Returns:
            EventSourceResponse: Production-ready SSE response with built-in features

        Raises:
            HTTPException: If user exceeds concurrency limits (429)
            RuntimeError: If Redis client is not initialized
        """
        logger.info(
            "📡 SSE connection request received",
            extra={
                "user_id": user_id,
                "client_host": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "last_event_id": request.headers.get("last-event-id"),
            },
        )

        try:
            # Extract tab_id from headers or query params
            qp = getattr(request, "query_params", None)
            qp_get = None
            if qp is not None and hasattr(qp, "get"):
                try:
                    qp_get = qp.get  # type: ignore[attr-defined]
                except Exception:
                    qp_get = None
            tab_id_val = qp_get("tab_id") if callable(qp_get) else None  # type: ignore[misc]
            tab_id = request.headers.get("x-tab-id") or request.headers.get("x-tabid")
            if not tab_id and isinstance(tab_id_val, str):
                tab_id = tab_id_val

            # Same-tab preemption: if an existing connection from the same tab exists, preempt it
            if tab_id:
                existing = self.state_manager.find_connection_by_tab(user_id, tab_id)
                if existing:
                    old_conn_id, _ = existing
                    logger.info(
                        "🔄 Preempting existing connection from same tab",
                        extra={"user_id": user_id, "tab_id": tab_id, "old_connection_id": old_conn_id},
                    )
                    # Free slot immediately to avoid limit rejection
                    await self.state_manager.preempt_connection(
                        old_conn_id, reason="same_tab", free_slot_immediately=True
                    )

            # 1) Enforce concurrency limits (after potential same-tab preemption)
            logger.debug(f"🔒 Checking connection limits for user {user_id}")
            if not self.redis_counter_service.redis_client:
                logger.error("Redis client未初始化，无法建立SSE连接")
                raise RuntimeError("Redis client not available")
            try:
                await self.redis_counter_service.check_connection_limit(user_id)
            except HTTPException as e:
                if e.status_code == 429:
                    # Attempt eviction of least-active connection and retry once
                    evicted = await self.state_manager.evict_least_active(user_id)
                    if evicted:
                        logger.info(
                            "🧹 Evicted least-active connection to admit new one",
                            extra={"user_id": user_id},
                        )
                        # Retry limit check
                        await self.redis_counter_service.check_connection_limit(user_id)
                    else:
                        raise
                else:
                    raise
            logger.debug(f"✅ Connection limit check passed for user {user_id}")

            # 2) Read Last-Event-ID from headers for reconnection support
            last_event_id = request.headers.get("last-event-id") or request.headers.get("last_event_id")
            if not last_event_id and callable(qp_get):
                le = qp_get("last-event-id") or qp_get("lastEventId")
                if isinstance(le, str):
                    last_event_id = le
            if last_event_id:
                logger.info(
                    f"🔄 Reconnection detected with last event ID: {last_event_id}",
                    extra={"user_id": user_id, "last_event_id": last_event_id},
                )
            else:
                logger.info("🆕 New SSE connection (no last event ID)", extra={"user_id": user_id})

            # 3) Create connection state
            logger.debug(f"🔧 Creating connection state for user {user_id}")
            connection_id, connection_state = self.state_manager.create_connection_state(user_id, last_event_id, tab_id)

            logger.info(
                "✅ SSE connection state created",
                extra={"user_id": user_id, "connection_id": connection_id, "has_last_event_id": bool(last_event_id)},
            )

            # 4) Create cleanup callback
            async def cleanup_callback():
                logger.info(
                    "🧹 Starting SSE connection cleanup", extra={"user_id": user_id, "connection_id": connection_id}
                )
                await self.state_manager.cleanup_connection(connection_id, user_id)
                logger.info(
                    "✅ SSE connection cleanup completed", extra={"user_id": user_id, "connection_id": connection_id}
                )

            # 5) Create EventSourceResponse with built-in ping and error handling
            logger.info(
                "🚀 Creating EventSourceResponse",
                extra={
                    "user_id": user_id,
                    "connection_id": connection_id,
                    "ping_interval": self.ping_interval,
                    "send_timeout": self.SEND_TIMEOUT_SECONDS,
                },
            )

            response = EventSourceResponse(
                self.event_streamer.create_event_generator(request, user_id, connection_state, cleanup_callback),
                ping=self.ping_interval,
                send_timeout=self.SEND_TIMEOUT_SECONDS,
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )

            logger.info(
                "✅ SSE connection established successfully",
                extra={"user_id": user_id, "connection_id": connection_id, "response_type": "EventSourceResponse"},
            )

            return response

        except HTTPException as e:
            logger.warning(
                "⚠️ SSE connection rejected",
                extra={
                    "user_id": user_id,
                    "status_code": e.status_code,
                    "detail": e.detail,
                    "error_type": "HTTPException",
                },
            )
            raise

        except Exception as e:
            logger.error(f"SSE连接失败: {type(e).__name__}: {e!s}", extra={"user_id": user_id})
            raise

    async def cleanup_stale_connections(self, batch_size: int | None = None) -> int:
        """Garbage collection for zombie connections."""
        return await self.state_manager.cleanup_stale_connections(batch_size=batch_size)

    async def cleanup_all_stale_connections_for_shutdown(self, max_iterations: int = 10) -> dict[str, Any]:
        """
        Complete cleanup of all stale connections during service shutdown.

        This method ensures all stale connections are cleaned up during service shutdown
        to prevent Redis counter drift and connection leaks.

        Args:
            max_iterations: Maximum cleanup iterations to prevent infinite loops.

        Returns:
            dict: Cleanup summary with statistics
        """
        return await self.state_manager.cleanup_all_stale_connections(max_iterations=max_iterations)

    async def get_connection_count(self) -> dict[str, int]:
        """Get connection statistics for monitoring."""
        return await self.state_manager.get_connection_count()

    # Additional private methods delegated to extracted services for test compatibility
    async def _rebuild_global_counter(self, global_key: str) -> int:
        """Rebuild the global connection counter by scanning all user connection keys."""
        return await self.redis_counter_service._rebuild_global_counter(global_key)

    async def _scan_total_connections(self) -> int:
        """Scan all user connection counters and sum them up."""
        return await self.redis_counter_service._scan_total_connections()

    async def start_periodic_cleanup(self) -> None:
        """Start periodic cleanup of stale connections."""
        await self.state_manager.start_periodic_cleanup()

    async def stop_periodic_cleanup(self) -> None:
        """Stop periodic cleanup of stale connections."""
        await self.state_manager.stop_periodic_cleanup()

    async def is_periodic_cleanup_running(self) -> bool:
        """Check if periodic cleanup is currently running."""
        return self.state_manager._cleanup_task is not None and not self.state_manager._cleanup_task.done()

    async def get_detailed_monitoring_stats(self) -> dict[str, Any]:
        """
        Get comprehensive SSE monitoring statistics for dashboard integration.

        This method combines connection counts, cleanup statistics, and performance
        metrics to provide a complete view of SSE service health for monitoring
        dashboards and alerting systems.

        Returns:
            dict: Comprehensive monitoring statistics including:
                - connection_stats: Current connection counts and Redis counters
                - cleanup_stats: Detailed cleanup performance and error metrics
                - health_indicators: Service health indicators for alerting
                - performance_metrics: Performance-related measurements
        """
        # Get basic connection statistics
        connection_stats = await self.get_connection_count()

        # Get detailed cleanup statistics
        cleanup_stats = await self.state_manager.get_cleanup_statistics()

        # Calculate health indicators for alerting
        health_indicators = self._calculate_health_indicators(connection_stats, cleanup_stats)

        # Performance metrics
        total_connections_cleaned = cleanup_stats.get("total_connections_cleaned", 0)
        failed_connections = cleanup_stats.get("failed_connections", 0)
        connection_attempts = total_connections_cleaned + failed_connections
        cleanup_success_rate = total_connections_cleaned / connection_attempts * 100 if connection_attempts else 100.0

        performance_metrics = {
            "avg_cleanup_duration_ms": cleanup_stats.get("last_cleanup_duration_ms", 0),
            "cleanup_efficiency_rate": cleanup_success_rate,
            "cleanup_error_rate": cleanup_stats.get("error_rate", 0),
            "connections_cleaned_per_operation": cleanup_stats.get("connections_per_cleanup", 0),
        }

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "service_name": "sse_connection_manager",
            "connection_stats": connection_stats,
            "cleanup_stats": cleanup_stats,
            "health_indicators": health_indicators,
            "performance_metrics": performance_metrics,
            "configuration": {
                "cleanup_interval_seconds": sse_config.CLEANUP_INTERVAL_SECONDS,
                "cleanup_batch_size": sse_config.CLEANUP_BATCH_SIZE,
                "stale_threshold_seconds": sse_config.STALE_CONNECTION_THRESHOLD_SECONDS,
                "periodic_cleanup_enabled": sse_config.ENABLE_PERIODIC_CLEANUP,
            },
        }

    def _calculate_health_indicators(self, connection_stats: dict, cleanup_stats: dict) -> dict[str, Any]:
        """
        Calculate health indicators for monitoring and alerting.

        Args:
            connection_stats: Current connection statistics
            cleanup_stats: Cleanup performance statistics

        Returns:
            dict: Health indicators with status and severity levels
        """
        indicators = {
            "overall_health": "healthy",
            "alerts": [],
            "warnings": [],
        }

        # Check connection health
        active_connections = connection_stats.get("active_connections", 0)
        redis_connections = connection_stats.get("redis_connection_counters", 0)

        # Alert: Redis counters under-report relative to in-memory tracking (likely drift)
        mismatch = redis_connections - active_connections
        mismatch_threshold = max(5, int(max(active_connections, redis_connections) * 0.2))
        if mismatch < -mismatch_threshold:
            mismatch_value = abs(mismatch)
            indicators["alerts"].append(
                {
                    "type": "redis_counter_underreporting",
                    "message": (
                        "Redis connection counters are lower than in-memory tracking; "
                        f"local={active_connections}, redis={redis_connections}, difference={mismatch_value}"
                    ),
                    "severity": "high",
                    "value": mismatch_value,
                }
            )
            indicators["overall_health"] = "degraded"

        # Warning: High connection count
        if active_connections > 1000:
            indicators["warnings"].append(
                {
                    "type": "high_connection_count",
                    "message": f"High number of active connections: {active_connections}",
                    "severity": "medium",
                    "value": active_connections,
                }
            )

        # Check cleanup health
        error_rate = cleanup_stats.get("error_rate", 0)
        cleanup_running = connection_stats.get("cleanup_task_running", False)

        # Alert: High cleanup error rate
        if error_rate > 10:
            indicators["alerts"].append(
                {
                    "type": "high_cleanup_error_rate",
                    "message": f"High cleanup error rate: {error_rate:.1f}%",
                    "severity": "high",
                    "value": error_rate,
                }
            )
            indicators["overall_health"] = "unhealthy"
        elif error_rate > 5:
            indicators["warnings"].append(
                {
                    "type": "elevated_cleanup_error_rate",
                    "message": f"Elevated cleanup error rate: {error_rate:.1f}%",
                    "severity": "medium",
                    "value": error_rate,
                }
            )

        # Alert: Cleanup not running when enabled
        if sse_config.ENABLE_PERIODIC_CLEANUP and not cleanup_running:
            indicators["alerts"].append(
                {
                    "type": "cleanup_not_running",
                    "message": "Periodic cleanup is enabled but not running",
                    "severity": "high",
                    "value": False,
                }
            )
            indicators["overall_health"] = "degraded"

        # Warning: Stale connections accumulating
        stale_connections = cleanup_stats.get("stale", 0)
        if stale_connections > 50:
            indicators["warnings"].append(
                {
                    "type": "stale_connections_accumulating",
                    "message": f"Large number of stale connections detected: {stale_connections}",
                    "severity": "medium",
                    "value": stale_connections,
                }
            )

        # Warning: Very old connections (potential memory leak)
        very_old_connections = cleanup_stats.get("very_old", 0)
        if very_old_connections > 10:
            indicators["warnings"].append(
                {
                    "type": "very_old_connections",
                    "message": f"Connections older than 6 hours detected: {very_old_connections}",
                    "severity": "medium",
                    "value": very_old_connections,
                }
            )

        return indicators
