"""Rate limiting service for API endpoints."""

import json
import time
from datetime import datetime, timedelta
from typing import Any

from redis import Redis

from src.core.config import settings


class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int):
        """Initialize rate limit exceeded exception.

        Args:
            message: Error message
            retry_after: Seconds until next request is allowed
        """
        super().__init__(message)
        self.retry_after = retry_after


class RateLimitService:
    """Service for managing rate limits using Redis."""

    def __init__(self):
        """Initialize rate limit service."""
        self._redis_client: Redis | None = None

    @property
    def redis_client(self) -> Redis:
        """Get Redis client for rate limiting."""
        if self._redis_client is None:
            self._redis_client = Redis(
                host=settings.database.redis_host,
                port=settings.database.redis_port,
                password=settings.database.redis_password,
                decode_responses=True,
            )
        return self._redis_client

    def check_rate_limit(self, key: str, limit: int, window: int, raise_exception: bool = False) -> dict[str, Any]:
        """Check and update rate limit for a key.

        Args:
            key: Unique identifier for rate limiting (e.g., user_id, IP)
            limit: Maximum number of requests allowed
            window: Time window in seconds
            raise_exception: Whether to raise exception when limit exceeded

        Returns:
            Dictionary with rate limit information

        Raises:
            RateLimitExceeded: If limit exceeded and raise_exception=True
        """
        now = time.time()
        redis_key = f"rate_limit:{key}"

        # Get current data from Redis
        data = self.redis_client.get(redis_key)

        if data:
            rate_data = json.loads(data)
            requests = rate_data.get("requests", [])

            # Remove expired requests (outside the window)
            cutoff_time = now - window
            requests = [req_time for req_time in requests if req_time > cutoff_time]
        else:
            requests = []

        # Check if limit is exceeded
        if len(requests) >= limit:
            retry_after = int(window - (now - requests[0]))

            if raise_exception:
                raise RateLimitExceededError(f"Rate limit exceeded. Try again in {retry_after} seconds.", retry_after)

            return {
                "allowed": False,
                "remaining": 0,
                "limit": limit,
                "reset_time": datetime.fromtimestamp(requests[0] + window),
                "retry_after": retry_after,
            }

        # Add current request
        requests.append(now)

        # Store updated data
        rate_data = {"requests": requests, "window": window, "limit": limit}

        # Set expiration to window + 1 second for cleanup
        self.redis_client.setex(redis_key, window + 1, json.dumps(rate_data))

        remaining = limit - len(requests)
        reset_time = (
            datetime.fromtimestamp(requests[0] + window) if requests else datetime.utcnow() + timedelta(seconds=window)
        )

        return {"allowed": True, "remaining": remaining, "limit": limit, "reset_time": reset_time}

    def get_rate_limit_info(self, key: str, limit: int, window: int) -> dict[str, Any]:
        """Get rate limit information without incrementing counter.

        Args:
            key: Unique identifier for rate limiting
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            Dictionary with current rate limit status
        """
        now = time.time()
        redis_key = f"rate_limit:{key}"

        # Get current data from Redis
        data = self.redis_client.get(redis_key)

        if data:
            rate_data = json.loads(data)
            requests = rate_data.get("requests", [])

            # Remove expired requests
            cutoff_time = now - window
            requests = [req_time for req_time in requests if req_time > cutoff_time]
        else:
            requests = []

        current = len(requests)
        remaining = max(0, limit - current)
        reset_time = (
            datetime.fromtimestamp(requests[0] + window) if requests else datetime.utcnow() + timedelta(seconds=window)
        )

        return {
            "current": current,
            "remaining": remaining,
            "limit": limit,
            "reset_time": reset_time,
        }

    def reset_rate_limit(self, key: str) -> None:
        """Reset rate limit for a key.

        Args:
            key: Unique identifier to reset
        """
        redis_key = f"rate_limit:{key}"
        self.redis_client.delete(redis_key)

    def get_client_key(self, request, user_id: str | None = None) -> str:
        """Generate a rate limit key for a client.

        Args:
            request: FastAPI request object
            user_id: Optional user ID for authenticated requests

        Returns:
            Unique key for rate limiting
        """
        if user_id:
            return f"user:{user_id}"

        # Use IP address for unauthenticated requests
        client_ip = request.client.host if request.client else "unknown"

        # Consider X-Forwarded-For header for reverse proxy setups
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        return f"ip:{client_ip}"


# Global instance
redis_client = (
    Redis(
        host=settings.database.redis_host,
        port=settings.database.redis_port,
        password=settings.database.redis_password,
        decode_responses=True,
    )
    if hasattr(settings.database, "redis_host")
    else None
)

rate_limit_service = RateLimitService()
