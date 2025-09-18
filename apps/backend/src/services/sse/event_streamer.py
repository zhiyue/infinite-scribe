"""SSE Event Streamer for managing event flow."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from contextlib import suppress

from fastapi import Request
from sse_starlette import ServerSentEvent

from .config import sse_config
from .redis_client import RedisSSEService

logger = logging.getLogger(__name__)


class SSEEventStreamer:
    """Service for managing SSE event streaming with history replay and real-time events."""

    def __init__(self, redis_sse_service: RedisSSEService, state_manager=None):
        """Initialize with Redis SSE service and optional state manager."""
        self.redis_sse = redis_sse_service
        self.state_manager = state_manager

    async def create_event_generator(
        self, request: Request, user_id: str, connection_state, cleanup_callback
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """Create async generator for SSE events with history replay and real-time streaming."""
        keepalive_task: asyncio.Task | None = None
        try:
            # Get connection state to extract last_event_id and connection_id
            since_id = connection_state.last_event_id if connection_state and connection_state.last_event_id else "-"
            connection_id = connection_state.connection_id if connection_state else None

            # Start background activity refresher so idle connections stay marked active
            if connection_id and self.state_manager:
                keepalive_task = asyncio.create_task(self._refresh_connection_activity(connection_id))

            # Push missed/historical events first (for reconnection)
            async for event in self._send_historical_events(request, user_id, connection_id, since_id=since_id):
                yield event

            # Stream real-time events with client disconnection detection
            async for event in self._stream_realtime_events(request, user_id, connection_id):
                yield event

        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for user {user_id}")
            raise
        except Exception as e:
            logger.error(f"Error in event generator for user {user_id}: {e}")
            # Send error event to client
            yield ServerSentEvent(data=json.dumps({"error": "Stream error occurred", "reconnect": True}), event="error")
        finally:
            if keepalive_task:
                keepalive_task.cancel()
                with suppress(asyncio.CancelledError):
                    await keepalive_task
            # Cleanup connection state
            await cleanup_callback()

    async def _send_historical_events(
        self, request: Request, user_id: str, connection_id: str | None = None, since_id: str = "-"
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """
        Send historical events to newly connected client with improved backfill.

        This method now handles event history properly:
        - Sends all events since Last-Event-ID (not just last 10)
        - Processes events in batches to avoid memory issues
        - Maintains chronological order
        - Updates connection activity timestamp when sending events
        """
        try:
            # Fetch all events since the given ID
            historical_events = await self.redis_sse.get_recent_events(user_id, since_id=since_id)

            # If no Last-Event-ID provided, limit to recent events for initial connection
            if since_id in ("-", None) and len(historical_events) > sse_config.DEFAULT_HISTORY_LIMIT:
                # For initial connections, send only recent events
                historical_events = historical_events[-sse_config.DEFAULT_HISTORY_LIMIT :]
                logger.info(
                    f"Initial connection for user {user_id}, sending last {sse_config.DEFAULT_HISTORY_LIMIT} events"
                )
            else:
                # For reconnections, send all events since Last-Event-ID
                logger.info(f"Reconnection for user {user_id} from {since_id}, sending {len(historical_events)} events")

            # Send events in chronological order
            for event in historical_events:
                if await request.is_disconnected():
                    logger.info(f"Client disconnected during history replay for user {user_id}")
                    return

                # Update connection activity timestamp when sending event
                if connection_id and self.state_manager:
                    self.state_manager.update_connection_activity(connection_id)

                # 添加元信息到数据中，供前端验证
                data_with_meta = {**event.data, "_scope": event.scope.value, "_version": event.version}
                yield ServerSentEvent(data=json.dumps(data_with_meta, ensure_ascii=False), event=event.event, id=event.id)
        except Exception as e:
            logger.error(f"Error pushing historical events for user {user_id}: {e}")

    async def _stream_realtime_events(
        self, request: Request, user_id: str, connection_id: str | None = None
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """Stream real-time events to client with disconnection detection and activity tracking."""
        async for sse_message in self.redis_sse.subscribe_user_events(user_id):
            # Check for client disconnection (sse-starlette feature)
            if await request.is_disconnected():
                logger.info(f"Client disconnected for user {user_id}, stopping event stream")
                break

            # Update connection activity timestamp when sending event
            if connection_id and self.state_manager:
                self.state_manager.update_connection_activity(connection_id)

            # 添加元信息到数据中，供前端验证
            data_with_meta = {**sse_message.data, "_scope": sse_message.scope.value, "_version": sse_message.version}

            # Use ServerSentEvent for structured events
            yield ServerSentEvent(
                data=json.dumps(data_with_meta, ensure_ascii=False),
                event=sse_message.event,
                id=sse_message.id,
            )

    async def _refresh_connection_activity(self, connection_id: str) -> None:
        """Periodically refresh connection activity so idle connections are not GC'd prematurely."""
        try:
            # Refresh at least once a minute, respecting configured ping interval when shorter
            refresh_interval = max(1, min(sse_config.PING_INTERVAL_SECONDS, sse_config.CLEANUP_INTERVAL_SECONDS))

            while True:
                await asyncio.sleep(refresh_interval)

                if not self.state_manager:
                    break

                updated = self.state_manager.update_connection_activity(connection_id)
                if not updated:
                    break
        except asyncio.CancelledError:
            raise
