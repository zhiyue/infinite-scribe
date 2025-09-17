from __future__ import annotations

from typing import AsyncIterator

from .base import ProviderAdapter
from .types import LLMRequest, LLMResponse, LLMStreamEvent, TokenUsage


class GeminiAdapter(ProviderAdapter):
    """Google Gemini adapter (skeleton).

    Integration priority: Google AI Studio (Gemini Developer API).

    Placeholder implementation. The production implementation should use the
    `google-genai` SDK (preferred) to call Gemini via AI Studio using
    `GEMINI_API_KEY` / `GOOGLE_API_KEY`, including streaming and tool/function
    calling as needed. Vertex AI is supported as an alternative path but not
    the primary route.
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
