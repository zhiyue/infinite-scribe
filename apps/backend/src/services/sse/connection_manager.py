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
        self.event_streamer = SSEEventStreamer(redis_sse_service)

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
            # 1) Enforce concurrency limits
            logger.debug(f"🔒 Checking connection limits for user {user_id}")
            if not self.redis_counter_service.redis_client:
                logger.error("Redis client未初始化，无法建立SSE连接")
                raise RuntimeError("Redis client not available")
            await self.redis_counter_service.check_connection_limit(user_id)
            logger.debug(f"✅ Connection limit check passed for user {user_id}")

            # 2) Read Last-Event-ID from headers for reconnection support
            last_event_id = request.headers.get("last-event-id")
            if last_event_id:
                logger.info(
                    f"🔄 Reconnection detected with last event ID: {last_event_id}",
                    extra={"user_id": user_id, "last_event_id": last_event_id},
                )
            else:
                logger.info("🆕 New SSE connection (no last event ID)", extra={"user_id": user_id})

            # 3) Create connection state
            logger.debug(f"🔧 Creating connection state for user {user_id}")
            connection_id, connection_state = self.state_manager.create_connection_state(user_id, last_event_id)

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

    async def cleanup_stale_connections(self) -> int:
        """Garbage collection for zombie connections."""
        return await self.state_manager.cleanup_stale_connections()

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
