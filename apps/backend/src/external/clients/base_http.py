"""Base HTTP client with common functionality for external service clients."""

import logging
import time
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class BaseHttpClient:
    """Base HTTP client with retry, timeout, and monitoring capabilities."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_keepalive_connections: int = 5,
        max_connections: int = 10,
        enable_retry: bool = False,
        retry_attempts: int = 3,
        retry_min_wait: float = 1.0,
        retry_max_wait: float = 10.0,
        metrics_hook: Callable[[str, str, int, float, Exception | None], None] | None = None,
    ):
        """Initialize base HTTP client.

        Args:
            base_url: Base URL for the external service
            timeout: Request timeout in seconds
            max_keepalive_connections: Maximum keepalive connections
            max_connections: Maximum total connections
            enable_retry: Enable retry mechanism for transient errors
            retry_attempts: Maximum number of retry attempts
            retry_min_wait: Minimum wait time between retries (seconds)
            retry_max_wait: Maximum wait time between retries (seconds)
            metrics_hook: Optional callback for metrics collection
        """
        self.base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout
        self._max_keepalive_connections = max_keepalive_connections
        self._max_connections = max_connections

        # Retry configuration
        self._enable_retry = enable_retry
        self._retry_attempts = retry_attempts
        self._retry_min_wait = retry_min_wait
        self._retry_max_wait = retry_max_wait

        # Observability
        self._metrics_hook = metrics_hook

    def _should_retry(self, exception: Exception) -> bool:
        """Determine if an exception should trigger a retry.

        Args:
            exception: Exception that occurred

        Returns:
            True if request should be retried
        """
        if isinstance(exception, httpx.HTTPStatusError):
            # Retry on server errors (5xx) and rate limiting (429)
            return exception.response.status_code >= 500 or exception.response.status_code == 429

        # Retry on network/connection errors
        return isinstance(
            exception,
            (
                httpx.RequestError,
                httpx.ConnectError,
                httpx.TimeoutException,
                httpx.NetworkError,
            ),
        )

    def _record_metrics(
        self, method: str, endpoint: str, status_code: int, duration: float, error: Exception | None = None
    ) -> None:
        """Record request metrics if hook is configured.

        Args:
            method: HTTP method
            endpoint: API endpoint
            status_code: HTTP status code (0 for errors)
            duration: Request duration in seconds
            error: Exception if request failed
        """
        if self._metrics_hook:
            try:
                self._metrics_hook(method, endpoint, status_code, duration, error)
            except Exception as e:
                logger.warning(f"Metrics hook failed: {e}")

    def _generate_correlation_id(self) -> str:
        """Generate a correlation ID for request tracing."""
        return str(uuid.uuid4())[:8]

    async def connect(self) -> None:
        """Establish HTTP client connection."""
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(
                    max_keepalive_connections=self._max_keepalive_connections,
                    max_connections=self._max_connections,
                ),
            )
            logger.debug(f"HTTP client connected to {self.base_url}")

    async def disconnect(self) -> None:
        """Close HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug(f"HTTP client disconnected from {self.base_url}")

    async def ensure_connected(self) -> bool:
        """Ensure HTTP client is connected."""
        try:
            if not self._client:
                await self.connect()
            return self._client is not None
        except Exception as e:
            logger.error(f"Failed to establish HTTP connection: {e}")
            return False

    async def health_check(self, endpoint: str = "/health") -> bool:
        """Perform health check against the service.

        Args:
            endpoint: Health check endpoint path

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            if not await self.ensure_connected():
                return False

            response = await self._client.get(f"{self.base_url}{endpoint}")
            is_healthy = response.status_code == 200

            if is_healthy:
                logger.debug(f"Health check passed for {self.base_url}")
            else:
                logger.warning(f"Health check failed for {self.base_url}: {response.status_code}")

            return is_healthy
        except Exception as e:
            logger.warning(f"Health check failed for {self.base_url}: {e}")
            return False

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        correlation_id: str | None = None,
    ) -> httpx.Response:
        """Perform GET request with retry and observability.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            headers: Request headers
            correlation_id: Optional correlation ID for request tracing

        Returns:
            HTTP response

        Raises:
            RuntimeError: If client is not connected
            httpx.HTTPStatusError: For HTTP error responses
        """
        if not await self.ensure_connected():
            raise RuntimeError("HTTP client not connected")

        # Add correlation ID to headers
        request_headers = headers.copy() if headers else {}
        request_correlation_id = correlation_id or self._generate_correlation_id()
        request_headers["X-Correlation-ID"] = request_correlation_id

        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        error = None
        response = None

        try:
            if self._enable_retry:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(self._retry_attempts),
                    wait=wait_exponential(
                        multiplier=1,
                        min=self._retry_min_wait,
                        max=self._retry_max_wait,
                    ),
                    retry=retry_if_exception_type(Exception) & retry_if_exception(self._should_retry),
                ):
                    with attempt:
                        response = await self._client.get(url, params=params, headers=request_headers)
                        response.raise_for_status()
            else:
                response = await self._client.get(url, params=params, headers=request_headers)
                response.raise_for_status()

            duration = time.time() - start_time
            self._record_metrics("GET", endpoint, response.status_code, duration)

            logger.debug(
                f"GET {endpoint} completed - "
                f"status: {response.status_code}, "
                f"duration: {duration:.3f}s, "
                f"correlation_id: {request_correlation_id}"
            )

            return response

        except Exception as e:
            error = e
            duration = time.time() - start_time
            status_code = getattr(getattr(e, "response", None), "status_code", 0)
            self._record_metrics("GET", endpoint, status_code, duration, error)

            logger.warning(
                f"GET {endpoint} failed - "
                f"error: {type(e).__name__}: {e}, "
                f"duration: {duration:.3f}s, "
                f"correlation_id: {request_correlation_id}"
            )
            raise

    async def post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Perform POST request.

        Args:
            endpoint: API endpoint path
            json_data: JSON payload
            data: Form data or raw data
            headers: Request headers

        Returns:
            HTTP response

        Raises:
            RuntimeError: If client is not connected
            httpx.HTTPStatusError: For HTTP error responses
        """
        if not await self.ensure_connected():
            raise RuntimeError("HTTP client not connected")

        url = f"{self.base_url}{endpoint}"
        response = await self._client.post(url, json=json_data, data=data, headers=headers)
        response.raise_for_status()
        return response

    @asynccontextmanager
    async def session(self):
        """Context manager for HTTP client session."""
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()

    def __repr__(self) -> str:
        """String representation of the client."""
        return f"BaseHttpClient(base_url='{self.base_url}')"
