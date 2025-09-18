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
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from src.core.config import settings
from src.db.redis import RedisService
from src.schemas.sse import EventScope, SSEMessage

logger = logging.getLogger(__name__)

# Constants
SSE_TIMEOUT = 30.0
CLEANUP_TIMEOUT = 2.0
MAX_EVENTS_QUERY = 100
BATCH_SIZE = 50  # Batch size for historical event processing
DEFAULT_HISTORY_LIMIT = 50  # Default limit for initial connections


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
        # Close existing connection to prevent resource leaks on re-init
        if self._pubsub_client:
            try:
                await self._pubsub_client.close()
            except Exception as e:
                logger.warning(f"Error closing existing pubsub client: {e}")
            finally:
                self._pubsub_client = None

        logger.info(
            "Initializing Redis Pub/Sub client",
            extra={
                "host": settings.database.redis_host,
                "port": settings.database.redis_port,
            },
        )
        self._pubsub_client = redis.from_url(
            settings.database.redis_url,
            decode_responses=True,
            health_check_interval=30,
            socket_connect_timeout=10,
            socket_timeout=30,
            retry_on_timeout=True,
        )
        try:
            await self._pubsub_client.ping()
            logger.info("Redis Pub/Sub ping successful")
        except Exception as e:
            logger.warning(f"Redis Pub/Sub ping failed: {e}")

    async def close(self) -> None:
        """Close Pub/Sub client during app shutdown."""
        if self._pubsub_client:
            await self._pubsub_client.close()
            self._pubsub_client = None

    async def check_health(self) -> bool:
        """
        Check if Pub/Sub client is healthy and connected.

        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            if not self._pubsub_client:
                return False

            # Test actual connectivity with ping
            await self._pubsub_client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis Pub/Sub health check failed: {e}")
            return False

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
        logger.info(
            "📤 Publishing SSE event",
            extra={
                "user_id": user_id,
                "event_type": event.event,
                "event_scope": event.scope.value if event.scope else None,
                "event_id": event.id,
                "has_data": bool(event.data),
                "data_size": len(json.dumps(event.data, default=str)) if event.data else 0,
            },
        )

        try:
            client: Redis = self._get_pubsub_client()

            stream_key = f"events:user:{user_id}"
            channel = f"sse:user:{user_id}"

            logger.debug(
                "📝 Preparing Redis operations",
                extra={
                    "user_id": user_id,
                    "stream_key": stream_key,
                    "channel": channel,
                    "maxlen": settings.database.redis_sse_stream_maxlen,
                },
            )

            # Add to stream for persistence
            async with self.redis_service.acquire() as redis_client:
                logger.debug(
                    "💾 Adding event to Redis stream",
                    extra={"user_id": user_id, "stream_key": stream_key, "event_type": event.event},
                )

                stream_id = await redis_client.xadd(
                    stream_key,
                    {"event": event.event, "data": json.dumps(event.data, ensure_ascii=False, default=str)},
                    maxlen=settings.database.redis_sse_stream_maxlen,
                    approximate=True,
                )

                logger.debug(
                    "✅ Event added to stream",
                    extra={
                        "user_id": user_id,
                        "stream_key": stream_key,
                        "stream_id": stream_id,
                        "event_type": event.event,
                    },
                )

            # Set event ID for consistency
            event.id = stream_id

            # Publish pointer for real-time notification
            pointer_data = {"stream_key": stream_key, "stream_id": stream_id}

            logger.debug(
                "📡 Publishing real-time notification",
                extra={"user_id": user_id, "channel": channel, "stream_id": stream_id, "pointer_data": pointer_data},
            )

            await client.publish(channel, json.dumps(pointer_data))

            logger.info(
                "✅ SSE event published successfully",
                extra={
                    "user_id": user_id,
                    "event_type": event.event,
                    "stream_id": stream_id,
                    "stream_key": stream_key,
                    "channel": channel,
                },
            )

            return stream_id

        except Exception as e:
            logger.error(
                "❌ Failed to publish SSE event",
                extra={"user_id": user_id, "event_type": event.event, "error": str(e), "error_type": type(e).__name__},
            )
            raise

    async def subscribe_user_events(
        self, user_id: str, last_event_id: str | None = None
    ) -> AsyncIterator[SSEMessage]:
        """
        Subscribe to real-time user events with connection resilience.

        Features:
        - Automatic reconnection on connection failure
        - Exponential backoff for retries
        - Graceful error handling
        - Proper resource cleanup to prevent memory leaks
        """
        max_retries = 3
        retry_delay = 1  # Initial delay in seconds
        retry_count = 0

        current_last_event_id = last_event_id if last_event_id not in {None, "-"} else None

        while retry_count < max_retries:
            pubsub = None
            channel = f"sse:user:{user_id}"

            try:
                # Get or reconnect to Pub/Sub client
                client: Redis = self._get_pubsub_client()
                pubsub = client.pubsub()
                await pubsub.subscribe(channel)

                # Reset retry count on successful connection
                retry_count = 0
                retry_delay = 1

                # Flush any events that may have arrived after history replay but before
                # the Pub/Sub subscription was ready. This narrows the race window where
                # events could otherwise be missed.
                if current_last_event_id:
                    try:
                        pending_events = await self.get_recent_events(user_id, since_id=current_last_event_id)
                    except Exception as gap_error:  # pragma: no cover - defensive logging
                        logger.warning(
                            "Failed to fetch catch-up events after subscribe",
                            extra={
                                "user_id": user_id,
                                "last_event_id": current_last_event_id,
                                "error": str(gap_error),
                            },
                        )
                    else:
                        for pending_event in pending_events:
                            if pending_event.id == current_last_event_id:
                                continue

                            current_last_event_id = pending_event.id
                            yield pending_event

                try:
                    # Consume messages directly from the async iterator to avoid
                    # repeatedly timing out and cancelling __anext__(), which can
                    # accumulate pending tasks and increase memory usage.
                    async for message in pubsub.listen():
                        if message.get("type") != "message":
                            continue

                        event = await self._process_pointer_message(message, user_id)
                        if event:
                            current_last_event_id = event.id or current_last_event_id
                            yield event

                except asyncio.CancelledError:
                    logger.debug(f"Subscription cancelled for user {user_id}")
                    raise

            except RedisConnectionError as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Max retries reached for user {user_id}: {e}")
                    raise

                logger.warning(
                    f"Pub/Sub connection error for user {user_id}, retry {retry_count}/{max_retries} in {retry_delay}s: {e}"
                )

                # Clean up the failed pubsub connection before retry
                if pubsub:
                    await self._safe_cleanup(pubsub, channel, user_id)
                    pubsub = None

                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)  # Exponential backoff, max 30s

                # Try to reinitialize the pubsub client and continue retry loop
                try:
                    await self.init_pubsub_client()
                except Exception as init_error:
                    logger.error(f"Failed to reinitialize Pub/Sub client: {init_error}")
                    # Don't break, let the retry loop try again with the potentially broken client
                    # The next iteration will fail quickly and we'll retry or give up

            except RedisError as e:
                logger.error(f"Redis error in subscription for user {user_id}: {e}")
                raise

            except Exception as e:
                logger.error(f"Unexpected error in subscription for user {user_id}: {e}")
                raise

            finally:
                # Always clean up pubsub resources
                if pubsub:
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
        """
        Retrieve historical events from Redis Streams for catch-up scenarios.

        For initial connections (since_id="-"), returns the most recent DEFAULT_HISTORY_LIMIT events.
        For reconnections (with since_id), returns all events since the given ID using batch processing.
        """
        stream_key = f"events:user:{user_id}"

        async with self.redis_service.acquire() as redis_client:
            if since_id in ("-", None):
                # Initial connection: Get most recent events using XREVRANGE
                items = await redis_client.xrevrange(stream_key, "+", "-", count=DEFAULT_HISTORY_LIMIT)
                # Reverse to maintain chronological order (oldest to newest)
                items = list(reversed(items))
            else:
                # Reconnection: Get all events since since_id using batch processing
                items = []
                current_id = since_id

                while True:
                    batch_entries = await redis_client.xread({stream_key: current_id}, count=BATCH_SIZE)

                    if not batch_entries:
                        break

                    (_key, batch_items) = batch_entries[0]

                    if not batch_items:
                        break

                    items.extend(batch_items)

                    # Update current_id to last processed ID for next batch
                    current_id = batch_items[-1][0]

                    # If we got fewer items than batch size, we've reached the end
                    if len(batch_items) < BATCH_SIZE:
                        break

        events = []
        for stream_id, fields in items:
            try:
                events.append(self._build_sse_message(fields["event"], fields["data"], stream_id))
            except (json.JSONDecodeError, KeyError):
                continue  # Skip corrupted entries

        return events
