"""Unit tests for BaseAgent stop idempotency"""

import asyncio
from typing import Any

import pytest
from src.agents.base import BaseAgent


class DummyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="dummy", consume_topics=[], produce_topics=[])
        self.stop_calls = 0

    async def process_message(
        self, message: dict[str, Any]
    ) -> dict[str, Any] | None:  # pragma: no cover - not used here
        return None

    async def on_stop(self):  # count on_stop invocations
        self.stop_calls += 1


@pytest.mark.asyncio
async def test_base_agent_stop_idempotent_sequential():
    agent = DummyAgent()
    agent.is_running = True

    await agent.stop()
    # Second call should be a no-op
    await agent.stop()

    assert agent.is_running is False
    assert agent.stop_calls == 1


@pytest.mark.asyncio
async def test_base_agent_stop_idempotent_concurrent():
    agent = DummyAgent()
    agent.is_running = True

    # Two concurrent stop calls should still result in single on_stop
    await asyncio.gather(agent.stop(), agent.stop())

    assert agent.is_running is False
    assert agent.stop_calls == 1
