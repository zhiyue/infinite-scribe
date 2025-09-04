"""Unit tests for launcher.signal_utils"""

import asyncio
import os
import signal

import pytest

from launcher.signal_utils import create_shutdown_signal_handler, register_shutdown_handler

pytestmark = pytest.mark.skipif(os.name == "nt", reason="Signal handler tests require POSIX loop")


@pytest.mark.asyncio
async def test_register_shutdown_handler_triggers_on_sigterm():
    shutdown = asyncio.Event()

    async def on_shutdown():
        shutdown.set()

    cleanup = register_shutdown_handler(on_shutdown)
    assert cleanup is not None

    # Send SIGTERM and ensure event is set
    loop = asyncio.get_running_loop()
    loop.call_later(0.05, lambda: os.kill(os.getpid(), signal.SIGTERM))

    await asyncio.wait_for(shutdown.wait(), timeout=1.0)

    # Cleanup handlers
    cleanup()


@pytest.mark.asyncio
async def test_create_shutdown_signal_handler_event_set_on_sigterm():
    event, cleanup = create_shutdown_signal_handler()
    assert event is not None

    loop = asyncio.get_running_loop()
    loop.call_later(0.05, lambda: os.kill(os.getpid(), signal.SIGTERM))

    await asyncio.wait_for(event.wait(), timeout=1.0)

    if cleanup:
        cleanup()
