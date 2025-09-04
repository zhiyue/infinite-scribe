"""Daemon mode handling for CLI launcher"""

import asyncio
from collections.abc import Callable


def handle_daemon_mode(orchestrator, service_names: list[str]) -> None:
    """
    Backwards-compatible hook for daemon mode selection.

    This function intentionally does not manage event loops; the actual
    wait/shutdown flow is handled in commands._handle_stay_mode to ensure
    services remain on the same asyncio loop.
    """
    print("🔄 Stay mode enabled (compat hook)")


def handle_daemon_mode_with_early_registration(
    orchestrator,
    service_names: list[str],
    shutdown_event: asyncio.Event,
    cleanup_fn: Callable[[], None],
) -> None:
    """
    Backwards-compatible hook for early registration mode selection.

    This function intentionally does not manage event loops; the actual
    wait/shutdown flow is handled in commands._handle_stay_mode.
    """
    print("🔄 Stay mode enabled (early registration compat hook)")


def _wait_and_shutdown(orchestrator, service_names: list[str]) -> None:
    """Deprecated: handled by commands._handle_stay_mode"""
    print("(deprecated) _wait_and_shutdown invoked")


def _wait_and_shutdown_with_event(orchestrator, service_names: list[str], shutdown_event: asyncio.Event) -> None:
    """Deprecated: handled by commands._handle_stay_mode"""
    print("(deprecated) _wait_and_shutdown_with_event invoked")


def _handle_interrupt(orchestrator, service_names: list[str]) -> None:
    """Handle keyboard interrupt during daemon mode"""
    print("📡 Interrupted by user, stopping services...")
    try:
        asyncio.run(orchestrator.orchestrate_shutdown(service_names))
        print("✅ Services stopped gracefully")
    except Exception as e:
        print(f"❌ Error during shutdown: {e}")
        raise


def _handle_error(orchestrator, service_names: list[str], error: Exception) -> None:
    """Handle errors during daemon mode"""
    print(f"❌ Error during shutdown: {error}")
    raise


def _cleanup_signal_handlers(cleanup_fn: Callable[[], None]) -> None:
    """Clean up signal handlers"""
    try:
        cleanup_fn()
    except Exception as e:
        print(f"⚠️  Warning: Failed to cleanup signal handlers: {e}")
