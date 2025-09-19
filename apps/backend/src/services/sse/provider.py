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
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from src.core.logging import get_logger
from src.db.redis import RedisService
from src.services.sse.connection_manager import SSEConnectionManager
from src.services.sse.redis_client import RedisSSEService

logger = get_logger(__name__)


class SSEProvider:
    """Provider managing SSE services with explicit lifecycle.

    - Lazy initialization with singleflight coordination (ensure_ready)
    - Thread-safe/Task-safe via asyncio.Lock for state mutations only
    - No awaiting while holding the lock to avoid deadlocks
    """

    def __init__(self, redis_service: RedisService | None = None) -> None:
        self._redis_service = redis_service or RedisService()
        self._redis_sse_service: RedisSSEService | None = None
        self._sse_connection_manager: SSEConnectionManager | None = None

        # Protect state changes; do not await I/O while holding this lock
        self._lock = asyncio.Lock()

        # Singleflight task to coordinate one-time initialization
        self._init_task: asyncio.Task | None = None

    async def ensure_ready(self) -> None:
        """Ensure the SSE services are initialized (singleflight).

        Safe for concurrent calls. Only creates one initialization task and
        awaits it without holding the internal lock.
        """
        # Fast path: already initialized
        if self._redis_sse_service is not None and self._sse_connection_manager is not None:
            return

        # If an init task exists, await it
        if self._init_task is not None:
            await self._init_task
            return

        # Create the init task under lock if still needed
        async with self._lock:
            if self._redis_sse_service is not None and self._sse_connection_manager is not None:
                return
            if self._init_task is None:
                self._init_task = asyncio.create_task(self._initialize())
            init_task = self._init_task

        # Await outside lock to avoid deadlocks
        try:
            await init_task
        finally:
            # Clear init task reference (allow retry if initialization failed)
            async with self._lock:
                self._init_task = None

    async def _initialize(self) -> None:
        """Perform actual initialization work (no locks inside)."""
        service = RedisSSEService(self._redis_service)
        await service.init_pubsub_client()
        manager = SSEConnectionManager(service)

        # Start periodic cleanup if enabled
        await manager.start_periodic_cleanup()

        # Publish state under lock without awaiting I/O
        async with self._lock:
            self._redis_sse_service = service
            self._sse_connection_manager = manager

    async def get_redis_sse_service(self) -> RedisSSEService:
        """Lazy-get RedisSSEService after ensuring readiness."""
        await self.ensure_ready()
        assert self._redis_sse_service is not None
        return self._redis_sse_service

    async def get_connection_manager(self) -> SSEConnectionManager:
        """Lazy-get SSEConnectionManager after ensuring readiness."""
        await self.ensure_ready()
        assert self._sse_connection_manager is not None
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
                    # Proactively signal all SSE connections to stop so generators exit quickly
                    try:
                        signaled = await manager.state_manager.preempt_all_connections(reason="shutdown")
                        if signaled:
                            logger.info("Signaled %d SSE connections to stop (shutdown)", signaled)
                    except Exception as e:
                        logger.debug(f"Error signaling SSE connections to stop: {e}")

                    # Stop periodic cleanup first
                    await manager.stop_periodic_cleanup()
                except Exception as e:
                    logger.warning(f"Error stopping periodic cleanup: {e}")

                try:
                    # Complete cleanup of all remaining stale connections
                    cleanup_summary = await manager.cleanup_all_stale_connections_for_shutdown(max_iterations=10)

                    if cleanup_summary["total_cleaned"] > 0:
                        logger.info(
                            f"Shutdown cleanup completed: cleaned {cleanup_summary['total_cleaned']} "
                            f"stale SSE connections in {cleanup_summary['iterations']} iteration(s), "
                            f"duration: {cleanup_summary['cleanup_duration_ms']:.2f}ms"
                        )

                    # Warn if cleanup was incomplete
                    if cleanup_summary["connections_after"] > 0:
                        logger.warning(
                            f"Shutdown cleanup incomplete: {cleanup_summary['connections_after']} "
                            f"connections remain after {cleanup_summary['iterations']} iterations. "
                            f"Redis counters may be inconsistent on next startup."
                        )

                except Exception as e:
                    logger.warning(f"Error during complete SSE cleanup: {e}")

                try:
                    # Reset global counter to prevent drift
                    pubsub_client = getattr(manager.redis_sse, "_pubsub_client", None)
                    if pubsub_client:
                        await pubsub_client.delete("global:sse_connections_count")
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
