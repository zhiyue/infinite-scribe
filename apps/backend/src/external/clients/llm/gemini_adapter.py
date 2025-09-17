from __future__ import annotations

from typing import AsyncIterator

from .base import ProviderAdapter
from .types import LLMRequest, LLMResponse, LLMStreamEvent, TokenUsage


class GeminiAdapter(ProviderAdapter):
    """Google Gemini adapter (skeleton).

    Placeholder implementation. The real implementation should use the
    `google-genai` SDK (recommended) or `google-generativeai` (legacy) to call
    Gemini models, including streaming and tool/function calling when needed.
    """

    def __init__(self) -> None:
        super().__init__(name="gemini")

    async def generate(self, req: LLMRequest) -> LLMResponse:
        text = "[Gemini placeholder] Hello from GeminiAdapter."
        return LLMResponse(
            content=text,
            usage=TokenUsage(prompt_tokens=0, completion_tokens=len(text.split())),
            provider=self.name,
            model=req.model,
            retries=0,
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[LLMStreamEvent]:
        yield {"type": "delta", "data": {"content": "[Gemini placeholder stream] "}}
        yield {"type": "complete", "data": {"content": "done"}}

