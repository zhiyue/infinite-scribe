"""Daemon mode handling for CLI launcher"""

import asyncio
from collections.abc import Callable


def handle_daemon_mode(orchestrator, service_names: list[str]) -> None:
    """
    Handle daemon mode: wait for shutdown signal and gracefully stop services

    :param orchestrator: The orchestrator instance to use for shutdown
    :param service_names: List of service names to shutdown
    """

    print("🔄 Stay mode enabled, waiting for shutdown signal (Ctrl+C)...")

    try:
        _wait_and_shutdown(orchestrator, service_names)
    except KeyboardInterrupt:
        _handle_interrupt(orchestrator, service_names)
    except Exception as e:
        _handle_error(orchestrator, service_names, e)


def handle_daemon_mode_with_early_registration(
    orchestrator,
    service_names: list[str],
    shutdown_event: asyncio.Event,
    cleanup_fn: Callable[[], None],
) -> None:
    """
    Handle daemon mode with pre-registered signal handlers

    :param orchestrator: The orchestrator instance to use for shutdown
    :param service_names: List of service names to shutdown
    :param shutdown_event: Pre-registered asyncio.Event that will be set on signal
    :param cleanup_fn: Pre-registered cleanup function
    """
    if cleanup_fn is None:
        raise RuntimeError("handle_daemon_mode_with_early_registration called with failed registration")

    if shutdown_event is None:
        raise RuntimeError("handle_daemon_mode_with_early_registration called with invalid shutdown_event")

    print("🔄 Stay mode enabled (early registration), waiting for shutdown signal (Ctrl+C)...")

    try:
        _wait_and_shutdown_with_event(orchestrator, service_names, shutdown_event)
    except KeyboardInterrupt:
        _handle_interrupt(orchestrator, service_names)
    except Exception as e:
        _handle_error(orchestrator, service_names, e)
    finally:
        _cleanup_signal_handlers(cleanup_fn)


def _wait_and_shutdown(orchestrator, service_names: list[str]) -> None:
    """Wait for shutdown signal and stop services"""
    from .signal_utils import wait_for_shutdown_signal

    asyncio.run(wait_for_shutdown_signal())
    print("📡 Shutdown signal received, stopping services...")
    asyncio.run(orchestrator.orchestrate_shutdown(service_names))
    print("✅ Services stopped gracefully")


def _wait_and_shutdown_with_event(orchestrator, service_names: list[str], shutdown_event: asyncio.Event) -> None:
    """Wait for pre-registered shutdown event and stop services"""
    asyncio.run(shutdown_event.wait())
    print("📡 Shutdown signal received, stopping services...")
    asyncio.run(orchestrator.orchestrate_shutdown(service_names))
    print("✅ Services stopped gracefully")


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
