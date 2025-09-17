from __future__ import annotations

from src.core.config import get_settings
from src.external.clients.llm import (
    LiteLLMAdapter,
    ProviderAdapter,
    ProviderRouter,
)
from src.services.llm import LLMService


class LLMServiceFactory:
    """Factory to build a default LLMService from Settings.

    - Uses LiteLLM Proxy configuration if available.
    - Creates a simple regex-based ProviderRouter with default provider 'litellm'.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def _build_router(self) -> ProviderRouter:
        # Route常量：当前阶段全部走 LiteLLM，由 Proxy 侧完成具体模型路由
        model_map: dict[str, str] = {
            r"^gpt-": "litellm",
            r"^claude-": "litellm",
            r"^gemini": "litellm",
            r"^glm-": "litellm",
            r"^qwen-": "litellm",
            r"^deepseek-": "litellm",
        }
        return ProviderRouter(default_provider="litellm", model_map=model_map)

    def _build_adapters(self) -> dict[str, ProviderAdapter]:
        adapters: dict[str, ProviderAdapter] = {}

        # Configure LiteLLM adapter when host is defined
        base_url = self.settings.litellm_api_url.rstrip("/") if self.settings.litellm_api_url else ""
        api_key = self.settings.litellm_api_key
        if base_url and api_key:
            adapters["litellm"] = LiteLLMAdapter(
                base_url=base_url,
                api_key=api_key,
                timeout=self.settings.llm.timeout,
                max_keepalive_connections=self.settings.llm.max_keepalive_connections,
                max_connections=self.settings.llm.max_connections,
                enable_retry=self.settings.llm.enable_retry,
                retry_attempts=self.settings.llm.retry_attempts,
            )

        return adapters

    def create_service(self) -> LLMService:
        adapters = self._build_adapters()
        router = self._build_router()
        return LLMService(router, adapters)
