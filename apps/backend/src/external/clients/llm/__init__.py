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
from .adapters.litellm_adapter import LiteLLMAdapter
from .adapters.gemini_adapter import GeminiAdapter
from .adapters.deepseek_adapter import DeepSeekAdapter
from .adapters.zhipuai_adapter import ZhipuAIAdapter
from .adapters.qwen_adapter import QwenAdapter

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
