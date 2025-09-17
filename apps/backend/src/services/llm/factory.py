from __future__ import annotations

from typing import Mapping

from src.core.config import get_settings
from src.external.clients.llm import (
    LLMRequest,
    ProviderAdapter,
    ProviderRouter,
    LLMResponse,
    LLMStreamEvent,
    LiteLLMAdapter,
    GeminiAdapter,
)
from src.services.llm import LLMService


class LLMServiceFactory:
    """Factory to build a default LLMService from Settings.

    - Uses LiteLLM Proxy configuration if available.
    - Creates a simple regex-based ProviderRouter with default provider 'litellm'.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def _build_router(self, available: Mapping[str, ProviderAdapter]) -> ProviderRouter:
        # Basic model prefix mapping; route to available adapters, otherwise to litellm
        model_map: dict[str, str] = {
            r"^gpt-": "litellm",
            r"^claude-": "litellm",
            r"^glm-": "litellm",
            r"^qwen-": "litellm",
            r"^deepseek-": "litellm",
        }
        if "gemini" in available:
            model_map[r"^gemini"] = "gemini"
        else:
            model_map[r"^gemini"] = "litellm"
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
                timeout=self.settings.embedding.timeout,
                max_keepalive_connections=self.settings.embedding.max_keepalive_connections,
                max_connections=self.settings.embedding.max_connections,
                enable_retry=self.settings.embedding.enable_retry,
                retry_attempts=self.settings.embedding.retry_attempts,
            )

        # Gemini via AI Studio (Developer API) — prefer official SDK in adapter
        if getattr(self.settings, "gemini_api_key", ""):
            adapters["gemini"] = GeminiAdapter()

        return adapters

    def create_service(self) -> LLMService:
        adapters = self._build_adapters()
        router = self._build_router(adapters)
        return LLMService(router, adapters)
