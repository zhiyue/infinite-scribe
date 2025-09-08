"""Base HTTP client with common functionality for external service clients."""

import logging
from contextlib import asynccontextmanager
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BaseHttpClient:
    """Base HTTP client with retry, timeout, and monitoring capabilities."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_keepalive_connections: int = 5,
        max_connections: int = 10,
    ):
        """Initialize base HTTP client.

        Args:
            base_url: Base URL for the external service
            timeout: Request timeout in seconds
            max_keepalive_connections: Maximum keepalive connections
            max_connections: Maximum total connections
        """
        self.base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout
        self._max_keepalive_connections = max_keepalive_connections
        self._max_connections = max_connections

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
    ) -> httpx.Response:
        """Perform GET request.

        Args:
            endpoint: API endpoint path
            params: Query parameters
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
        response = await self._client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response

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
