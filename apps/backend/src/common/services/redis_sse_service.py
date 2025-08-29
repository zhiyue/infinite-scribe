"""
Redis SSE service implementation for Server-Sent Events.

This service implements a hybrid architecture combining Redis Pub/Sub and Streams:

1. **Event Publishing**: Events are first added to Redis Streams for persistence,
   then a pointer is published via Pub/Sub for real-time notification.

2. **Event Subscription**: Clients subscribe to Pub/Sub channels to receive
   event pointers, then fetch complete event data from Streams.

3. **Event History**: Historical events can be retrieved directly from Streams
   using event IDs for reconnection and catch-up scenarios.

Key Benefits:
- Real-time delivery via Pub/Sub
- Event persistence and history via Streams
- Consistent event IDs for Last-Event-ID support
- Separation of concerns between real-time notifications and data storage
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from src.common.services.redis_service import RedisService
from src.core.config import settings
from src.schemas.sse import EventScope, SSEMessage

logger = logging.getLogger(__name__)

# Constants
SSE_TIMEOUT = 30.0
CLEANUP_TIMEOUT = 2.0
MAX_EVENTS_QUERY = 100


class RedisSSEService:
    """
    Service for Redis-based Server-Sent Events using hybrid Pub/Sub + Streams architecture.

    This service manages SSE event distribution using two Redis data structures:

    - **Redis Streams**: Persistent event storage with automatic IDs and history retention
    - **Redis Pub/Sub**: Real-time event notification system for connected clients

    Architecture Pattern:
    1. Events are stored in Streams (durable, with IDs)
    2. Pointers to Stream entries are published via Pub/Sub (ephemeral, real-time)
    3. Subscribers receive pointers and fetch full events from Streams

    This ensures both real-time delivery and reliable event history for reconnections.

    Usage:
        service = RedisSSEService(redis_service)
        await service.init_pubsub_client()

        # Publishing
        stream_id = await service.publish_event(user_id, event)

        # Real-time subscription
        async for event in service.subscribe_user_events(user_id):
            process_event(event)

        # Historical events
        past_events = await service.get_recent_events(user_id, since_id)
    """

    def __init__(self, redis_service: RedisService):
        """Initialize Redis SSE service with existing RedisService."""
        self.redis_service = redis_service
        self._pubsub_client: Redis | None = None

    async def init_pubsub_client(self) -> None:
        """Initialize dedicated Redis client for Pub/Sub operations."""
        self._pubsub_client = redis.from_url(
            settings.database.redis_url,
            decode_responses=True,
            health_check_interval=30,
            socket_connect_timeout=10,
            socket_timeout=30,
            retry_on_timeout=True,
        )

    async def close(self) -> None:
        """Close Pub/Sub client during app shutdown."""
        if self._pubsub_client:
            await self._pubsub_client.close()
            self._pubsub_client = None

    def _ensure_pubsub_client(self) -> None:
        """Ensure Pub/Sub client is initialized."""
        if not self._pubsub_client:
            raise RuntimeError("Pub/Sub client not initialized")

    def _get_pubsub_client(self) -> Redis:
        """Return initialized Pub/Sub client or raise if missing."""
        if self._pubsub_client is None:
            raise RuntimeError("Pub/Sub client not initialized")
        return self._pubsub_client

    def _build_sse_message(self, event_type: str, data: str, stream_id: str) -> SSEMessage:
        """Build SSEMessage from stream data."""
        return SSEMessage(
            event=event_type,
            data=json.loads(data),
            id=stream_id,
            retry=None,
            scope=EventScope.USER,
            version="1.0",
        )

    async def _safe_cleanup(self, pubsub: PubSub, channel: str, user_id: str) -> None:
        """Safely cleanup pubsub resources with timeout protection."""
        try:
            await asyncio.wait_for(pubsub.unsubscribe(channel), timeout=CLEANUP_TIMEOUT)
        except (TimeoutError, Exception) as e:
            logger.debug(f"Timeout/error during unsubscribe for user {user_id}: {e}")

        try:
            await asyncio.wait_for(pubsub.close(), timeout=CLEANUP_TIMEOUT)
        except (TimeoutError, Exception) as e:
            logger.debug(f"Timeout/error during pubsub close for user {user_id}: {e}")

    async def publish_event(self, user_id: str, event: SSEMessage) -> str:
        """Publish event to user channel via Streams + Pub/Sub architecture."""
        client: Redis = self._get_pubsub_client()

        stream_key = f"events:user:{user_id}"
        channel = f"sse:user:{user_id}"

        # Add to stream for persistence
        async with self.redis_service.acquire() as redis_client:
            stream_id = await redis_client.xadd(
                stream_key,
                {"event": event.event, "data": json.dumps(event.data, ensure_ascii=False, default=str)},
                maxlen=settings.database.redis_sse_stream_maxlen,
                approximate=True,
            )

        # Set event ID for consistency
        event.id = stream_id

        # Publish pointer for real-time notification
        await client.publish(channel, json.dumps({"stream_key": stream_key, "stream_id": stream_id}))

        return stream_id

    async def subscribe_user_events(self, user_id: str) -> AsyncIterator[SSEMessage]:
        """Subscribe to real-time user events using pointer-based architecture."""
        client: Redis = self._get_pubsub_client()

        channel = f"sse:user:{user_id}"
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)

        try:
            listener = pubsub.listen()
            while True:
                try:
                    message = await asyncio.wait_for(listener.__anext__(), timeout=SSE_TIMEOUT)
                    if message["type"] != "message":
                        continue

                    event = await self._process_pointer_message(message, user_id)
                    if event:
                        yield event

                except TimeoutError:
                    continue  # Allow cancellation check
                except StopAsyncIteration:
                    break

        except asyncio.CancelledError:
            logger.debug(f"Subscription cancelled for user {user_id}")
            raise
        finally:
            await self._safe_cleanup(pubsub, channel, user_id)

    async def _process_pointer_message(self, message: dict, user_id: str) -> SSEMessage | None:
        """Process a pointer message and return the SSE event."""
        try:
            pointer = json.loads(message["data"])
            stream_key = pointer["stream_key"]
            stream_id = pointer["stream_id"]

            async with self.redis_service.acquire() as redis_client:
                items = await redis_client.xrange(stream_key, stream_id, stream_id, count=1)

            if not items:
                return None

            stream_id, fields = items[0]
            return self._build_sse_message(fields["event"], fields["data"], stream_id)

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Invalid pointer message for user {user_id}: {e}")
            return None

    async def get_recent_events(self, user_id: str, since_id: str = "-") -> list[SSEMessage]:
        """Retrieve historical events from Redis Streams for catch-up scenarios."""
        stream_key = f"events:user:{user_id}"

        async with self.redis_service.acquire() as redis_client:
            if since_id in ("-", None):
                items = await redis_client.xrange(stream_key, "-", "+", count=MAX_EVENTS_QUERY)
            else:
                entries = await redis_client.xread({stream_key: since_id}, count=MAX_EVENTS_QUERY)
                if not entries:
                    return []
                (_key, items) = entries[0]

        events = []
        for stream_id, fields in items:
            try:
                events.append(self._build_sse_message(fields["event"], fields["data"], stream_id))
            except (json.JSONDecodeError, KeyError):
                continue  # Skip corrupted entries

        return events
