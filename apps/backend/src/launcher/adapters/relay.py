"""Relay service adapter for Outbox -> Kafka"""

from __future__ import annotations

import asyncio
import contextlib
from time import monotonic
from typing import Any

import structlog

from src.services.outbox.relay import OutboxRelayService

from ..types import ServiceStatus
from .base import BaseAdapter

logger = structlog.get_logger(__name__)


class RelayAdapter(BaseAdapter):
    """Adapter for managing Outbox Relay service"""

    def __init__(self, config: dict[str, Any]):
        super().__init__("relay", config)
        self._service: OutboxRelayService | None = None
        self._task: asyncio.Task | None = None
        # Optional readiness wait (seconds)
        rt = config.get("ready_timeout")
        try:
            self._ready_timeout: float = float(rt) if rt is not None else 0.0
        except Exception:
            self._ready_timeout = 0.0

    async def start(self) -> bool:
        if self.status == ServiceStatus.RUNNING:
            logger.info("Relay already running; skip start")
            return False

        try:
            self.status = ServiceStatus.STARTING
            self._service = OutboxRelayService()
            # Start in background
            self._task = asyncio.create_task(self._service.run_forever())

            # Yield once to let the loop start
            await asyncio.sleep(0)
            if self._task.done():
                exc = self._task.exception()
                if exc is not None:
                    logger.error("Relay startup failed immediately", error=str(exc))
                    self.status = ServiceStatus.FAILED
                    return False

            # Optional short readiness wait: check service producer readiness
            if self._ready_timeout and self._ready_timeout > 0:
                started = await self._wait_until_ready(self._ready_timeout)
                if not started:
                    logger.warning("Relay not fully ready within timeout", timeout=self._ready_timeout)

            self.status = ServiceStatus.RUNNING
            logger.info("Relay startup initiated (background)")
            return True
        except Exception as e:
            logger.error("Failed to start relay", error=str(e))
            self.status = ServiceStatus.FAILED
            return False

    async def stop(self, timeout: int = 10) -> bool:
        if self.status != ServiceStatus.RUNNING:
            logger.info("Relay not running; nothing to stop")
            return True

        self.status = ServiceStatus.STOPPING
        try:
            if self._service is not None:
                await asyncio.wait_for(self._service.stop(), timeout=timeout)
            if self._task is not None:
                # Ensure task completes
                try:
                    await asyncio.wait_for(self._task, timeout=timeout)
                except TimeoutError:
                    self._task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await self._task
                self._task = None
            self._service = None
            self.status = ServiceStatus.STOPPED
            logger.info("Relay stopped successfully")
            return True
        except Exception as e:
            logger.error("Failed to stop relay", error=str(e))
            self.status = ServiceStatus.STOPPED
            return True

    async def health_check(self) -> dict[str, Any]:
        # Basic health: running status + internal readiness hints
        service = self._service
        producer_ready = bool(getattr(service, "_producer", None)) if service else False
        background_alive = self._task is not None and not self._task.done()
        status = (
            "running" if (self.status == ServiceStatus.RUNNING and background_alive and producer_ready) else "starting"
        )
        return {
            "status": status,
            "producer_ready": producer_ready,
            "background_alive": background_alive,
        }

    async def _wait_until_ready(self, timeout: float) -> bool:
        start = monotonic()
        while monotonic() - start < timeout:
            service = self._service
            if service and getattr(service, "_producer", None):
                return True
            await asyncio.sleep(0.1)
        return False
