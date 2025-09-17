import asyncio
import types

import pytest

from src.agents.writer.agent import WriterAgent
from src.external.clients.llm.types import LLMResponse, TokenUsage
from src.external.clients.errors import ServiceUnavailableError


class DummyProducer:
    def __init__(self):
        self.sent = []

    async def send_and_wait(self, topic, value, key=None):
        self.sent.append({"topic": topic, "value": value, "key": key})


class DummyMsg:
    def __init__(self, topic: str = "writer.input", partition: int = 0, offset: int = 1):
        self.topic = topic
        self.partition = partition
        self.offset = offset
        self.headers = []


class FakeLLMService:
    def __init__(self, plan: list[object]):
        # plan: sequence of exceptions or LLMResponse objects to return per call
        self.plan = plan
        self.calls = 0

    async def generate(self, req):
        idx = self.calls
        self.calls += 1
        item = self.plan[idx] if idx < len(self.plan) else self.plan[-1]
        if isinstance(item, Exception):
            raise item
        return item

    async def stream(self, req):
        yield {"type": "complete", "data": {}}


@pytest.mark.asyncio
async def test_writer_agent_process_success():
    llm = FakeLLMService([
        LLMResponse(content="Hello Content", usage=TokenUsage(), provider="litellm", model="x"),
    ])
    agent = WriterAgent(llm_service=llm)

    msg = {"type": "write_chapter", "chapter_id": 1, "prompt": "写一段内容"}
    result = await agent.process_message(msg, context={})

    assert result is not None
    assert result["type"] == "chapter_written"
    assert "Hello Content" in result["content"]


@pytest.mark.asyncio
async def test_writer_agent_retry_then_success(monkeypatch):
    # First call fails with retriable error, second succeeds
    llm = FakeLLMService([
        ServiceUnavailableError("litellm"),
        LLMResponse(content="Retried Success", usage=TokenUsage(), provider="litellm", model="x"),
    ])
    agent = WriterAgent(llm_service=llm)

    # Use MessageProcessor to exercise retry/DLT path
    safe_message = {"type": "write_chapter", "chapter_id": 2, "prompt": "请写作"}
    context = {}
    correlation_id = "cid-1"
    message_id = "mid-1"

    dummy_msg = DummyMsg()
    dummy_producer = DummyProducer()

    async def _producer_func():
        return dummy_producer

    result = await agent.message_processor.process_message_with_retry(
        msg=dummy_msg,
        safe_message=safe_message,
        context=context,
        correlation_id=correlation_id,
        message_id=message_id,
        process_func=agent.process_message,
        producer_func=_producer_func,
        agent_metrics=agent.metrics,
    )

    assert result["handled"] is True
    assert result["success"] is True
    # ensure at least one retry occurred
    assert int(agent.metrics.get("retries", 0)) >= 1


@pytest.mark.asyncio
async def test_writer_agent_non_retriable_goes_dlt():
    from src.agents.errors import NonRetriableError

    llm = FakeLLMService([
        NonRetriableError("bad input"),
    ])
    agent = WriterAgent(llm_service=llm)

    safe_message = {"type": "write_scene", "scene_id": 9, "prompt": "请写作"}
    context = {}
    correlation_id = "cid-2"
    message_id = "mid-2"

    dummy_msg = DummyMsg()
    dummy_producer = DummyProducer()

    async def _producer_func():
        return dummy_producer

    result = await agent.message_processor.process_message_with_retry(
        msg=dummy_msg,
        safe_message=safe_message,
        context=context,
        correlation_id=correlation_id,
        message_id=message_id,
        process_func=agent.process_message,
        producer_func=_producer_func,
        agent_metrics=agent.metrics,
    )

    assert result["handled"] is True
    assert result["success"] is False
    # Should send one message to DLT
    assert len(dummy_producer.sent) == 1
    assert dummy_producer.sent[0]["topic"].endswith(agent.error_handler.dlt_suffix)
