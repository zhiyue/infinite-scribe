"""Process management utilities for adapters"""

import asyncio
import os
import signal
import sys
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ProcessManager:
    """Utility class for cross-platform process management"""

    @staticmethod
    def create_subprocess_args(_command: list[str], **kwargs: Any) -> dict[str, Any]:
        """Create subprocess arguments with platform-specific handling"""
        if os.name != "nt":
            # POSIX: create new process group for signal handling
            return {"preexec_fn": os.setsid, **kwargs}
        else:
            # Windows: use CREATE_NEW_PROCESS_GROUP
            return {"creationflags": 0x00000200, **kwargs}

    @staticmethod
    async def terminate_process(process: asyncio.subprocess.Process, timeout: int = 30) -> None:
        """Terminate a process gracefully with fallback to force kill"""
        if not process or process.returncode is not None:
            return

        try:
            # Send termination signal
            if os.name != "nt":
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                ctrl_break = getattr(signal, "CTRL_BREAK_EVENT", 1)
                process.send_signal(ctrl_break)

            # Wait with timeout
            await asyncio.wait_for(process.wait(), timeout=timeout)

        except (TimeoutError, ProcessLookupError):
            logger.warning(f"Process {process.pid} didn't respond gracefully, force killing")
            try:
                # Force kill
                if os.name != "nt":
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    process.kill()
                await process.wait()
            except ProcessLookupError:
                pass  # Already dead

    @staticmethod
    def build_uvicorn_command(host: str, port: int, reload: bool = False) -> list[str]:
        """Build uvicorn command arguments"""
        args = [sys.executable, "-m", "uvicorn", "src.api.main:app", 
                "--host", host, "--port", str(port)]
        if reload:
            args.append("--reload")
        return args
