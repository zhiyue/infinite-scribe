from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field

ChatRole = Literal["system", "user", "assistant", "tool"]


class ChatMessage(BaseModel):
    role: ChatRole
    content: str | dict[str, Any]


class ToolFunctionSpec(BaseModel):
    name: str
    description: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolSpec(BaseModel):
    type: Literal["function"] = "function"
    function: ToolFunctionSpec


class ToolCall(BaseModel):
    id: str | None = None
    name: str
    arguments: str | dict[str, Any]


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    tools: list[ToolSpec] | None = None
    tool_choice: Literal["auto", "none"] | str | None = None
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: list[str] | None = None
    metadata: dict[str, Any] | None = None


class LLMResponse(BaseModel):
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: TokenUsage | None = None
    provider: str = ""
    model: str = ""
    retries: int = 0


class LLMStreamEvent(TypedDict):
    type: Literal["delta", "tool_call", "tool_result", "complete", "error"]
    data: dict[str, Any]


# Keep a Protocol-like alias for client stream typing usage in adapters
AsyncStream = AsyncIterator[LLMStreamEvent]
