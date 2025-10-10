from __future__ import annotations

from collections.abc import AsyncIterator

from src.external.clients.llm.base import ProviderAdapter
from src.external.clients.llm.types import LLMRequest, LLMResponse, LLMStreamEvent, TokenUsage


class QwenAdapter(ProviderAdapter):
    """Qwen (Alibaba DashScope) adapter (skeleton).

    Placeholder implementation. Production code can use the `dashscope` SDK to
    call Qwen models (e.g., qwen2.5) with streaming and tool/function calls.
    """

    def __init__(self) -> None:
        super().__init__(name="qwen")

    async def generate(self, req: LLMRequest) -> LLMResponse:
        text = "[Qwen placeholder] Hello from QwenAdapter."
        return LLMResponse(
            content=text,
            usage=TokenUsage(prompt_tokens=0, completion_tokens=len(text.split())),
            provider=self.name,
            model=req.model,
            retries=0,
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[LLMStreamEvent]:
        yield {"type": "delta", "data": {"content": "[Qwen placeholder stream] "}}
        yield {"type": "complete", "data": {"content": "done"}}
