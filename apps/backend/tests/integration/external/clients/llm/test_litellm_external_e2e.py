"""E2E-style integration test that calls a real LiteLLM Proxy.

WARNING: This test performs a real network call and may incur cost depending
on your configured model/router. It is skipped by default and only runs when
RUN_LITELLM_E2E=true and required env vars are present.
"""

import os

import pytest
from src.core.config import settings
from src.external.clients.llm import ChatMessage, LLMRequest
from src.services.llm import LLMServiceFactory

run_e2e = os.getenv("RUN_LITELLM_E2E", "false").lower() == "true"
skip_reasons = []
if os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("CI") == "true":
    skip_reasons.append("running on CI")
if not run_e2e:
    skip_reasons.append("RUN_LITELLM_E2E not enabled")

lite_host = os.getenv("LLM__LITELLM_API_HOST") or os.getenv("LITELLM_API_HOST") or ""
lite_key = os.getenv("LLM__LITELLM_API_KEY") or os.getenv("LITELLM_API_KEY") or ""
if not lite_host or not lite_key:
    skip_reasons.append("LiteLLM host/key not configured")

skip_condition = pytest.mark.skipif(bool(skip_reasons), reason=f"Skip e2e: {', '.join(skip_reasons)}")


@skip_condition
@pytest.mark.asyncio
async def test_litellm_generate_e2e():
    # Apply configured values to Settings
    settings.llm.litellm_api_host = lite_host
    settings.llm.litellm_api_key = lite_key
    # Use a small timeout for test
    settings.llm.timeout = float(os.getenv("LLM__TIMEOUT", 20.0))

    model = os.getenv("LLM_E2E_MODEL", os.getenv("LLM__DEFAULT_MODEL", "gemini-2.5-flash"))

    service = LLMServiceFactory().create_service()
    req = LLMRequest(model=model, messages=[ChatMessage(role="user", content="返回完整的李白的静夜思的诗句")])

    result = await service.generate(req)

    # Output the actual API response content for debugging
    print("\n=== LiteLLM API Response ===")
    print(f"Content: {result.content}")
    print(f"Provider: {result.provider}")
    print(f"Model: {result.model}")
    print(f"Token usage: {getattr(result, 'token_usage', 'N/A')}")
    print("=== End Response ===\n")

    assert isinstance(result.content, str)
    assert result.content != ""
    assert result.provider == "litellm"
