"""Integration-style tests for LiteLLMAdapter via LLMServiceFactory using httpx mock.

These tests exercise the real HTTP layer (BaseHttpClient) with pytest-httpx
intercepting outbound requests to a LiteLLM Proxy-compatible endpoint.
They respect configured values via Settings.llm (read from environment or TOML),
and are safe to run on CI (use httpx_mock, no real network).
"""

import json

import pytest
from src.core.config import settings
from src.external.clients.llm import ChatMessage, LLMRequest
from src.services.llm import LLMServiceFactory


@pytest.mark.asyncio
async def test_litellm_generate_basic(httpx_mock):
    # Provide local defaults for base/key; CI-safe as outbound calls are mocked
    base = "http://litellm.local"
    api_key = "sk-proxy"

    # Ensure Settings reflects configured values
    settings.llm.litellm_api_host = base
    settings.llm.litellm_api_key = api_key

    # Mock LiteLLM Proxy response for chat completions
    response_json = {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello from proxy", "tool_calls": []},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }

    httpx_mock.add_response(
        url=f"{settings.llm.litellm_api_url}v1/chat/completions",
        json=response_json,
        status_code=200,
    )

    service = LLMServiceFactory().create_service()
    req = LLMRequest(model="gpt-4o-mini", messages=[ChatMessage(role="user", content="hi")])

    result = await service.generate(req)

    # Validate result mapping
    assert result.content == "Hello from proxy"
    assert result.model == "gpt-4o-mini"
    assert result.provider == "litellm"
    assert result.usage is not None
    assert result.usage.prompt_tokens == 5
    assert result.usage.completion_tokens == 3

    # Verify outbound request
    request = httpx_mock.get_request()
    assert request.headers.get("Authorization") == f"Bearer {api_key}"
    assert request.url.path.endswith("/v1/chat/completions")
    payload = json.loads(request.content)
    assert payload["model"] == "gpt-4o-mini"
    assert payload["stream"] is False
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "hi"
