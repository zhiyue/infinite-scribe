"""API service adapter for managing FastAPI Gateway"""

import asyncio
import contextlib
from typing import Any

import structlog
import uvicorn

from ..types import LaunchMode, ServiceStatus
from .base import BaseAdapter
from .process_utils import ProcessManager

logger = structlog.get_logger(__name__)


class ApiAdapter(BaseAdapter):
    """Adapter for managing API Gateway service"""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the API adapter"""
        super().__init__("api", config or {})
        self._task: asyncio.Task | None = None
        self._server: uvicorn.Server | None = None
        self._host: str = self.config.get("host", "0.0.0.0")
        self._port: int = int(self.config.get("port", 8000))

    async def start(self) -> bool:
        """Start the API Gateway service using config values"""
        if self.status == ServiceStatus.RUNNING:
            logger.info("API adapter is already running; skip start")
            return False

        # Resolve mode and reload from config
        mode_cfg = self.config.get("mode", LaunchMode.SINGLE)
        reload_cfg = bool(self.config.get("reload", False))

        # Convert mode if string
        mode = mode_cfg
        if isinstance(mode_cfg, str):
            try:
                mode = LaunchMode(mode_cfg)
            except ValueError:
                raise ValueError(f"Unsupported launch mode: {mode_cfg}")

        self._host = self.config.get("host", self._host)
        self._port = int(self.config.get("port", self._port))
        self.status = ServiceStatus.STARTING

        try:
            if mode == LaunchMode.SINGLE:
                await self._start_single_process(reload_cfg)
            elif mode == LaunchMode.MULTI:
                await self._start_multi_process(reload_cfg)
            else:
                raise ValueError(f"Unsupported launch mode: {mode}")

            self.status = ServiceStatus.RUNNING
            logger.info("API Gateway started", host=self._host, port=self._port, mode=mode.value)
            return True
        except Exception as e:
            logger.error("Failed to start API Gateway", error=str(e))
            self.status = ServiceStatus.STOPPED
            return False

    async def _start_single_process(self, reload: bool) -> None:
        """Start API Gateway in single-process mode using asyncio task"""
        config = uvicorn.Config("src.api.main:app", host=self._host, port=self._port, reload=reload, log_level="info")
        self._server = uvicorn.Server(config)
        self._task = asyncio.create_task(self._server.serve())

        # Wait for server to be ready
        max_wait = 10  # Max 10 seconds
        wait_time = 0.0
        while not self._server.started and wait_time < max_wait:
            await asyncio.sleep(0.1)
            wait_time += 0.1

        if not self._server.started:
            raise RuntimeError(f"API server failed to start within {max_wait} seconds")

    async def _start_multi_process(self, reload: bool) -> None:
        """Start API Gateway in multi-process mode using subprocess"""
        args = ProcessManager.build_uvicorn_command(self._host, self._port, reload)
        kwargs = ProcessManager.create_subprocess_args(args)

        # Reuse BaseAdapter.process slot
        self.process = await asyncio.create_subprocess_exec(*args, **kwargs)
        logger.info("Started API Gateway subprocess", pid=self.process.pid if self.process else None)

        # Wait for process to be ready by checking if it's accepting connections
        max_wait = 10  # Max 10 seconds
        wait_time = 0.0
        import httpx

        while wait_time < max_wait:
            # Check if process has exited
            if self.process and self.process.returncode is not None:
                raise RuntimeError(f"API process exited unexpectedly with code {self.process.returncode}")

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"http://{self._host}:{self._port}/health", timeout=1.0)
                    if response.status_code == 200:
                        break
            except (httpx.RequestError, httpx.TimeoutException):
                pass  # Server not ready yet

            await asyncio.sleep(0.5)
            wait_time += 0.5

        if wait_time >= max_wait:
            raise RuntimeError(f"API server failed to respond within {max_wait} seconds")

    async def stop(self, timeout: int = 10) -> bool:
        """Stop the API Gateway service (idempotent)"""
        if self.status != ServiceStatus.RUNNING:
            logger.info("API adapter not running; nothing to stop")
            return True

        self.status = ServiceStatus.STOPPING

        try:
            if self._task is not None:
                await self._stop_single_process()
            elif self.process is not None:
                await ProcessManager.terminate_process(self.process, timeout)
                self.process = None

            self.status = ServiceStatus.STOPPED
            logger.info("API Gateway stopped successfully")
            return True
        except Exception as e:
            logger.error("Error stopping API Gateway", error=str(e))
            self.status = ServiceStatus.STOPPED
            return True  # Force cleanup even on error

    async def _stop_single_process(self) -> None:
        """Stop single-process mode; prefer graceful should_exit, fallback to cancel"""
        if self._task:
            if self._server is not None:
                # Request graceful shutdown
                self._server.should_exit = True
                with contextlib.suppress(asyncio.CancelledError):
                    await self._task
            else:
                # Fallback: cancel the task if server ref missing
                self._task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._task
            self._task = None
            self._server = None

    async def health_check(self) -> dict[str, Any]:
        """Return adapter health information"""
        # Get mode and ensure it's consistently a string value
        mode_config = self.config.get("mode", LaunchMode.SINGLE)
        if isinstance(mode_config, LaunchMode):
            mode_value = mode_config.value
        elif isinstance(mode_config, str):
            mode_value = mode_config
        else:
            mode_value = LaunchMode.SINGLE.value

        data: dict[str, Any] = {
            "status": self.status.value,
            "mode": mode_value,
            "url": self.get_url(),
        }
        return data

    def get_url(self) -> str:
        """Get the API Gateway URL"""
        return f"http://{self._host}:{self._port}"

    # Backward-compat method presence for structure tests
    def get_status_str(self) -> str:
        """Return current status as string (for compatibility with older checks)"""
        return self.get_status().value
