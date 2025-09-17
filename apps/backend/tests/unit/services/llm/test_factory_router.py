import types

import pytest

from src.services.llm.factory import LLMServiceFactory
from src.external.clients.llm.types import LLMRequest, ChatMessage


class _FakeLLMSettings:
    def __init__(self) -> None:
        self.timeout = 5.0
        self.max_keepalive_connections = 1
        self.max_connections = 2
        self.enable_retry = False
        self.retry_attempts = 1
        self.litellm_api_key = "test-key"
        self.litellm_api_host = "http://localhost:4000"
        self.router_model_map = {r"^claude-": "other-provider"}

    @property
    def litellm_api_url(self) -> str:
        return f"{self.litellm_api_host.rstrip('/')}/"


class _FakeSettings:
    def __init__(self) -> None:
        self.llm = _FakeLLMSettings()
        # legacy fallback (not used when llm.litellm_api_host provided)
        self.litellm_api_host = ""
        self.litellm_api_key = ""

    @property
    def litellm_api_url(self) -> str:
        # use nested llm value
        return self.llm.litellm_api_url


@pytest.mark.asyncio
async def test_router_model_map_override(monkeypatch):
    fake_settings = _FakeSettings()

    # Patch get_settings used inside factory
    monkeypatch.setattr("src.services.llm.factory.get_settings", lambda: fake_settings)

    factory = LLMServiceFactory()
    service = factory.create_service()

    # Verify that router uses override for claude- prefix
    req = LLMRequest(model="claude-3-sonnet", messages=[ChatMessage(role="user", content="hi")])
    provider = service._router.choose_provider(req)
    assert provider == "other-provider"

