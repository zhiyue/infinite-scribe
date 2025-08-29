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

import json
import logging
from collections.abc import AsyncIterator

import redis.asyncio as redis

from src.common.services.redis_service import RedisService
from src.core.config import settings
from src.schemas.sse import EventScope, SSEMessage

logger = logging.getLogger(__name__)


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
        self._pubsub_client: redis.Redis | None = None

    async def init_pubsub_client(self) -> None:
        """
        Initialize a dedicated Redis client for Pub/Sub operations.

        A separate client is required because:
        1. Pub/Sub connections are stateful and block other Redis operations
        2. Stream operations (XADD, XREAD) need a different connection pool
        3. Avoids conflicts with other Redis services (e.g., RateLimitService)

        The dedicated client is configured with optimized timeouts for real-time use.

        Raises:
            redis.ConnectionError: If unable to connect to Redis server
        """
        self._pubsub_client = redis.from_url(
            settings.database.redis_url,
            decode_responses=True,
            health_check_interval=30,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    async def close(self) -> None:
        """Close Pub/Sub client during app shutdown."""
        if self._pubsub_client:
            await self._pubsub_client.close()
            self._pubsub_client = None

    async def publish_event(self, user_id: str, event: SSEMessage) -> str:
        """
        Publish event to user channel.

        First XADD to Stream to get ID, then publish pointer to Pub/Sub for ID consistency.

        Args:
            user_id: Target user ID
            event: SSE message to publish

        Returns:
            Stream ID of the published event

        Note:
            This method modifies the input event by setting event.id to the generated stream_id
            for Last-Event-ID consistency. The original SSEMessage object will be mutated.
        """
        if not self._pubsub_client:
            raise RuntimeError("Pub/Sub client not initialized")

        stream_key = f"events:user:{user_id}"  # Streams storage
        channel = f"sse:user:{user_id}"  # Pub/Sub channel (separate key namespace)

        # 1) First XADD to Stream using RedisService
        async with self.redis_service.acquire() as redis_client:
            stream_id = await redis_client.xadd(
                stream_key,
                {"event": event.event, "data": json.dumps(event.data, ensure_ascii=False, default=str)},
                maxlen=settings.database.redis_sse_stream_maxlen,
                approximate=True,
            )

        # 2) Set SSE id to stream_id for Last-Event-ID consistency
        event.id = stream_id

        # 3) Publish pointer message pointing to the Stream entry
        await self._pubsub_client.publish(channel, json.dumps({"stream_key": stream_key, "stream_id": stream_id}))

        return stream_id

    async def subscribe_user_events(self, user_id: str) -> AsyncIterator[SSEMessage]:
        """
        Subscribe to real-time user events using pointer-based architecture.

        This method:
        1. Subscribes to the user's Pub/Sub channel (sse:user:{user_id})
        2. Receives pointer messages containing stream_key + stream_id
        3. Fetches complete event data from Redis Streams using XRANGE
        4. Yields reconstructed SSEMessage objects

        The pointer-based approach ensures:
        - Real-time notification via Pub/Sub (low latency)
        - Complete event data from Streams (reliable, persistent)
        - Consistent event IDs for Last-Event-ID reconnection support

        Args:
            user_id: User ID to subscribe to events for

        Yields:
            SSEMessage: Complete SSE messages with event data and metadata

        Raises:
            RuntimeError: If Pub/Sub client is not initialized

        Note:
            - Invalid pointer messages are logged and skipped gracefully
            - Resources are automatically cleaned up when iteration ends
            - Supports infinite streaming until client disconnection
        """
        if not self._pubsub_client:
            raise RuntimeError("Pub/Sub client not initialized")

        channel = f"sse:user:{user_id}"
        pubsub = self._pubsub_client.pubsub()
        await pubsub.subscribe(channel)

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                # Parse pointer message
                try:
                    pointer = json.loads(message["data"])
                    stream_key = pointer["stream_key"]
                    stream_id = pointer["stream_id"]

                    # XRANGE to get the exact entry by ID using RedisService
                    async with self.redis_service.acquire() as redis_client:
                        items = await redis_client.xrange(stream_key, stream_id, stream_id, count=1)
                    if not items:
                        continue

                    (actual_stream_id, fields) = items[0]

                    # Reconstruct SSE message as unified model (formatted by upper layer as SSE)
                    sse_event = SSEMessage(
                        event=fields["event"],
                        data=json.loads(fields["data"]),
                        id=actual_stream_id,
                        retry=None,
                        scope=EventScope.USER,
                        version="1.0",
                    )
                    yield sse_event

                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Invalid pointer message in channel {channel} for user {user_id}: {e}")
                    continue
        finally:
            # Cleanup resources
            try:
                await pubsub.unsubscribe(channel)
            finally:
                await pubsub.close()

    async def get_recent_events(self, user_id: str, since_id: str = "-") -> list[SSEMessage]:
        """
        Retrieve historical events from Redis Streams for catch-up scenarios.

        This method directly queries Redis Streams to fetch past events, typically used:
        - During SSE reconnection to get missed events (Last-Event-ID support)
        - For initial page load to show recent activity
        - For debugging and event replay scenarios

        Unlike `subscribe_user_events()`, this is a one-time query, not a real-time stream.

        Args:
            user_id: User ID to get events for
            since_id: Starting event ID to fetch from. Special values:
                     "-": Get all available events (oldest first)
                     "0": Get from beginning of stream
                     "{timestamp}-{seq}": Get events after this specific ID

        Returns:
            List[SSEMessage]: Historical events ordered chronologically (oldest first).
                             Empty list if no events found or stream doesn't exist.

        Raises:
            RuntimeError: If Pub/Sub client is not initialized

        Note:
            - Limited to 100 events per call to prevent memory issues
            - Corrupted events in streams are silently skipped and logged
            - Event IDs are preserved for Last-Event-ID compatibility
        """
        if not self._pubsub_client:
            raise RuntimeError("Pub/Sub client not initialized")

        stream_key = f"events:user:{user_id}"
        async with self.redis_service.acquire() as redis_client:
            entries = await redis_client.xread({stream_key: since_id}, count=100)

        if not entries:
            return []

        events = []
        (_key, items) = entries[0]

        for stream_id, fields in items:
            try:
                sse_event = SSEMessage(
                    event=fields["event"],
                    data=json.loads(fields["data"]),
                    id=stream_id,
                    retry=None,
                    scope=EventScope.USER,
                    version="1.0",
                )
                events.append(sse_event)
            except (json.JSONDecodeError, KeyError):
                # Skip corrupted entries
                continue

        return events
