"""Streaming integration test for LiteLLMAdapter using SSE-like chunks.

The adapter reads lines from `aiter_lines()` and expects `data: ...` payloads.
We simulate a small stream with two deltas and a final [DONE]. Tests respect
configured values via Settings.llm and are safe to run on CI (use httpx_mock,
no real network).
"""

import pytest
from src.core.config import settings
from src.external.clients.llm import ChatMessage, LLMRequest
from src.services.llm import LLMServiceFactory


@pytest.mark.asyncio
async def test_litellm_stream_basic(httpx_mock):
    # Provide local defaults for base/key; CI-safe as outbound calls are mocked
    settings.llm.litellm_api_host = "http://litellm.local"
    settings.llm.litellm_api_key = "sk-proxy"

    # Build SSE-like text with two deltas and a final [DONE]
    chunk1 = 'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
    chunk2 = 'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
    done = "data: [DONE]\n\n"
    stream_text = chunk1 + chunk2 + done

    httpx_mock.add_response(
        method="POST",
        url=f"{settings.llm.litellm_api_url}v1/chat/completions",
        headers={"Content-Type": "text/event-stream"},
        text=stream_text,
        status_code=200,
    )

    service = LLMServiceFactory().create_service()
    req = LLMRequest(model="gpt-4o-mini", messages=[ChatMessage(role="user", content="hi")], stream=True)

    deltas = []
    async for event in service.stream(req):
        if event["type"] == "delta":
            deltas.append(event["data"]["content"])
        elif event["type"] == "complete":
            break

    assert "".join(deltas) == "Hello world"
