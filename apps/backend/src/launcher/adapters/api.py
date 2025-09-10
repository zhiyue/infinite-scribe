"""API service adapter for managing FastAPI Gateway"""

import asyncio
import contextlib
import socket
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
        self._runtime_mode: LaunchMode | None = None  # Track actual runtime mode
        # Use launcher-provided timeout if available (default 10s)
        try:
            self._startup_timeout: float = float(self.config.get("startup_timeout", 10))
        except Exception:
            self._startup_timeout = 10.0

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
            except ValueError as e:
                raise ValueError(f"Unsupported launch mode: {mode_cfg}") from e

        self._host = self.config.get("host", self._host)
        self._port = int(self.config.get("port", self._port))
        self.status = ServiceStatus.STARTING

        try:
            # Pre-check port availability to avoid uvicorn's SystemExit on bind errors
            if not self._is_port_available(self._host, self._port):
                logger.error("api_port_in_use", host=self._host, port=self._port)
                self.status = ServiceStatus.STOPPED
                return False

            # When reload=True and mode=SINGLE, automatically switch to MULTI for stability
            if mode == LaunchMode.SINGLE and reload_cfg:
                logger.info(
                    "reload_requested_in_single_mode_switching_to_multi",
                    reason="uvicorn reload is more reliable under subprocess",
                )
                mode = LaunchMode.MULTI

            if mode == LaunchMode.SINGLE:
                await self._start_single_process(reload_cfg)
            elif mode == LaunchMode.MULTI:
                await self._start_multi_process(reload_cfg)
            else:
                raise ValueError(f"Unsupported launch mode: {mode}")

            self._runtime_mode = mode  # Store the actual runtime mode
            self.status = ServiceStatus.RUNNING
            logger.info("API Gateway started", host=self._host, port=self._port, mode=mode.value)
            return True
        except SystemExit as e:
            logger.error("API Gateway failed to start (SystemExit)", exit_code=e.code)
            self.status = ServiceStatus.STOPPED
            return False
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
        max_wait = self._startup_timeout
        wait_time = 0.0
        while wait_time < max_wait:
            # If the task finished, surface exceptions (e.g., SystemExit from port binding error)
            if self._task.done():
                try:
                    await self._task
                except SystemExit as e:
                    raise e
                except Exception as e:
                    raise RuntimeError(f"API server task failed: {e}") from e

            # If server started, give it a moment to catch any immediate failures, then return
            if self._server.started:
                extra_wait = 0.2
                while extra_wait > 0 and not self._task.done():
                    await asyncio.sleep(0.1)
                    extra_wait -= 0.1

                if self._task.done():
                    try:
                        await self._task
                    except SystemExit as e:
                        raise e
                    except Exception as e:
                        raise RuntimeError(f"API server task failed after startup: {e}") from e

                return

            await asyncio.sleep(0.1)
            wait_time += 0.1

        # Timeout occurred
        if not self._server.started:
            reasons = await self._diagnose_dependencies()
            hint = self._format_diagnostic_hint(reasons)
            raise RuntimeError(f"API server failed to start within {max_wait:.0f} seconds. {hint}")
        else:
            raise RuntimeError(f"API server startup validation timed out after {max_wait:.0f} seconds")

    async def _start_multi_process(self, reload: bool) -> None:
        """Start API Gateway in multi-process mode using subprocess"""
        args = ProcessManager.build_uvicorn_command(self._host, self._port, reload)
        kwargs = ProcessManager.create_subprocess_args(args)

        # Reuse BaseAdapter.process slot
        self.process = await asyncio.create_subprocess_exec(*args, **kwargs)
        logger.info("Started API Gateway subprocess", pid=self.process.pid if self.process else None)

        # Wait for process to be ready by checking if it's accepting connections
        max_wait = self._startup_timeout
        wait_time = 0.0
        import httpx

        while wait_time < max_wait:
            # Check if process has exited
            if self.process and self.process.returncode is not None:
                raise RuntimeError(f"API process exited unexpectedly with code {self.process.returncode}")

            try:
                async with httpx.AsyncClient() as client:
                    # Use 127.0.0.1 for health checks when host is 0.0.0.0
                    health_check_host = "127.0.0.1" if self._host == "0.0.0.0" else self._host
                    response = await client.get(f"http://{health_check_host}:{self._port}/health", timeout=1.0)
                    if response.status_code == 200:
                        break
            except (httpx.RequestError, httpx.TimeoutException):
                pass

            await asyncio.sleep(0.5)
            wait_time += 0.5

        if wait_time >= max_wait:
            reasons = await self._diagnose_dependencies()
            hint = self._format_diagnostic_hint(reasons)
            raise RuntimeError(f"API server failed to respond within {max_wait:.0f} seconds. {hint}")

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
            self._runtime_mode = None
            logger.info("API Gateway stopped successfully")
            return True
        except Exception as e:
            logger.error("Error stopping API Gateway", error=str(e))
            self.status = ServiceStatus.STOPPED
            self._runtime_mode = None
            return True

    async def _stop_single_process(self) -> None:
        """Stop single-process mode; prefer graceful should_exit, fallback to cancel"""
        if self._task:
            if self._server is not None:
                self._server.should_exit = True
                with contextlib.suppress(asyncio.CancelledError):
                    await self._task
            else:
                self._task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._task
            self._task = None
            self._server = None

    async def health_check(self) -> dict[str, Any]:
        """Return adapter health information"""
        # Use the actual runtime mode if available, otherwise fall back to configured mode
        if self._runtime_mode is not None:
            mode_value = self._runtime_mode.value
        else:
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
        # Use 127.0.0.1 for URLs when host is 0.0.0.0 (bind all interfaces)
        url_host = "127.0.0.1" if self._host == "0.0.0.0" else self._host
        return f"http://{url_host}:{self._port}"

    def _is_port_available(self, host: str, port: int) -> bool:
        """Return True if the TCP port is available to bind on the given host.

        - Port 0 always considered available (OS will choose a free port).
        - Uses a bind attempt to detect conflicts early.
        """
        if port == 0:
            return True
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
            return True
        except OSError:
            return False

    async def _tcp_check(self, host: str, port: int, timeout: float = 1.5) -> tuple[bool, str | None]:
        """Lightweight TCP connectivity check to a host/port."""
        try:
            reader_task = asyncio.open_connection(host, port)
            await asyncio.wait_for(reader_task, timeout=timeout)
            return True, None
        except Exception as e:
            return False, str(e)

    async def _diagnose_dependencies(self) -> dict[str, dict[str, Any]]:
        """Best-effort diagnostics for common dependencies when startup is slow/failing.

        Returns a dict like:
        {
          "postgres": {"ok": False, "host": "localhost", "port": 5432, "error": "..."},
          "neo4j": {"ok": True, ...},
          "redis": {"ok": False, ...}
        }
        """
        reasons: dict[str, dict[str, Any]] = {}
        try:
            from src.core.config import settings

            checks = {
                "postgres": (settings.database.postgres_host, int(settings.database.postgres_port)),
                "neo4j": (settings.database.neo4j_host, int(settings.database.neo4j_port)),
                "redis": (settings.database.redis_host, int(settings.database.redis_port)),
            }

            tasks = {name: asyncio.create_task(self._tcp_check(host, port)) for name, (host, port) in checks.items()}
            for name, (host, port) in checks.items():
                ok, err = await tasks[name]
                reasons[name] = {"ok": ok, "host": host, "port": port}
                if not ok:
                    reasons[name]["error"] = err
        except Exception as e:
            logger.warning("dependency_diagnostics_failed", error=str(e))
        return reasons

    def _format_diagnostic_hint(self, reasons: dict[str, dict[str, Any]]) -> str:
        """Format a short human-readable hint from diagnostics."""
        if not reasons:
            return "Check server logs for details."
        bad = [name for name, info in reasons.items() if not info.get("ok")]
        if not bad:
            return "Check server logs for details."
        parts = []
        for name in bad:
            info = reasons.get(name, {})
            host = info.get("host")
            port = info.get("port")
            parts.append(f"{name}({host}:{port})")
        return "Potential dependency issues: " + ", ".join(parts)
