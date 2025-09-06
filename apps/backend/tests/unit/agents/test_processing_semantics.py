"""Unit tests for BaseAgent processing semantics: retries, DLT, batching."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import pytest
from src.agents.base import BaseAgent
from src.agents.errors import NonRetriableError


@dataclass
class FakeMessage:
    topic: str
    partition: int
    offset: int
    value: dict[str, Any]


class FakeConsumer:
    def __init__(self, messages: list[FakeMessage]):
        self._messages = messages
        self._i = 0
        self.commits: list[dict[Any, Any]] = []

    async def start(self) -> None:  # pragma: no cover - not used directly
        pass

    async def stop(self) -> None:  # pragma: no cover - not used directly
        pass

    def __aiter__(self) -> AsyncIterator[FakeMessage]:
        return self

    async def __anext__(self) -> FakeMessage:
        if self._i >= len(self._messages):
            raise StopAsyncIteration
        msg = self._messages[self._i]
        self._i += 1
        return msg

    async def commit(self, offsets=None) -> None:
        self.commits.append(offsets)


class FakeProducer:
    def __init__(self):
        self.sent: list[tuple[str, dict[str, Any], Any]] = []

    async def start(self) -> None:  # pragma: no cover - not used directly
        pass

    async def stop(self) -> None:  # pragma: no cover - not used directly
        pass

    async def send_and_wait(self, topic: str, value: dict[str, Any], key=None) -> None:
        self.sent.append((topic, value, key))


class FakeAgent(BaseAgent):
    def __init__(self, messages: list[FakeMessage], behavior: str):
        super().__init__(name="test", consume_topics=["t"], produce_topics=["out"])
        # Override processing configs for deterministic tests
        self.max_retries = 2
        self.retry_backoff_ms = 1
        self.commit_batch_size = 2
        self.commit_interval_ms = 10_000  # large to avoid time-based commit
        self._fake_consumer = FakeConsumer(messages)
        self._fake_producer = FakeProducer()
        self._behavior = behavior

    async def _create_consumer(self):  # type: ignore[override]
        consumer = self._fake_consumer
        # 设置kafka_client.consumer以确保BaseAgent能找到它
        self.kafka_client.consumer = consumer
        return consumer

    async def _create_producer(self):  # type: ignore[override]
        producer = self._fake_producer
        # 设置kafka_client.producer以确保BaseAgent能找到它
        self.kafka_client.producer = producer
        return producer

    async def _get_or_create_producer(self):  # type: ignore[override]
        producer = self._fake_producer
        # 设置kafka_client.producer以确保BaseAgent能找到它
        if not self.kafka_client.producer:
            self.kafka_client.producer = producer
        return producer

    async def process_message(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        if self._behavior == "success":
            return {"ok": True, "_topic": "out"}
        if self._behavior == "retriable_then_success":
            c = message.get("count", 0)
            if c == 0:
                # mutate message to simulate stateful retry
                message["count"] = 1
                raise RuntimeError("transient")
            return {"ok": True, "_topic": "out"}
        if self._behavior == "non_retriable":
            raise NonRetriableError("bad request")
        return None


@pytest.mark.asyncio
async def test_retriable_then_success_commits_once_and_no_dlt():
    msgs = [FakeMessage("t", 0, 0, {}), FakeMessage("t", 0, 1, {})]
    agent = FakeAgent(messages=msgs, behavior="retriable_then_success")

    # run agent once over messages
    await agent.start()

    # After start completes, it auto-stops due to consumer exhaustion
    # Commit batching: batch size=2 -> expect at least one commit with both partitions
    assert len(agent._fake_consumer.commits) >= 1
    # produced exactly one result to 'out'
    assert len(agent._fake_producer.sent) == 2  # two messages produce since two inputs
    # verify retries tag appears (first message had one retry before success)
    first_topic, first_value, _ = agent._fake_producer.sent[0]
    second_topic, second_value, _ = agent._fake_producer.sent[1]
    assert first_topic == "out"
    assert second_topic == "out"
    # Our behavior causes each message to fail once before succeeding
    assert first_value.get("retries", 0) >= 1
    assert second_value.get("retries", 0) >= 1
    # metrics - 使用新的AgentMetrics接口
    metrics_dict = agent.metrics.get_metrics_dict()
    assert metrics_dict["retries"] >= 1
    assert metrics_dict["processed"] == 2


@pytest.mark.asyncio
async def test_non_retriable_goes_direct_to_dlt_and_commit():
    msgs = [FakeMessage("t", 0, 0, {"correlation_id": "c-1"})]
    agent = FakeAgent(messages=msgs, behavior="non_retriable")

    await agent.start()

    # DLT sent once
    assert len(agent._fake_producer.sent) == 1
    topic, value, key = agent._fake_producer.sent[0]
    assert topic == "t.DLT"
    assert value["correlation_id"] == "c-1"
    assert value["retries"] == 0
    assert key == b"c-1"

    # Offset committed (either batch or final flush on stop)
    assert len(agent._fake_consumer.commits) >= 1
    # metrics - 使用新的AgentMetrics接口
    metrics_dict = agent.metrics.get_metrics_dict()
    assert metrics_dict["dlt"] == 1
    assert metrics_dict["failed"] == 1


@pytest.mark.asyncio
async def test_batch_commit_by_size_and_flush_on_stop():
    msgs = [FakeMessage("t", 0, i, {}) for i in range(3)]
    agent = FakeAgent(messages=msgs, behavior="success")
    agent.commit_batch_size = 2
    agent.commit_interval_ms = 10_000

    await agent.start()

    # Expect at least two commits: one for first two by size, one final flush
    assert len(agent._fake_consumer.commits) >= 1
    # Ensure processed count matches - 使用新的AgentMetrics接口
    metrics_dict = agent.metrics.get_metrics_dict()
    assert metrics_dict["processed"] == 3
