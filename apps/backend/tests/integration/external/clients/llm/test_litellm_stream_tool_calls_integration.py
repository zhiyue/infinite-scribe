"""Streaming tool_calls integration test for LiteLLMAdapter.

Simulates OpenAI-compatible streaming of tool_calls delta and asserts that
incremental tool_call events are emitted and aggregated in the final complete.
"""

import json

import pytest
from src.core.config import settings
from src.external.clients.llm import ChatMessage, LLMRequest
from src.services.llm import LLMServiceFactory


@pytest.mark.asyncio
async def test_litellm_stream_tool_calls(httpx_mock):
    settings.llm.litellm_api_host = "http://litellm.local"
    settings.llm.litellm_api_key = "sk-proxy"

    # Stream with two tool_call chunks (index 0), accumulating arguments
    obj1 = {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": '{"city": "Par'},
                        }
                    ]
                }
            }
        ]
    }
    obj2 = {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "type": "function",
                            "function": {"arguments": 'is"}'},
                        }
                    ]
                },
                "finish_reason": "tool_calls",
            }
        ]
    }
    stream_text = f"data: {json.dumps(obj1)}\n\n" + f"data: {json.dumps(obj2)}\n\n" + "data: [DONE]\n\n"

    httpx_mock.add_response(
        method="POST",
        url=f"{settings.llm.litellm_api_url}v1/chat/completions",
        headers={"Content-Type": "text/event-stream"},
        text=stream_text,
        status_code=200,
    )

    service = LLMServiceFactory().create_service()
    req = LLMRequest(model="gpt-4o-mini", messages=[ChatMessage(role="user", content="hi")], stream=True)

    tool_events = []
    complete = None
    async for event in service.stream(req):
        if event["type"] == "tool_call":
            tool_events.append(event["data"])
        elif event["type"] == "complete":
            complete = event["data"]
            break

    assert len(tool_events) == 2
    assert tool_events[0]["name"] == "get_weather"
    assert "Par" in tool_events[0]["arguments"]
    assert 'is"}' in tool_events[1]["arguments"]

    assert complete is not None
    assert complete.get("finish_reason") in ("tool_calls", "stop", "")
    agg = complete.get("tool_calls", [])
    assert agg and agg[0]["name"] == "get_weather"
    assert "Paris" in agg[0]["arguments"]
