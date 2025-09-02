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
        cleanup_functions = []

        # Register both SIGINT and SIGTERM for comprehensive coverage
        # This takes ownership from any previous handlers (like AgentLauncher)
        loop.add_signal_handler(signal.SIGINT, callback_wrapper)
        cleanup_functions.append(lambda: loop.remove_signal_handler(signal.SIGINT))

        loop.add_signal_handler(signal.SIGTERM, callback_wrapper)
        cleanup_functions.append(lambda: loop.remove_signal_handler(signal.SIGTERM))

        logger.info("Registered POSIX signal handlers", signals="SIGINT,SIGTERM")

        def combined_cleanup():
            for cleanup_fn in cleanup_functions:
                try:
                    cleanup_fn()
                except Exception as e:
                    logger.warning("Individual signal cleanup failed", error=str(e))

        return combined_cleanup
    except Exception as e:
        logger.error("Failed to register POSIX signal handlers", error=str(e))
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
    Register a unified shutdown signal handler that takes ownership of SIGINT/SIGTERM

    This function registers handlers for both SIGINT and SIGTERM on POSIX systems,
    and SIGINT only on Windows. It takes precedence over any previously registered
    handlers (e.g., from AgentLauncher) to ensure unified signal management.

    :param callback: Async shutdown callback function
    :return: Cleanup function to remove all registered signal handlers
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

    注：如果信号注册失败，将自动回退到捕获KeyboardInterrupt
    """
    shutdown_event = asyncio.Event()
    signal_registered_successfully = True

    async def shutdown_handler():
        shutdown_event.set()
        logger.info("Shutdown signal received")

    # 注册信号处理器
    cleanup = register_shutdown_handler(shutdown_handler)

    # 检查是否成功注册（通过检查cleanup函数是否为no-op）
    try:
        # 如果信号注册失败，register_shutdown_handler会返回lambda: None
        # 我们可以通过检查其字节码来判断是否为no-op函数
        if cleanup.__code__.co_code == (lambda: None).__code__.co_code:
            signal_registered_successfully = False
            logger.warning("Signal registration failed, will rely on KeyboardInterrupt fallback")
    except Exception:
        # 如果检查失败，假设注册成功，让后续逻辑处理
        pass

    try:
        # 等待信号或KeyboardInterrupt
        if signal_registered_successfully:
            await shutdown_event.wait()
        else:
            # 信号注册失败时的回退策略：等待KeyboardInterrupt
            logger.info("Using KeyboardInterrupt fallback for shutdown detection")
            # 创建一个永远不会完成的task，让KeyboardInterrupt来中断它
            await asyncio.sleep(float("inf"))
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, proceeding with shutdown")
        # KeyboardInterrupt被捕获，正常继续
    finally:
        # 清理信号处理器
        try:
            cleanup()
        except Exception as e:
            logger.warning("Failed to cleanup signal handler during shutdown", error=str(e))
