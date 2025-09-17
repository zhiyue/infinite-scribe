from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from .types import LLMRequest, LLMResponse, LLMStreamEvent


class ProviderAdapter(ABC):
    """Abstract adapter for a specific LLM provider.

    Concrete implementations should translate `LLMRequest` to provider API,
    and map provider responses/stream events back to our unified types.
    """

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    async def generate(self, req: LLMRequest) -> LLMResponse:
        """Non-streaming text generation call."""
        raise NotImplementedError

    @abstractmethod
    async def stream(self, req: LLMRequest) -> AsyncGenerator[LLMStreamEvent, None]:
        """Streaming text generation call, yields `LLMStreamEvent`."""
        raise NotImplementedError
