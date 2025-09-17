from __future__ import annotations

from typing import AsyncIterator

from ..base import ProviderAdapter
from ..types import LLMRequest, LLMResponse, LLMStreamEvent, TokenUsage


class DeepSeekAdapter(ProviderAdapter):
    """DeepSeek adapter (skeleton).

    Placeholder implementation. DeepSeek exposes an OpenAI-compatible API
    (base_url like https://api.deepseek.com), so a production adapter could
    reuse the OpenAI client configured with a custom base_url.
    """

    def __init__(self) -> None:
        super().__init__(name="deepseek")

    async def generate(self, req: LLMRequest) -> LLMResponse:
        text = "[DeepSeek placeholder] Hello from DeepSeekAdapter."
        return LLMResponse(
            content=text,
            usage=TokenUsage(prompt_tokens=0, completion_tokens=len(text.split())),
            provider=self.name,
            model=req.model,
            retries=0,
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[LLMStreamEvent]:
        yield {"type": "delta", "data": {"content": "[DeepSeek placeholder stream] "}}
        yield {"type": "complete", "data": {"content": "done"}}
