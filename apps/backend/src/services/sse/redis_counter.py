"""Redis Counter Service for SSE connection tracking."""

import logging

from fastapi import HTTPException
from redis.asyncio import Redis

from .config import sse_config

logger = logging.getLogger(__name__)


class RedisCounterService:
    """Service for managing Redis-based connection counters with atomic operations."""

    def __init__(self, redis_client: Redis | None):
        """Initialize with Redis client."""
        self.redis_client = redis_client

    def get_connection_key(self, user_id: str) -> str:
        """Get Redis key for user connection counter."""
        return f"user:{user_id}:sse_conns"

    async def safe_decr_counter(self, user_id: str) -> None:
        """Safely decrement Redis counter with negative protection."""
        if not self.redis_client:
            return

        # Decrement user-specific counter
        conn_key = self.get_connection_key(user_id)
        val = await self.redis_client.decr(conn_key)
        if val < 0:
            await self.redis_client.set(conn_key, 0)

        # Decrement global counter
        global_key = "global:sse_connections_count"
        global_val = await self.redis_client.decr(global_key)
        if global_val < 0:
            await self.redis_client.set(global_key, 0)

    async def check_connection_limit(self, user_id: str) -> None:
        """
        Check and enforce user connection limits atomically.

        Uses a Lua script to atomically:
        1. Check current connection count
        2. Increment if under limit
        3. Set expiry
        4. Update global counter

        Falls back to non-atomic implementation for testing compatibility.
        """
        if not self.redis_client:
            raise RuntimeError("Redis Pub/Sub client not initialized")

        conn_key = self.get_connection_key(user_id)
        global_key = "global:sse_connections_count"

        # Try atomic implementation with Lua script
        if hasattr(self.redis_client, "eval"):
            # Lua script for atomic connection limit check
            lua_script = """
            local conn_key = KEYS[1]
            local global_key = KEYS[2]
            local max_conns = tonumber(ARGV[1])
            local expiry = tonumber(ARGV[2])

            -- Get current connection count
            local current = redis.call('GET', conn_key)
            current = current and tonumber(current) or 0

            -- Check if under limit
            if current >= max_conns then
                return {current, 0}  -- Return current count and failure flag
            end

            -- Atomically increment both counters
            local new_count = redis.call('INCR', conn_key)
            redis.call('EXPIRE', conn_key, expiry)
            redis.call('INCR', global_key)

            return {new_count, 1}  -- Return new count and success flag
            """

            try:
                # Execute Lua script atomically
                result = await self.redis_client.eval(
                    lua_script,
                    2,  # Number of keys
                    conn_key,
                    global_key,
                    sse_config.MAX_CONNECTIONS_PER_USER,
                    sse_config.CONNECTION_EXPIRY_SECONDS,
                )

                if result and len(result) >= 2:  # Check if result is valid
                    try:
                        # Ensure robust type conversion
                        current_conns, success = int(result[0]), int(result[1])

                        if not success:
                            raise HTTPException(
                                status_code=429,
                                detail="Too many concurrent SSE connections",
                                headers={"Retry-After": str(sse_config.RETRY_AFTER_SECONDS)},
                            )
                        return
                    except (ValueError, TypeError, IndexError) as conversion_error:
                        logger.warning(f"Failed to parse Lua script result {result}: {conversion_error}")
                        # Fall through to non-atomic implementation
                else:
                    logger.warning(f"Unexpected Lua script result: {result}")
                    # Fall through to non-atomic implementation

            except (AttributeError, ValueError) as e:
                # Fall through to non-atomic implementation
                logger.debug(f"Lua script not supported, using non-atomic fallback: {e}")

        # Fallback: Non-atomic implementation (for testing and compatibility)
        # Increment user-specific counter
        current_conns = await self.redis_client.incr(conn_key)
        await self.redis_client.expire(conn_key, sse_config.CONNECTION_EXPIRY_SECONDS)

        # Increment global counter
        await self.redis_client.incr(global_key)

        if current_conns > sse_config.MAX_CONNECTIONS_PER_USER:
            # Rollback both counters
            await self.safe_decr_counter(user_id)
            raise HTTPException(
                status_code=429,
                detail="Too many concurrent SSE connections",
                headers={"Retry-After": str(sse_config.RETRY_AFTER_SECONDS)},
            )

    async def get_total_redis_connections(self) -> int:
        """
        Get total connection count from global counter with fault tolerance.

        This optimized version uses a global counter instead of SCAN.
        If the global counter is missing or corrupted, it will fallback to
        SCAN aggregation and rebuild the global counter.
        """
        if not self.redis_client:
            return 0

        global_key = "global:sse_connections_count"

        try:
            # Try to get global counter first (O(1) operation)
            global_count = await self.redis_client.get(global_key)

            if global_count is not None:
                try:
                    count = int(global_count)
                    # Sanity check: if count is negative, it's corrupted
                    if count >= 0:
                        return count
                    else:
                        logger.warning(f"Global connection count is negative ({count}), rebuilding")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid global connection count value: {global_count}, rebuilding")

            # Fallback: Rebuild global counter using SCAN aggregation
            logger.info("Rebuilding global connection count from individual counters")
            return await self._rebuild_global_counter(global_key)

        except Exception as e:
            logger.warning(f"Error getting global connection count, using SCAN fallback: {e}")
            # Last resort: Use SCAN aggregation without updating global counter
            return await self._scan_total_connections()

    async def _rebuild_global_counter(self, global_key: str) -> int:
        """
        Rebuild the global connection counter by scanning all user connection keys.

        Args:
            global_key: The Redis key for the global counter

        Returns:
            int: The rebuilt connection count
        """
        if not self.redis_client:
            return 0

        try:
            total_connections = await self._scan_total_connections()

            # Set the rebuilt counter with a reasonable TTL to prevent permanent drift
            await self.redis_client.setex(
                global_key,
                3600,  # 1 hour TTL
                total_connections,
            )

            logger.info(f"Rebuilt global connection count: {total_connections}")
            return total_connections

        except Exception as e:
            logger.error(f"Failed to rebuild global counter: {e}")
            return 0

    async def _scan_total_connections(self) -> int:
        """
        Scan all user connection counters and sum them up.

        This is the fallback method when the global counter is unavailable.
        """
        if not self.redis_client:
            return 0

        total_connections = 0

        try:
            # Use SCAN to find all user connection keys
            async for key in self.redis_client.scan_iter(match="user:*:sse_conns"):
                try:
                    count = await self.redis_client.get(key)
                    if count is not None:
                        total_connections += int(count)
                except (ValueError, TypeError):
                    # Skip corrupted individual counters
                    continue

        except Exception as e:
            logger.error(f"Error during connection scan: {e}")

        return total_connections

    async def get_user_connection_count(self, user_id: str) -> int:
        """Get current connection count for a specific user without modifying counters.

        Args:
            user_id: The user identifier

        Returns:
            int: Current connection count (0 if missing/unavailable)
        """
        if not self.redis_client:
            return 0

        try:
            key = self.get_connection_key(user_id)
            val = await self.redis_client.get(key)
            if val is None:
                return 0
            try:
                count = int(val)
                return max(count, 0)
            except (ValueError, TypeError):
                logger.warning(f"Invalid user connection count value for {key}: {val}")
                return 0
        except Exception as e:
            logger.warning(f"Error fetching user connection count for {user_id}: {e}")
            return 0
