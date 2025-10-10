"""EventBridge service adapter for Kafka -> SSE"""

from __future__ import annotations

import asyncio
import contextlib
from time import monotonic
from typing import Any

import structlog

from src.services.eventbridge.main import EventBridgeApplication

from ..types import ServiceStatus
from .base import BaseAdapter

logger = structlog.get_logger(__name__)


class EventBridgeAdapter(BaseAdapter):
    """Adapter for managing EventBridge service"""

    def __init__(self, config: dict[str, Any]):
        super().__init__("eventbridge", config)
        self._application: EventBridgeApplication | None = None
        self._task: asyncio.Task | None = None
        # Optional readiness wait (seconds)
        rt = config.get("ready_timeout")
        try:
            self._ready_timeout: float = float(rt) if rt is not None else 0.0
        except Exception:
            self._ready_timeout = 0.0

    async def start(self) -> bool:
        if self.status == ServiceStatus.RUNNING:
            logger.info("EventBridge already running; skip start")
            return False

        try:
            self.status = ServiceStatus.STARTING
            self._application = EventBridgeApplication()
            # Start in background
            self._task = asyncio.create_task(self._application.start())

            # Yield once to let the loop start
            await asyncio.sleep(0)
            if self._task.done():
                exc = self._task.exception()
                if exc is not None:
                    logger.error("EventBridge startup failed immediately", error=str(exc))
                    self.status = ServiceStatus.FAILED
                    return False

            # Optional short readiness wait: check service readiness
            if self._ready_timeout and self._ready_timeout > 0:
                started = await self._wait_until_ready(self._ready_timeout)
                if not started:
                    logger.warning("EventBridge not fully ready within timeout", timeout=self._ready_timeout)

            self.status = ServiceStatus.RUNNING
            logger.info("EventBridge startup initiated (background)")
            return True
        except Exception as e:
            logger.error("Failed to start EventBridge", error=str(e))
            self.status = ServiceStatus.FAILED
            return False

    async def stop(self, timeout: int = 10) -> bool:
        if self.status != ServiceStatus.RUNNING:
            logger.info("EventBridge not running; nothing to stop")
            return True

        self.status = ServiceStatus.STOPPING
        try:
            if self._application is not None:
                await asyncio.wait_for(self._application.stop(), timeout=timeout)
            if self._task is not None:
                # Ensure task completes
                try:
                    await asyncio.wait_for(self._task, timeout=timeout)
                except TimeoutError:
                    self._task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await self._task
                self._task = None
            self._application = None
            self.status = ServiceStatus.STOPPED
            logger.info("EventBridge stopped successfully")
            return True
        except Exception as e:
            logger.error("Failed to stop EventBridge", error=str(e))
            self.status = ServiceStatus.STOPPED
            return True

    async def health_check(self) -> dict[str, Any]:
        # Basic health: running status + service health
        application = self._application
        service_healthy = False
        bridge_service_status = {}

        if application and application.bridge_service:
            try:
                bridge_service_status = application.bridge_service.get_health_status()
                service_healthy = bridge_service_status.get("healthy", False)
            except Exception as e:
                logger.warning("Failed to get bridge service health", error=str(e))

        background_alive = self._task is not None and not self._task.done()
        status = (
            "running"
            if (self.status == ServiceStatus.RUNNING and background_alive and service_healthy)
            else "starting"
            if self.status == ServiceStatus.STARTING
            else "degraded"
        )

        return {
            "status": status,
            "service_healthy": service_healthy,
            "background_alive": background_alive,
            "bridge_service_status": bridge_service_status,
        }

    async def _wait_until_ready(self, timeout: float) -> bool:
        start = monotonic()
        while monotonic() - start < timeout:
            application = self._application
            if application and application.bridge_service:
                try:
                    health_status = application.bridge_service.get_health_status()
                    if health_status.get("healthy", False):
                        return True
                except Exception:
                    pass  # Continue waiting
            await asyncio.sleep(0.1)
        return False
