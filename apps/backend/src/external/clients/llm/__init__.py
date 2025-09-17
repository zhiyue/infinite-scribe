"""Unified LLM client interfaces and adapters.

This package defines the minimal, testable skeleton for integrating external
LLM providers behind a common interface. It follows the Strategy pattern and
prefers dependency injection for easy testing and swapping providers.
"""

from .types import (
    ChatMessage,
    LLMRequest,
    LLMResponse,
    LLMStreamEvent,
    ToolCall,
    ToolFunctionSpec,
    ToolSpec,
    TokenUsage,
)
from .base import ProviderAdapter
from .router import ProviderRouter
from .litellm_adapter import LiteLLMAdapter
from .gemini_adapter import GeminiAdapter
from .deepseek_adapter import DeepSeekAdapter
from .zhipuai_adapter import ZhipuAIAdapter
from .qwen_adapter import QwenAdapter

__all__ = [
    "ChatMessage",
    "LLMRequest",
    "LLMResponse",
    "LLMStreamEvent",
    "ToolCall",
    "ToolFunctionSpec",
    "ToolSpec",
    "TokenUsage",
    "ProviderAdapter",
    "ProviderRouter",
    "LiteLLMAdapter",
    "GeminiAdapter",
    "DeepSeekAdapter",
    "ZhipuAIAdapter",
    "QwenAdapter",
]
