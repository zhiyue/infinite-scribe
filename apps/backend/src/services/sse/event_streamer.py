"""SSE Event Streamer for managing event flow."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from contextlib import suppress

from fastapi import Request
from sse_starlette import ServerSentEvent

from .config import sse_config

logger = logging.getLogger(__name__)


class SSEEventStreamer:
    """Service for streaming events to SSE clients with history replay."""

    def __init__(self, redis_sse_service, state_manager=None):
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

            # Start background activity refresher that checks connection liveness
            if connection_id and self.state_manager:
                keepalive_task = asyncio.create_task(self._refresh_connection_activity(request, connection_id))

            # Push missed/historical events first (for reconnection)
            async for event in self._send_historical_events(
                request,
                user_id,
                connection_id,
                connection_state,
                since_id=since_id,
            ):
                yield event

            # Stream real-time events with client disconnection detection
            async for event in self._stream_realtime_events(
                request,
                user_id,
                connection_id,
                connection_state,
            ):
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
        self,
        request: Request,
        user_id: str,
        connection_id: str | None = None,
        connection_state=None,
        since_id: str = "-",
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """Send historical events to client for replay/catch-up on reconnection."""
        # Extract connection_id from connection_state if not provided (backward compatibility)
        if connection_id is None and connection_state:
            connection_id = getattr(connection_state, 'connection_id', None)
        
        # Retrieve missed events from since_id (if connection was resumed)
        if since_id != "-":
            logger.debug(f"Replaying events for user {user_id} since event ID: {since_id}")

            # Get events from Redis stream since last_event_id
            historical_events = await self.redis_sse.get_recent_events(user_id, since_id=since_id)
            
            for sse_message in historical_events:
                # Check disconnection before sending each historical event
                if await request.is_disconnected():
                    logger.info(f"Client disconnected for user {user_id}, stopping historical event replay")
                    break

                # Update activity when successfully sending historical events
                if connection_id and self.state_manager:
                    self.state_manager.update_connection_activity(connection_id)

                # Update last delivered event ID
                if connection_state and sse_message.id:
                    connection_state.last_event_id = sse_message.id

                # Prepare data with metadata
                data_with_meta = {**sse_message.data, "_scope": sse_message.scope.value, "_version": sse_message.version}

                yield ServerSentEvent(
                    data=json.dumps(data_with_meta, ensure_ascii=False),
                    event=sse_message.event,
                    id=sse_message.id,
                )

            logger.debug(f"Finished replaying historical events for user {user_id}")

    async def _stream_realtime_events(
        self,
        request: Request,
        user_id: str,
        connection_id: str | None = None,
        connection_state=None,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """Stream real-time events to client with disconnection detection and activity tracking."""
        last_event_id = connection_state.last_event_id if connection_state else None

        async for sse_message in self.redis_sse.subscribe_user_events(user_id, last_event_id=last_event_id):
            # Check for client disconnection (sse-starlette feature)
            if await request.is_disconnected():
                logger.info(f"Client disconnected for user {user_id}, stopping event stream")
                break

            # Update connection activity timestamp when sending event
            if connection_id and self.state_manager:
                self.state_manager.update_connection_activity(connection_id)

            # Persist last delivered event ID for reconnection catch-up
            if connection_state and sse_message.id:
                connection_state.last_event_id = sse_message.id

            # 添加元信息到数据中，供前端验证
            data_with_meta = {**sse_message.data, "_scope": sse_message.scope.value, "_version": sse_message.version}

            # Use ServerSentEvent for structured events
            yield ServerSentEvent(
                data=json.dumps(data_with_meta, ensure_ascii=False),
                event=sse_message.event,
                id=sse_message.id,
            )

    async def _check_connection_liveness(self, request: Request) -> bool:
        """Check if the SSE connection is still alive by testing client disconnection status."""
        try:
            # Use FastAPI's built-in disconnection check
            return not await request.is_disconnected()
        except Exception as e:
            logger.debug(f"Error checking connection liveness: {e}")
            return False

    async def _refresh_connection_activity(self, request: Request, connection_id: str) -> None:
        """Periodically refresh connection activity only if connection is confirmed alive."""
        try:
            # Refresh at least once a minute, respecting configured ping interval when shorter
            refresh_interval = max(1, min(sse_config.PING_INTERVAL_SECONDS, sse_config.CLEANUP_INTERVAL_SECONDS))

            while True:
                await asyncio.sleep(refresh_interval)

                if not self.state_manager:
                    break

                # Only refresh activity if connection is confirmed alive
                if await self._check_connection_liveness(request):
                    updated = self.state_manager.update_connection_activity(connection_id)
                    if not updated:
                        break
                    logger.debug(f"Connection {connection_id} confirmed alive, activity refreshed")
                else:
                    # Connection is dead, stop refreshing to allow cleanup
                    logger.info(f"Connection {connection_id} detected as dead, stopping activity refresh")
                    break
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Error in connection activity refresh for {connection_id}: {e}")
            # Stop refreshing on any error to allow cleanup
            return
