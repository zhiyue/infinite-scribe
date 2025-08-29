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

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette import EventSourceResponse, ServerSentEvent

from src.common.services.redis_sse_service import RedisSSEService

logger = logging.getLogger(__name__)


class SSEConnectionState(BaseModel):
    """SSE connection state model for tracking active connections."""

    connection_id: str = Field(..., description="Unique connection identifier")
    user_id: str = Field(..., description="User ID associated with connection")
    connected_at: datetime = Field(..., description="Connection timestamp")
    last_event_id: str | None = Field(None, description="Last processed event ID for reconnection")
    channel_subscriptions: list[str] = Field(default_factory=list, description="Subscribed channels")


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

    # Configuration constants
    MAX_CONNECTIONS_PER_USER = 2
    CONNECTION_EXPIRY_SECONDS = 300
    PING_INTERVAL_SECONDS = 15
    SEND_TIMEOUT_SECONDS = 30
    RECENT_EVENTS_LIMIT = 10
    STALE_CONNECTION_THRESHOLD_SECONDS = 300
    RETRY_AFTER_SECONDS = 30

    def __init__(self, redis_sse_service: RedisSSEService):
        """Initialize SSE Connection Manager."""
        self.redis_sse = redis_sse_service
        self.connections: dict[str, SSEConnectionState] = {}
        self.ping_interval = self.PING_INTERVAL_SECONDS

    def _get_connection_key(self, user_id: str) -> str:
        """Get Redis key for user connection counter."""
        return f"user:{user_id}:sse_conns"

    async def _safe_decr_counter(self, user_id: str) -> None:
        """Safely decrement Redis counter with negative protection."""
        if not self.redis_sse._pubsub_client:
            return

        conn_key = self._get_connection_key(user_id)
        val = await self.redis_sse._pubsub_client.decr(conn_key)
        if val < 0:
            await self.redis_sse._pubsub_client.set(conn_key, 0)

    async def _check_connection_limit(self, user_id: str) -> None:
        """Check and enforce user connection limits."""
        if not self.redis_sse._pubsub_client:
            raise RuntimeError("Redis Pub/Sub client not initialized")

        conn_key = self._get_connection_key(user_id)
        current_conns = await self.redis_sse._pubsub_client.incr(conn_key)
        await self.redis_sse._pubsub_client.expire(conn_key, self.CONNECTION_EXPIRY_SECONDS)

        if current_conns > self.MAX_CONNECTIONS_PER_USER:
            await self._safe_decr_counter(user_id)
            raise HTTPException(
                status_code=429,
                detail="Too many concurrent SSE connections",
                headers={"Retry-After": str(self.RETRY_AFTER_SECONDS)}
            )

    async def _create_event_generator(self, request: Request, user_id: str, connection_id: str) -> AsyncGenerator[ServerSentEvent, None]:
        """Create async generator for SSE events with history replay and real-time streaming."""
        try:
            # Get connection state to extract last_event_id
            connection_state = self.connections.get(connection_id)
            since_id = connection_state.last_event_id if connection_state and connection_state.last_event_id else "-"

            # Push missed/historical events first (for reconnection)
            async for event in self._send_historical_events(request, user_id, since_id=since_id):
                yield event

            # Stream real-time events with client disconnection detection
            async for event in self._stream_realtime_events(request, user_id):
                yield event

        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for user {user_id}")
            raise
        except Exception as e:
            logger.error(f"Error in event generator for user {user_id}: {e}")
            # Send error event to client
            yield ServerSentEvent(data=json.dumps({"error": "Stream error occurred", "reconnect": True}), event="error")
        finally:
            # Cleanup connection state
            await self._cleanup_connection(connection_id, user_id)

    async def _send_historical_events(self, request: Request, user_id: str, since_id: str = "-") -> AsyncGenerator[ServerSentEvent, None]:
        """Send historical events to newly connected client."""
        try:
            recent_events = await self.redis_sse.get_recent_events(user_id, since_id=since_id)
            for event in recent_events[-self.RECENT_EVENTS_LIMIT :]:
                if await request.is_disconnected():
                    logger.info(f"Client disconnected during history replay for user {user_id}")
                    return

                yield ServerSentEvent(data=json.dumps(event.data, ensure_ascii=False), event=event.event, id=event.id)
        except Exception as e:
            logger.error(f"Error pushing missed events for user {user_id}: {e}")

    async def _stream_realtime_events(self, request: Request, user_id: str) -> AsyncGenerator[ServerSentEvent, None]:
        """Stream real-time events to client with disconnection detection."""
        async for sse_message in self.redis_sse.subscribe_user_events(user_id):
            # Check for client disconnection (sse-starlette feature)
            if await request.is_disconnected():
                logger.info(f"Client disconnected for user {user_id}, stopping event stream")
                break

            # Use ServerSentEvent for structured events
            yield ServerSentEvent(
                data=json.dumps(sse_message.data, ensure_ascii=False),
                event=sse_message.event,
                id=sse_message.id,
            )

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
        # 1) Enforce concurrency limits
        await self._check_connection_limit(user_id)

        # 2) Read Last-Event-ID from headers for reconnection support
        # Note: Standard header name is "Last-Event-ID" but Starlette headers are case-insensitive
        last_event_id = request.headers.get("last-event-id")

        # 3) Create connection state
        connection_id = str(uuid4())
        connection_state = SSEConnectionState(
            connection_id=connection_id,
            user_id=user_id,
            connected_at=datetime.now(UTC),
            last_event_id=last_event_id,
        )
        self.connections[connection_id] = connection_state

        # 4) Create EventSourceResponse with built-in ping and error handling
        return EventSourceResponse(
            self._create_event_generator(request, user_id, connection_id),
            ping=self.ping_interval,
            send_timeout=self.SEND_TIMEOUT_SECONDS,
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    async def _cleanup_connection(self, connection_id: str, user_id: str):
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
        await self._safe_decr_counter(user_id)

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
        cutoff_time = datetime.now(UTC).timestamp() - self.STALE_CONNECTION_THRESHOLD_SECONDS

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
                await self._cleanup_connection(connection_id, connection_state.user_id)
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
        total_redis_conns = await self._get_total_redis_connections()

        return {"active_connections": active_conns, "redis_connection_counters": total_redis_conns}

    async def _get_total_redis_connections(self) -> int:
        """Get total connection count from all Redis counters."""
        if not self.redis_sse._pubsub_client:
            return 0

        total_redis_conns = 0
        pattern = "user:*:sse_conns"
        async for key in self.redis_sse._pubsub_client.scan_iter(match=pattern):
            try:
                count = await self.redis_sse._pubsub_client.get(key)
                if count:
                    total_redis_conns += int(count)
            except (ValueError, TypeError):
                continue

        return total_redis_conns
