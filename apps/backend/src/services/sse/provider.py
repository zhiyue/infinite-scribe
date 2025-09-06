"""
SSE service provider and registry.

Goals:
- Provide a reusable, test-friendly way to access RedisSSEService and
  SSEConnectionManager across contexts (FastAPI, background workers, EventBridge).
- Avoid opaque module-level singletons while still offering an optional
  process-level fallback for non-web contexts.
- Centralize cleanup logic.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from src.common.services.redis_service import RedisService
from src.services.sse.connection_manager import SSEConnectionManager
from src.services.sse.redis_client import RedisSSEService

logger = logging.getLogger(__name__)


class SSEProvider:
    """Provider managing SSE services with explicit lifecycle.

    Instances of this provider are meant to be scoped (e.g., app/process scope)
    and can be easily swapped in tests.
    """

    def __init__(self, redis_service: RedisService | None = None) -> None:
        self._redis_service = redis_service or RedisService()
        self._redis_sse_service: RedisSSEService | None = None
        self._sse_connection_manager: SSEConnectionManager | None = None

        # Protect lazy init from concurrent calls
        self._lock = asyncio.Lock()

    async def get_redis_sse_service(self) -> RedisSSEService:
        async with self._lock:
            if self._redis_sse_service is None:
                self._redis_sse_service = RedisSSEService(self._redis_service)
                await self._redis_sse_service.init_pubsub_client()
            return self._redis_sse_service

    async def get_connection_manager(self) -> SSEConnectionManager:
        async with self._lock:
            if self._sse_connection_manager is None:
                redis_sse = await self.get_redis_sse_service()
                self._sse_connection_manager = SSEConnectionManager(redis_sse)
            return self._sse_connection_manager

    async def close(self) -> None:
        """Cleanup and close underlying services."""
        # Snapshot references under lock to avoid races
        async with self._lock:
            manager = self._sse_connection_manager
            service = self._redis_sse_service
            self._sse_connection_manager = None
            self._redis_sse_service = None

        # Cleanup outside lock (IO)
        try:
            if manager is not None:
                try:
                    stale = await manager.cleanup_stale_connections()
                    if stale:
                        logger.info(f"Cleaned up {stale} stale SSE connections")
                except Exception as e:
                    logger.warning(f"Error cleaning stale SSE connections: {e}")

                try:
                    # Reset global counter to prevent drift
                    if getattr(manager.redis_sse, "_pubsub_client", None):
                        await manager.redis_sse._pubsub_client.delete("global:sse_connections_count")
                except Exception as e:
                    logger.debug(f"Error resetting global SSE counter: {e}")

            if service is not None:
                try:
                    await service.close()
                except Exception as e:
                    logger.debug(f"Error closing RedisSSEService: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during SSEProvider.close(): {e}")


# Optional process-level default provider for non-web contexts
_default_provider: SSEProvider | None = None


def set_default_provider(provider: SSEProvider | None) -> None:
    """Set or clear the process-level default provider."""
    global _default_provider
    _default_provider = provider


def get_default_provider() -> SSEProvider:
    """Get the process-level default provider, creating one if missing."""
    global _default_provider
    if _default_provider is None:
        _default_provider = SSEProvider()
    return _default_provider


@asynccontextmanager
async def override_provider(provider: SSEProvider) -> AsyncIterator[SSEProvider]:
    """Temporarily override the default provider (test helper)."""
    global _default_provider
    prev = _default_provider
    _default_provider = provider
    try:
        yield provider
    finally:
        # Ensure the temporary provider is closed to avoid leaked resources
        with suppress(Exception):
            await provider.close()
        _default_provider = prev
