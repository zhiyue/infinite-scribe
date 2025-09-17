from __future__ import annotations

from typing import AsyncIterator

from ..base import ProviderAdapter
from ..types import LLMRequest, LLMResponse, LLMStreamEvent, TokenUsage


class ZhipuAIAdapter(ProviderAdapter):
    """ZhipuAI (GLM) adapter (skeleton).

    Placeholder implementation. Production code can use the `zhipuai` SDK to
    call GLM models (e.g., glm-4) with function calling and streaming.
    """

    def __init__(self) -> None:
        super().__init__(name="glm")

    async def generate(self, req: LLMRequest) -> LLMResponse:
        text = "[GLM placeholder] Hello from ZhipuAIAdapter."
        return LLMResponse(
            content=text,
            usage=TokenUsage(prompt_tokens=0, completion_tokens=len(text.split())),
            provider=self.name,
            model=req.model,
            retries=0,
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[LLMStreamEvent]:
        yield {"type": "delta", "data": {"content": "[GLM placeholder stream] "}}
        yield {"type": "complete", "data": {"content": "done"}}
