from __future__ import annotations

from collections.abc import AsyncGenerator

from src.external.clients.llm import (
    LLMRequest,
    LLMResponse,
    LLMStreamEvent,
    ProviderAdapter,
    ProviderRouter,
)


class LLMService:
    """Facade for generating text via configured LLM providers.

    This service delegates provider selection to `ProviderRouter` and forwards
    the request to the appropriate `ProviderAdapter` implementation.
    """

    def __init__(self, router: ProviderRouter, adapters: dict[str, ProviderAdapter]) -> None:
        self._router = router
        self._adapters = dict(adapters)

    def _get_adapter(self, provider: str) -> ProviderAdapter:
        if provider not in self._adapters:
            raise KeyError(f"No adapter registered for provider: {provider}")
        return self._adapters[provider]

    async def generate(self, req: LLMRequest, provider_override: str | None = None) -> LLMResponse:
        provider = self._router.choose_provider(req, override=provider_override)
        adapter = self._get_adapter(provider)
        return await adapter.generate(req)

    async def stream(
        self, req: LLMRequest, provider_override: str | None = None
    ) -> AsyncGenerator[LLMStreamEvent, None]:
        provider = self._router.choose_provider(req, override=provider_override)
        adapter = self._get_adapter(provider)
        async for event in adapter.stream(req):  # type: ignore[misc]
            yield event
