"""Tests for BaseAgent config validation logic."""

import pytest
from src.agents.base import BaseAgent
from src.core.config import settings


class Dummy(BaseAgent):
    def __init__(self):
        super().__init__(name="d", consume_topics=[], produce_topics=[])

    async def process_message(
        self, message: dict[str, object]
    ) -> dict[str, object] | None:  # pragma: no cover - unused
        return None


def test_invalid_retries(monkeypatch):
    monkeypatch.setattr(settings, "agent_max_retries", -1, raising=False)
    with pytest.raises(ValueError):
        Dummy()


def test_invalid_backoff(monkeypatch):
    monkeypatch.setattr(settings, "agent_retry_backoff_ms", -1, raising=False)
    with pytest.raises(ValueError):
        Dummy()


def test_invalid_commit_batch_size(monkeypatch):
    monkeypatch.setattr(settings, "agent_commit_batch_size", 0, raising=False)
    with pytest.raises(ValueError):
        Dummy()


def test_invalid_commit_interval(monkeypatch):
    monkeypatch.setattr(settings, "agent_commit_interval_ms", -1, raising=False)
    with pytest.raises(ValueError):
        Dummy()
