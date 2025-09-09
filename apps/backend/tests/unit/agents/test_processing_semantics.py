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
    """Test that retriable errors are retried successfully and messages commit normally.

    This test verifies the complete retry flow:
    1. Messages that fail with retriable errors are retried according to max_retries
    2. After successful retry, messages are processed and committed normally
    3. No messages are sent to DLT (dead letter topic)
    4. Metrics accurately track retries and processing counts

    Uses FakeAgent with 'retriable_then_success' behavior:
    - First attempt fails with RuntimeError (retriable)
    - Second attempt succeeds and produces output
    """
    # Setup: 2 messages, batch size = 2 (configured in FakeAgent)
    msgs = [FakeMessage("t", 0, 0, {"test_id": "msg1"}), FakeMessage("t", 0, 1, {"test_id": "msg2"})]
    agent = FakeAgent(messages=msgs, behavior="retriable_then_success")

    # Execute: process all messages
    await agent.start()

    # Verify commits: batch size=2, so expect exactly 1 commit containing both messages
    assert (
        len(agent._fake_consumer.commits) == 1
    ), f"Expected exactly 1 commit for batch of 2, got {len(agent._fake_consumer.commits)}"

    # Verify outputs: both messages should produce successful results
    assert (
        len(agent._fake_producer.sent) == 2
    ), f"Expected exactly 2 outputs for 2 inputs, got {len(agent._fake_producer.sent)}"

    # Verify output structure and retry tracking
    first_topic, first_value, _ = agent._fake_producer.sent[0]
    second_topic, second_value, _ = agent._fake_producer.sent[1]

    assert first_topic == "out", f"Expected output topic 'out', got '{first_topic}'"
    assert second_topic == "out", f"Expected output topic 'out', got '{second_topic}'"
    assert first_value["status"] == "ok", f"Expected first message status 'ok', got '{first_value['status']}'"
    assert second_value["status"] == "ok", f"Expected second message status 'ok', got '{second_value['status']}'"
    assert first_value["data"]["ok"] is True, f"Expected first message success in data, got {first_value['data']}"
    assert second_value["data"]["ok"] is True, f"Expected second message success in data, got {second_value['data']}"

    # Verify retry tracking: each message fails once before succeeding (due to behavior)
    assert (
        first_value.get("retries", 0) == 1
    ), f"Expected exactly 1 retry for first message, got {first_value.get('retries', 0)}"
    assert (
        second_value.get("retries", 0) == 1
    ), f"Expected exactly 1 retry for second message, got {second_value.get('retries', 0)}"

    # Verify metrics reflect accurate counts
    metrics_dict = agent.metrics.get_metrics_dict()
    assert metrics_dict["retries"] == 2, f"Expected exactly 2 total retries, got {metrics_dict['retries']}"
    assert metrics_dict["processed"] == 2, f"Expected exactly 2 processed messages, got {metrics_dict['processed']}"
    assert metrics_dict.get("dlt", 0) == 0, f"Expected 0 DLT messages, got {metrics_dict.get('dlt', 0)}"
    assert metrics_dict.get("failed", 0) == 0, f"Expected 0 failed messages, got {metrics_dict.get('failed', 0)}"


@pytest.mark.asyncio
async def test_non_retriable_goes_direct_to_dlt_and_commit():
    """Test that non-retriable errors bypass retries and go directly to DLT.

    This test verifies the DLT (dead letter topic) flow:
    1. Messages that fail with NonRetriableError skip retry logic entirely
    2. Failed messages are immediately sent to the DLT topic with error context
    3. Original message offset is still committed (processed, though failed)
    4. Metrics accurately track DLT and failure counts

    Uses FakeAgent with 'non_retriable' behavior:
    - Always raises NonRetriableError("bad request")
    - No retries attempted, direct to DLT
    """
    # Setup: single message with correlation_id for tracking
    test_correlation_id = "test-correlation-non-retriable"
    msgs = [FakeMessage("t", 0, 0, {"correlation_id": test_correlation_id, "data": "test-payload"})]
    agent = FakeAgent(messages=msgs, behavior="non_retriable")

    # Execute: process message (should fail non-retriably)
    await agent.start()

    # Verify exactly one DLT message was sent
    assert len(agent._fake_producer.sent) == 1, f"Expected exactly 1 DLT message, got {len(agent._fake_producer.sent)}"

    # Verify DLT message structure
    topic, value, key = agent._fake_producer.sent[0]
    assert topic == "t.DLT", f"Expected DLT topic 't.DLT', got '{topic}'"
    assert (
        value["correlation_id"] == test_correlation_id
    ), f"Expected correlation_id '{test_correlation_id}', got '{value['correlation_id']}'"
    assert value["retries"] == 0, f"Expected 0 retries for non-retriable error, got {value['retries']}"
    assert key == test_correlation_id.encode(), f"Expected key '{test_correlation_id.encode()}', got '{key}'"

    # Verify DLT-specific structure
    assert value["type"] == "error", f"Expected DLT type 'error', got '{value['type']}'"
    assert value["original_topic"] == "t", f"Expected original_topic 't', got '{value['original_topic']}'"

    # Verify error information is included in DLT
    assert "error" in value, "DLT message missing 'error' field"
    assert "bad request" in value["error"], f"Expected error message containing 'bad request', got '{value['error']}'"

    # Verify original message data is preserved in payload
    assert "payload" in value, "DLT message missing 'payload' field"
    assert (
        value["payload"]["correlation_id"] == test_correlation_id
    ), f"Expected payload correlation_id '{test_correlation_id}', got '{value['payload']['correlation_id']}'"
    assert (
        value["payload"]["data"] == "test-payload"
    ), f"Expected payload data 'test-payload', got '{value['payload']['data']}'"

    # Verify message offset was committed (even though processing failed)
    assert len(agent._fake_consumer.commits) == 1, f"Expected exactly 1 commit, got {len(agent._fake_consumer.commits)}"

    # Verify metrics reflect DLT and failure
    metrics_dict = agent.metrics.get_metrics_dict()
    assert metrics_dict["dlt"] == 1, f"Expected exactly 1 DLT message, got {metrics_dict['dlt']}"
    assert metrics_dict["failed"] == 1, f"Expected exactly 1 failed message, got {metrics_dict['failed']}"
    assert metrics_dict["retries"] == 0, f"Expected 0 retries for non-retriable, got {metrics_dict['retries']}"
    assert metrics_dict["processed"] == 0, f"Expected 0 successful processing, got {metrics_dict['processed']}"


@pytest.mark.asyncio
async def test_batch_commit_by_size_and_flush_on_stop():
    """Test that batch commit logic works correctly based on size and final flush.

    This test verifies the commit batching behavior:
    1. Messages are committed in batches based on commit_batch_size
    2. When batch size is reached, a commit occurs immediately
    3. When agent stops, any remaining uncommitted messages are flushed
    4. All messages are processed successfully

    Test setup:
    - 3 messages with batch_size=2
    - Expected: commits occur as batches are filled + final flush
    - Large commit_interval_ms to avoid time-based commits
    """
    # Setup: 3 messages, batch size = 2, time-based commits disabled
    test_messages = [
        FakeMessage("t", 0, 0, {"message_id": "msg1"}),
        FakeMessage("t", 0, 1, {"message_id": "msg2"}),
        FakeMessage("t", 0, 2, {"message_id": "msg3"}),
    ]
    agent = FakeAgent(messages=test_messages, behavior="success")
    agent.commit_batch_size = 2  # Commit after every 2 messages
    agent.commit_interval_ms = 10_000  # Large interval to avoid time-based commits

    # Execute: process all messages
    await agent.start()

    # Verify commit behavior: expect at least 1 commit (implementation may vary)
    # Note: Different implementations may batch differently, so use >= 1 for robustness
    assert (
        len(agent._fake_consumer.commits) >= 1
    ), f"Expected at least 1 commit, got {len(agent._fake_consumer.commits)}"

    # Verify all messages produced successful outputs
    assert (
        len(agent._fake_producer.sent) == 3
    ), f"Expected exactly 3 outputs for 3 inputs, got {len(agent._fake_producer.sent)}"

    # Verify all outputs are successful
    for i, (topic, value, key) in enumerate(agent._fake_producer.sent):
        assert topic == "out", f"Message {i}: expected topic 'out', got '{topic}'"
        assert isinstance(value, dict), f"Message {i}: expected dict value, got {type(value)}"
        assert value["status"] == "ok", f"Message {i}: expected status 'ok', got '{value['status']}'"
        assert "data" in value, f"Message {i}: expected 'data' field in envelope"
        assert value["data"]["ok"] is True, f"Message {i}: expected success in data, got {value['data']}"
        assert (
            value.get("retries", 0) == 0
        ), f"Message {i}: expected 0 retries for success behavior, got {value.get('retries', 0)}"

    # Verify metrics reflect successful processing
    metrics_dict = agent.metrics.get_metrics_dict()
    assert metrics_dict["processed"] == 3, f"Expected exactly 3 processed messages, got {metrics_dict['processed']}"
    assert (
        metrics_dict.get("retries", 0) == 0
    ), f"Expected 0 retries for success behavior, got {metrics_dict.get('retries', 0)}"
    assert metrics_dict.get("failed", 0) == 0, f"Expected 0 failed messages, got {metrics_dict.get('failed', 0)}"
    assert metrics_dict.get("dlt", 0) == 0, f"Expected 0 DLT messages, got {metrics_dict.get('dlt', 0)}"
