"""SSE Event Streamer for managing event flow."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import Request
from sse_starlette import ServerSentEvent

from .config import sse_config
from .redis_client import RedisSSEService

logger = logging.getLogger(__name__)


class SSEEventStreamer:
    """Service for managing SSE event streaming with history replay and real-time events."""

    def __init__(self, redis_sse_service: RedisSSEService):
        """Initialize with Redis SSE service."""
        self.redis_sse = redis_sse_service

    async def create_event_generator(
        self, request: Request, user_id: str, connection_state, cleanup_callback
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """Create async generator for SSE events with history replay and real-time streaming."""
        try:
            # Get connection state to extract last_event_id
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
            await cleanup_callback()

    async def _send_historical_events(
        self, request: Request, user_id: str, since_id: str = "-"
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """
        Send historical events to newly connected client with improved backfill.

        This method now handles event history properly:
        - Sends all events since Last-Event-ID (not just last 10)
        - Processes events in batches to avoid memory issues
        - Maintains chronological order
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

                yield ServerSentEvent(data=json.dumps(event.data, ensure_ascii=False), event=event.event, id=event.id)
        except Exception as e:
            logger.error(f"Error pushing historical events for user {user_id}: {e}")

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
