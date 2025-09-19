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
            logger.info(f"🚀 Starting SSE event generator for user {user_id}")

            # Get connection state to extract last_event_id and connection_id
            since_id = connection_state.last_event_id if connection_state and connection_state.last_event_id else "-"
            connection_id = connection_state.connection_id if connection_state else None

            logger.debug(f"📋 SSE connection state: connection_id={connection_id}, since_id={since_id}")

            # Start background activity refresher that checks connection liveness
            if connection_id and self.state_manager:
                logger.debug(f"⏰ Starting keepalive task for connection {connection_id}")
                keepalive_task = asyncio.create_task(self._refresh_connection_activity(request, connection_id))

            # Push missed/historical events first (for reconnection)
            logger.info(f"📜 Sending historical events for user {user_id} since {since_id}")
            event_count = 0
            async for event in self._send_historical_events(
                request,
                user_id,
                connection_id,
                connection_state,
                since_id=since_id,
            ):
                event_count += 1
                logger.debug(f"📤 Sent historical event #{event_count} to user {user_id}")
                yield event

            if event_count > 0:
                logger.info(f"✅ Sent {event_count} historical events to user {user_id}")

            # Stream real-time events with client disconnection detection
            logger.info(f"🔄 Starting real-time event stream for user {user_id}")
            async for event in self._stream_realtime_events(
                request,
                user_id,
                connection_id,
                connection_state,
            ):
                logger.debug(f"📡 Streaming real-time event to user {user_id}: {event.event}")
                yield event

        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for user {user_id}")
            raise
        except Exception as e:
            logger.error(f"Error in event generator for user {user_id}: {e}")
            # Send error event to client
            yield ServerSentEvent(data=json.dumps({"error": "Stream error occurred", "reconnect": True}), event="error")
        finally:
            logger.info(f"🧹 Cleaning up SSE connection for user {user_id}")
            if keepalive_task:
                keepalive_task.cancel()
                with suppress(asyncio.CancelledError):
                    await keepalive_task
            # Cleanup connection state
            await cleanup_callback()
            logger.info(f"✅ SSE connection cleanup completed for user {user_id}")

    async def _send_historical_events(
        self,
        request: Request,
        user_id: str,
        connection_id: str | None = None,
        connection_state=None,
        since_id: str = "-",
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """Send historical events to client for replay/catch-up on reconnection."""
        # Abort early if preempted
        if connection_state and getattr(connection_state, "abort_event", None) and connection_state.abort_event.is_set():
            return
        # Extract connection_id from connection_state if not provided (backward compatibility)
        if connection_id is None and connection_state:
            connection_id = getattr(connection_state, "connection_id", None)

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
                # Respect preemption
                if connection_state and getattr(connection_state, "abort_event", None) and connection_state.abort_event.is_set():
                    logger.info(f"Connection preempted for user {user_id}, stopping historical replay")
                    break

                # Update activity when successfully sending historical events
                if connection_id and self.state_manager:
                    self.state_manager.update_connection_activity(connection_id)

                # Update last delivered event ID
                if connection_state and sse_message.id:
                    connection_state.last_event_id = sse_message.id

                # Prepare data with metadata
                data_with_meta = {
                    **sse_message.data,
                    "_scope": sse_message.scope.value,
                    "_version": sse_message.version,
                }

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

        logger.info(f"📡 Starting real-time event subscription for user {user_id}, last_event_id={last_event_id}")

        try:
            event_count = 0
            stop_event = getattr(connection_state, "abort_event", None)
            async for sse_message in self.redis_sse.subscribe_user_events(
                user_id, last_event_id=last_event_id, stop_event=stop_event
            ):
                event_count += 1
                logger.debug(f"📨 Received real-time event #{event_count} for user {user_id}: {sse_message.event}")

                # Check for client disconnection (sse-starlette feature)
                if await request.is_disconnected():
                    logger.info(
                        f"Client disconnected for user {user_id}, stopping event stream after {event_count} events"
                    )
                    break
                # Respect preemption
                if stop_event is not None and stop_event.is_set():
                    logger.info(
                        f"Connection preempted for user {user_id}, stopping stream after {event_count} events"
                    )
                    break

                # Update connection activity timestamp when sending event
                if connection_id and self.state_manager:
                    self.state_manager.update_connection_activity(connection_id)

                # Persist last delivered event ID for reconnection catch-up
                if connection_state and sse_message.id:
                    connection_state.last_event_id = sse_message.id

                # 添加元信息到数据中，供前端验证
                data_with_meta = {
                    **sse_message.data,
                    "_scope": sse_message.scope.value,
                    "_version": sse_message.version,
                }

                # Use ServerSentEvent for structured events
                logger.debug(f"📤 Yielding event to user {user_id}: event={sse_message.event}, id={sse_message.id}")
                yield ServerSentEvent(
                    data=json.dumps(data_with_meta, ensure_ascii=False),
                    event=sse_message.event,
                    id=sse_message.id,
                )
        except Exception as e:
            logger.error(f"❌ Error in real-time event stream for user {user_id}: {type(e).__name__}: {e}")
            raise
        finally:
            logger.info(f"🔚 Real-time event stream ended for user {user_id} after {event_count} events")

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
