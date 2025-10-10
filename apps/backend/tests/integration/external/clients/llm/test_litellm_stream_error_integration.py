"""Error handling tests for LiteLLMAdapter streaming path."""

import httpx
import pytest
from src.core.config import settings
from src.external.clients.errors import ServiceRateLimitError, ServiceUnavailableError
from src.external.clients.llm import ChatMessage, LLMRequest
from src.services.llm import LLMServiceFactory


@pytest.mark.asyncio
async def test_litellm_stream_http_429(httpx_mock):
    settings.llm.litellm_api_host = "http://litellm.local"
    settings.llm.litellm_api_key = "sk-proxy"

    httpx_mock.add_response(
        method="POST",
        url=f"{settings.llm.litellm_api_url}v1/chat/completions",
        json={"error": "rate limit"},
        status_code=429,
    )

    service = LLMServiceFactory().create_service()
    req = LLMRequest(model="gpt-4o-mini", messages=[ChatMessage(role="user", content="hi")], stream=True)

    with pytest.raises(ServiceRateLimitError):
        async for _ in service.stream(req):
            pass


@pytest.mark.asyncio
async def test_litellm_stream_timeout(httpx_mock):
    settings.llm.litellm_api_host = "http://litellm.local"
    settings.llm.litellm_api_key = "sk-proxy"

    httpx_mock.add_exception(
        method="POST",
        url=f"{settings.llm.litellm_api_url}v1/chat/completions",
        exception=httpx.TimeoutException("timeout"),
    )

    service = LLMServiceFactory().create_service()
    req = LLMRequest(model="gpt-4o-mini", messages=[ChatMessage(role="user", content="hi")], stream=True)

    with pytest.raises(ServiceUnavailableError):
        async for _ in service.stream(req):
            pass
