import asyncio
import os
import signal
from collections.abc import Awaitable, Callable
from typing import Protocol

import structlog

logger = structlog.get_logger(__name__)


class CleanupFunction(Protocol):
    """Protocol for cleanup functions"""

    def __call__(self) -> None: ...


def _create_safe_callback_wrapper(callback: Callable[[], Awaitable[None]]) -> Callable[[], None]:
    """Create a wrapper that safely executes async callbacks in signal context"""

    def wrapper() -> None:
        try:
            loop = asyncio.get_running_loop()
            # Use call_soon_threadsafe to safely schedule async task
            loop.call_soon_threadsafe(lambda: asyncio.create_task(callback()))
        except RuntimeError:
            logger.warning("No running event loop for signal callback")

    return wrapper


def _register_posix_signal_handler(callback_wrapper: Callable[[], None]) -> CleanupFunction | None:
    """Register signal handler for POSIX systems using asyncio event loop"""
    try:
        loop = asyncio.get_running_loop()
        # Only register SIGINT to avoid conflicts with AgentLauncher signal handlers
        loop.add_signal_handler(signal.SIGINT, callback_wrapper)
        logger.info("Registered POSIX signal handler", signal="SIGINT")

        return lambda: loop.remove_signal_handler(signal.SIGINT)
    except Exception as e:
        logger.error("Failed to register POSIX signal handler", error=str(e))
        return None


def _register_windows_signal_handler(callback_wrapper: Callable[[], None]) -> CleanupFunction | None:
    """Register signal handler for Windows using signal.signal fallback"""
    try:
        # Windows only supports SIGINT, use signal.signal fallback
        original_handler = signal.signal(signal.SIGINT, lambda sig, frame: callback_wrapper())
        logger.info("Registered Windows signal handler", signal="SIGINT")

        return lambda: signal.signal(signal.SIGINT, original_handler)
    except Exception as e:
        logger.error("Failed to register Windows signal handler", error=str(e))
        return None


def register_shutdown_handler(callback: Callable[[], Awaitable[None]]) -> Callable[[], None]:
    """
    Register a shutdown signal handler (lightweight utility function)

    :param callback: Async shutdown callback function
    :return: Cleanup function to remove the signal handler
    """
    callback_wrapper = _create_safe_callback_wrapper(callback)

    # Register platform-specific signal handler
    if os.name != "nt":  # POSIX systems
        cleanup_fn = _register_posix_signal_handler(callback_wrapper)
    else:  # Windows systems
        cleanup_fn = _register_windows_signal_handler(callback_wrapper)

    # Return cleanup function or no-op if registration failed
    if cleanup_fn is None:
        logger.warning("Signal handler registration failed, returning no-op cleanup")
        return lambda: None

    def cleanup() -> None:
        """Clean up the signal handler"""
        try:
            cleanup_fn()
            logger.info("Signal handler cleaned up")
        except Exception as e:
            logger.warning("Signal handler cleanup failed", error=str(e))

    return cleanup


async def wait_for_shutdown_signal() -> None:
    """
    等待关闭信号（便利函数）
    """
    shutdown_event = asyncio.Event()

    async def shutdown_handler():
        shutdown_event.set()
        logger.info("Shutdown signal received")

    # 注册信号处理器
    cleanup = register_shutdown_handler(shutdown_handler)

    try:
        # 等待信号
        await shutdown_event.wait()
    finally:
        # 清理信号处理器
        cleanup()
