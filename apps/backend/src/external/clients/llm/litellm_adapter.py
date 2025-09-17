from __future__ import annotations

from typing import AsyncIterator

from .base import ProviderAdapter
from .types import LLMRequest, LLMResponse, LLMStreamEvent, TokenUsage


class LiteLLMAdapter(ProviderAdapter):
    """LiteLLM adapter (skeleton).

    NOTE: This is a placeholder implementation that returns a stubbed response.
    The real implementation should call LiteLLM Proxy or the `litellm` library
    and map provider responses to our unified types.
    """

    def __init__(self) -> None:
        super().__init__(name="litellm")

    async def generate(self, req: LLMRequest) -> LLMResponse:
        # Placeholder implementation — returns a minimal response without
        # performing any network calls. Replace with real LiteLLM invocation.
        text = "[LiteLLM placeholder] Hello from LiteLLMAdapter."
        return LLMResponse(
            content=text,
            usage=TokenUsage(prompt_tokens=0, completion_tokens=len(text.split())),
            provider=self.name,
            model=req.model,
            retries=0,
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[LLMStreamEvent]:
        # Placeholder streaming: emit a single delta and a complete event.
        yield {"type": "delta", "data": {"content": "[LiteLLM placeholder stream] "}}
        yield {"type": "complete", "data": {"content": "done"}}

