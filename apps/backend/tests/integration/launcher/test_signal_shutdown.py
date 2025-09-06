"""Integration test: AgentLauncher reacts to SIGTERM via signal_utils"""

import asyncio
import os
import signal
from typing import Any

import pytest
from src.agents.base import BaseAgent
from src.agents.launcher import AgentLauncher

pytestmark = pytest.mark.skipif(os.name == "nt", reason="Signal handler tests require POSIX loop")


class IdleAgent(BaseAgent):
    def __init__(self):
        # No consume/produce topics to avoid Kafka dependency
        super().__init__(name="idle", consume_topics=[], produce_topics=[])
        self.stopped = asyncio.Event()

    async def process_message(self, message: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any] | None:  # pragma: no cover - not used
        return None

    async def on_stop(self):
        self.stopped.set()


@pytest.mark.asyncio
async def test_launcher_graceful_shutdown_on_sigterm():
    launcher = AgentLauncher()
    agent = IdleAgent()
    launcher.agents = {"idle": agent}

    # Register signal handlers via signal_utils
    launcher.setup_signal_handlers(enable=True)

    # Start in background
    task = asyncio.create_task(launcher.start_all())

    # Give the agent some time to enter idle loop
    await asyncio.sleep(0.05)
    assert launcher.running is True

    # Trigger SIGTERM
    os.kill(os.getpid(), signal.SIGTERM)

    # Launcher should stop gracefully
    await asyncio.wait_for(task, timeout=2.0)

    assert launcher.running is False
    assert agent.is_running is False
    assert agent.stopped.is_set()

    # Cleanup signal handlers to avoid interference with other tests
    launcher.cleanup_signal_handlers()
