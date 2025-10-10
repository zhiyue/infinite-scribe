# LLM API Integration Design Document (2025)

## Executive Summary

This document provides a comprehensive design for integrating multiple LLM API providers (LiteLLM, OpenAI, Claude/Anthropic, OpenRouter, Kimi) into the InfiniteScribe platform. Based on the latest API documentation and best practices as of September 2025, this integration creates a unified, resilient, and cost-effective interface for accessing cutting-edge LLM models.

## Table of Contents

1. [Overview](#overview)
2. [Provider Landscape 2025](#provider-landscape-2025)
3. [Architecture Design](#architecture-design)
4. [Provider Specifications](#provider-specifications)
5. [Implementation Plan](#implementation-plan)
6. [Configuration Management](#configuration-management)
7. [Error Handling & Resilience](#error-handling--resilience)
8. [Security & Compliance](#security--compliance)
9. [Testing Strategy](#testing-strategy)
10. [Migration Strategy](#migration-strategy)

## Overview

### Current Market Dynamics (2025)

- **Anthropic's Growth**: Market share doubled from 12% to 24% (2024-2025)
- **OpenAI Evolution**: Dominance shifted from 50% to 34%, but released GPT-5 series
- **Competition Intensification**: Multiple providers offering free tiers and competitive pricing
- **Technical Advancement**: Reasoning models (o3, Claude 4, GPT-5) with extended thinking capabilities

### Goals

- **Unified Interface**: Single abstraction layer compatible with OpenAI/Anthropic API formats
- **Provider Diversity**: Support for 400+ models through multiple providers
- **Cost Optimization**: Intelligent routing based on performance/cost metrics
- **High Availability**: Automatic failover with circuit breakers and retries
- **Streaming Support**: Native SSE streaming for all providers
- **Reasoning Integration**: Support for new thinking/reasoning modes
- **Tool Calling**: Native support for function/tool calling across providers
- **Observability**: Comprehensive telemetry, cost tracking, and performance metrics

### Non-Goals

- Building custom LLM models
- Direct model fine-tuning through platform
- Managing provider billing systems
- Implementing custom tokenizers

## Provider Landscape 2025

### Leading Models Comparison

| Provider | Model | Context | Input $/1M | Output $/1M | Key Features |
|----------|-------|---------|------------|-------------|--------------|
| **OpenAI** | GPT-5 | 272K/128K | Varies by reasoning | Varies by reasoning | Thinking modes (minimal/low/medium/high), SWE-bench: 74.9% |
| | GPT-5 mini | 272K/128K | Lower | Lower | Cost-optimized GPT-5 |
| | o3 | 200K | Higher | Higher | Complex reasoning, June 2024 cutoff |
| | o3-mini | 200K/100K | Medium | Medium | Fast reasoning for coding/math |
| **Anthropic** | Claude Opus 4.1 | 200K | $15 | $75 | SWE-bench: 74.5%, hybrid reasoning |
| | Claude Sonnet 4 | 200K (1M beta) | $3 | $15 | SWE-bench: 72.7%, best coding |
| | Claude 3.5 Haiku | 200K | $0.80 | $4 | Fast, affordable |
| **Kimi** | K2 | 256K | $0.58 | $2.29 | 1T parameters, tool calling |
| | K2-128K | 128K | $0.15 (cached) | $2.50 | Long context specialist |

### Provider Capabilities Matrix (2025)

| Feature | LiteLLM | OpenAI | Claude | OpenRouter | Kimi |
|---------|---------|--------|--------|------------|------|
| Models Supported | 100+ | GPT-5/o3 series | Claude 4/3.5 | 400+ | K2 series |
| Streaming | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tool/Function Calling | ✅ | ✅ | ✅ | ✅ | ✅ |
| Reasoning/Thinking | Via providers | ✅ (4 levels) | ✅ (hybrid) | Via providers | ✅ |
| Vision/Multimodal | Via providers | ✅ | ✅ | Via providers | ❌ |
| Embeddings | ✅ | ✅ | ❌ | Via providers | ✅ |
| Cost Tracking | ✅ | Manual | Manual | ✅ | Manual |
| MCP Support | ✅ | ❌ | ❌ | ❌ | ❌ |

## Architecture Design

### Enhanced Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
├─────────────────────────────────────────────────────────────┤
│              LLM Service Orchestrator v2                     │
├──────────────┬────────────┬────────────┬───────────────────┤
│   Provider   │  Request   │   Cost     │    Reasoning      │
│   Registry   │  Router    │ Optimizer  │    Manager        │
├──────────────┴────────────┴────────────┴───────────────────┤
│                    Provider Abstraction Layer                │
├──────┬──────┬──────┬──────┬──────┬─────────────────────────┤
│LiteLLM│OpenAI│Claude│OpenRouter│Kimi│   [Future Providers]  │
│ v1.74│ GPT-5│ Opus4│  400+    │ K2 │                       │
├──────┴──────┴──────┴──────┴──────┴─────────────────────────┤
│         Resilience Layer (Retry, Circuit Breaker)           │
├─────────────────────────────────────────────────────────────┤
│        Performance Layer (Caching, Connection Pool)         │
├─────────────────────────────────────────────────────────────┤
│              Configuration & Credentials Layer               │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Enhanced LLM Service Interface

```python
# apps/backend/src/infrastructure/llm/llm_service_v2.py

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncIterator, Union, Literal
from pydantic import BaseModel, Field
from enum import Enum

class ReasoningLevel(str, Enum):
    """Reasoning effort levels for GPT-5 and similar models"""
    MINIMAL = "minimal"  # GPT-5 only, fastest streaming
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    THINKING = "thinking"  # For reasoning/thinking messages

class ToolCall(BaseModel):
    id: str
    type: Literal["function"]
    function: Dict[str, Any]

class Message(BaseModel):
    role: MessageRole
    content: Union[str, List[Dict]]  # Supports multi-modal
    name: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    thinking_visible: Optional[bool] = False  # Claude 4 hybrid reasoning

class LLMRequest(BaseModel):
    """Enhanced LLM request for 2025 models"""
    model: str
    messages: List[Message]

    # Standard parameters
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = None
    stream: bool = False
    top_p: Optional[float] = Field(None, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(None, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(None, ge=-2, le=2)
    stop: Optional[Union[str, List[str]]] = None

    # Tool/Function calling
    tools: Optional[List[Dict]] = None
    tool_choice: Optional[Union[str, Dict]] = None
    parallel_tool_calls: Optional[bool] = True

    # Response formatting
    response_format: Optional[Dict] = None  # JSON mode

    # Reasoning/Thinking parameters (2025)
    reasoning_effort: Optional[ReasoningLevel] = None  # GPT-5, o3
    thinking_budget: Optional[int] = None  # Claude 4
    enable_search: Optional[bool] = False  # Tool use during thinking

    # Provider routing hints
    optimize_for: Optional[Literal["cost", "speed", "quality", "reasoning"]] = "balance"
    fallback_enabled: bool = True

    # MCP integration (LiteLLM)
    mcp_tools: Optional[List[str]] = None

    metadata: Dict = {}

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    reasoning_tokens: Optional[int] = 0  # For thinking models
    cache_creation_input_tokens: Optional[int] = 0
    cache_read_input_tokens: Optional[int] = 0
    search_units: Optional[int] = 0  # For models with search

class LLMResponse(BaseModel):
    """Enhanced response model for 2025"""
    content: str
    model: str
    provider: str
    usage: Usage
    cost: float
    finish_reason: str

    # Optional fields
    tool_calls: Optional[List[ToolCall]] = None
    thinking_content: Optional[str] = None  # Reasoning trace
    search_results: Optional[List[Dict]] = None  # If search was used

    # Performance metrics
    latency_ms: Optional[int] = None
    time_to_first_token_ms: Optional[int] = None

    metadata: Dict = {}
```

#### 2. Provider Implementations (2025 Updates)

##### LiteLLM Provider v1.74

```python
# apps/backend/src/infrastructure/llm/providers/litellm_provider_v2.py

import litellm
from litellm import Router, acompletion
import os

class LiteLLMProvider(ILLMProvider):
    """
    LiteLLM v1.74.3 provider with MCP support
    100+ models with unified interface
    """

    def __init__(self):
        # Configure LiteLLM v1.74 settings
        litellm.set_verbose = False
        litellm.drop_params = True
        litellm.request_timeout = 60

        # Enhanced router with new models
        self.router = Router(
            model_list=[
                # OpenAI GPT-5 series
                {
                    "model_name": "gpt-5",
                    "litellm_params": {
                        "model": "openai/gpt-5",
                        "api_key": os.getenv("OPENAI_API_KEY")
                    }
                },
                {
                    "model_name": "gpt-5-mini",
                    "litellm_params": {
                        "model": "openai/gpt-5-mini",
                        "api_key": os.getenv("OPENAI_API_KEY")
                    }
                },
                # OpenAI o3 series
                {
                    "model_name": "o3",
                    "litellm_params": {
                        "model": "openai/o3",
                        "api_key": os.getenv("OPENAI_API_KEY")
                    }
                },
                # Claude 4 series
                {
                    "model_name": "claude-opus-4",
                    "litellm_params": {
                        "model": "anthropic/claude-4-opus",
                        "api_key": os.getenv("ANTHROPIC_API_KEY")
                    }
                },
                # Kimi K2
                {
                    "model_name": "kimi-k2",
                    "litellm_params": {
                        "model": "moonshot/kimi-k2",
                        "api_key": os.getenv("KIMI_API_KEY"),
                        "api_base": "https://api.moonshot.cn/v1"
                    }
                },
                # Alibaba Qwen via Dashscope
                {
                    "model_name": "qwen-max",
                    "litellm_params": {
                        "model": "dashscope/qwen-max",
                        "api_key": os.getenv("DASHSCOPE_API_KEY")
                    }
                }
            ],
            fallback_models=["gpt-5-mini", "claude-sonnet-4", "kimi-k2"],
            enable_pre_call_checks=True,
            retry_strategy="exponential_backoff",
            model_group_alias={
                "reasoning": ["o3", "claude-opus-4", "gpt-5"],
                "coding": ["claude-sonnet-4", "gpt-5", "kimi-k2"],
                "cost_optimized": ["gpt-5-mini", "claude-haiku", "qwen-max"]
            }
        )

        # MCP (Model Context Protocol) settings
        self.mcp_enabled = os.getenv("LITELLM_MCP_ENABLED", "true").lower() == "true"
        if self.mcp_enabled:
            self._setup_mcp()

    def _setup_mcp(self):
        """Setup MCP tool cost tracking and access groups"""
        # MCP tool pricing configuration
        self.mcp_tool_costs = {
            "web_search": 0.001,  # per call
            "code_interpreter": 0.002,
            "file_operations": 0.0005
        }

    async def complete(self, request: LLMRequest) -> LLMResponse:
        # Handle reasoning effort for supported models
        extra_params = {}
        if request.reasoning_effort and request.model in ["gpt-5", "o3"]:
            extra_params["reasoning_effort"] = request.reasoning_effort.value

        response = await self.router.acompletion(
            model=request.model,
            messages=[msg.dict() for msg in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=request.tools,
            stream=False,
            **extra_params,
            **request.metadata
        )

        # Calculate comprehensive cost including MCP tools
        total_cost = litellm.completion_cost(response)
        if request.mcp_tools:
            for tool in request.mcp_tools:
                total_cost += self.mcp_tool_costs.get(tool, 0)

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            provider="litellm",
            usage=Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                reasoning_tokens=getattr(response.usage, 'reasoning_tokens', 0)
            ),
            cost=total_cost,
            finish_reason=response.choices[0].finish_reason
        )
```

##### OpenAI Provider (GPT-5 & o3)

```python
# apps/backend/src/infrastructure/llm/providers/openai_provider_v2.py

from openai import AsyncOpenAI
import os

class OpenAIProvider(ILLMProvider):
    """
    Native OpenAI API integration for GPT-5 and o3 series
    Supports reasoning levels and extended context
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            organization=os.getenv("OPENAI_ORGANIZATION"),
            max_retries=3
        )

        # 2025 Model specifications
        self.models = {
            # GPT-5 series
            "gpt-5": {"context": 272000, "output": 128000, "reasoning": True},
            "gpt-5-mini": {"context": 272000, "output": 128000, "reasoning": True},
            "gpt-5-nano": {"context": 128000, "output": 32000, "reasoning": True},

            # o3 reasoning series
            "o3": {"context": 200000, "output": 100000, "reasoning": True},
            "o3-mini": {"context": 200000, "output": 100000, "reasoning": True},
            "o1": {"context": 200000, "output": 100000, "reasoning": True},

            # Legacy
            "gpt-4o": {"context": 128000, "output": 16384, "reasoning": False},
            "gpt-4-turbo": {"context": 128000, "output": 4096, "reasoning": False}
        }

    async def complete(self, request: LLMRequest) -> LLMResponse:
        # Build request parameters
        params = {
            "model": request.model,
            "messages": self._format_messages(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False
        }

        # Add reasoning effort for GPT-5 and o3 models
        if request.reasoning_effort and self.models.get(request.model, {}).get("reasoning"):
            params["reasoning_effort"] = request.reasoning_effort.value

            # GPT-5 specific: minimal reasoning for instant responses
            if request.reasoning_effort == ReasoningLevel.MINIMAL:
                params["stream_reasoning"] = False  # Disable reasoning tokens in stream

        # Tool calling support
        if request.tools:
            params["tools"] = request.tools
            params["tool_choice"] = request.tool_choice
            params["parallel_tool_calls"] = request.parallel_tool_calls

        # Response format for JSON mode
        if request.response_format:
            params["response_format"] = request.response_format

        start_time = time.time()
        response = await self.client.chat.completions.create(**params)
        latency_ms = int((time.time() - start_time) * 1000)

        # Parse response with reasoning tokens
        usage_dict = response.usage.model_dump()
        reasoning_tokens = usage_dict.get("reasoning_tokens", 0)

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            provider="openai",
            usage=Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                reasoning_tokens=reasoning_tokens
            ),
            cost=self._calculate_cost(response.model, response.usage),
            finish_reason=response.choices[0].finish_reason,
            tool_calls=response.choices[0].message.tool_calls,
            latency_ms=latency_ms
        )

    def _calculate_cost(self, model: str, usage) -> float:
        """Calculate cost including reasoning tokens"""
        # GPT-5 pricing varies by reasoning level
        pricing = {
            "gpt-5": {"input": 0.015, "output": 0.045, "reasoning": 0.030},
            "gpt-5-mini": {"input": 0.005, "output": 0.015, "reasoning": 0.010},
            "o3": {"input": 0.020, "output": 0.060, "reasoning": 0.040},
            "o3-mini": {"input": 0.003, "output": 0.012, "reasoning": 0.008}
        }

        if model not in pricing:
            return 0

        rates = pricing[model]
        cost = (usage.prompt_tokens * rates["input"] / 1000000)
        cost += (usage.completion_tokens * rates["output"] / 1000000)

        if hasattr(usage, "reasoning_tokens") and usage.reasoning_tokens > 0:
            cost += (usage.reasoning_tokens * rates["reasoning"] / 1000000)

        return cost
```

##### Claude Provider (Opus 4.1)

```python
# apps/backend/src/infrastructure/llm/providers/claude_provider_v2.py

from anthropic import AsyncAnthropic
import os

class ClaudeProvider(ILLMProvider):
    """
    Anthropic Claude 4 series integration
    Supports hybrid reasoning and extended context
    """

    def __init__(self):
        self.client = AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        # 2025 Model mappings
        self.models = {
            "claude-opus-4.1": "claude-4-opus-20250501",
            "claude-opus-4": "claude-4-opus-20250301",
            "claude-sonnet-4": "claude-4-sonnet-20250301",
            "claude-3.5-haiku": "claude-3-5-haiku-20250301",
            "claude-3-haiku": "claude-3-haiku-20240307"
        }

        # Context windows
        self.context_windows = {
            "claude-opus-4.1": 200000,
            "claude-opus-4": 200000,
            "claude-sonnet-4": 1000000,  # With beta header
            "claude-3.5-haiku": 200000
        }

    async def complete(self, request: LLMRequest) -> LLMResponse:
        model_id = self.models.get(request.model, request.model)

        # Build request parameters
        params = {
            "model": model_id,
            "messages": self._convert_messages(request.messages),
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
            "stream": False
        }

        # Add beta headers for extended features
        headers = {}
        if request.model == "claude-sonnet-4" and request.max_tokens and request.max_tokens > 200000:
            headers["anthropic-beta"] = "context-1m-2025-08-07"

        # Hybrid reasoning for Claude 4
        if request.thinking_budget and request.model.startswith("claude-opus-4"):
            params["thinking_budget"] = request.thinking_budget
            params["thinking_visible"] = any(msg.thinking_visible for msg in request.messages)

        # Tool support for Claude 4
        if request.tools:
            params["tools"] = self._convert_tools(request.tools)
            params["tool_choice"] = request.tool_choice or "auto"

        response = await self.client.messages.create(**params)

        # Extract thinking content if present
        thinking_content = None
        if hasattr(response, 'thinking') and response.thinking:
            thinking_content = response.thinking.content

        return LLMResponse(
            content=response.content[0].text if response.content else "",
            model=response.model,
            provider="anthropic",
            usage=Usage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                cache_creation_input_tokens=getattr(response.usage, 'cache_creation_input_tokens', 0),
                cache_read_input_tokens=getattr(response.usage, 'cache_read_input_tokens', 0)
            ),
            cost=self._calculate_cost(request.model, response.usage),
            finish_reason=response.stop_reason,
            thinking_content=thinking_content
        )

    def _calculate_cost(self, model: str, usage) -> float:
        """Calculate cost for Claude models (2025 pricing)"""
        pricing = {
            "claude-opus-4.1": {"input": 0.015, "output": 0.075},
            "claude-opus-4": {"input": 0.015, "output": 0.075},
            "claude-sonnet-4": {"input": 0.003, "output": 0.015},
            "claude-3.5-haiku": {"input": 0.0008, "output": 0.004},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125}
        }

        if model not in pricing:
            return 0

        rates = pricing[model]
        cost = (usage.input_tokens * rates["input"] / 1000000)
        cost += (usage.output_tokens * rates["output"] / 1000000)

        # Apply cache discount if applicable
        if usage.cache_read_input_tokens > 0:
            cache_discount = usage.cache_read_input_tokens * rates["input"] * 0.9 / 1000000
            cost -= cache_discount

        return cost
```

##### OpenRouter Provider (400+ Models)

```python
# apps/backend/src/infrastructure/llm/providers/openrouter_provider_v2.py

import httpx
import os
import json

class OpenRouterProvider(ILLMProvider):
    """
    OpenRouter unified API gateway
    Access to 400+ models through single endpoint
    """

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"

        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://infinitescribe.ai"),
                "X-Title": os.getenv("OPENROUTER_SITE_NAME", "InfiniteScribe")
            },
            timeout=httpx.Timeout(120.0)  # Longer timeout for reasoning models
        )

        # Routing suffixes
        self.routing_modes = {
            "speed": ":nitro",      # Optimize for throughput
            "cost": ":floor",       # Optimize for price
            "search": ":online",    # Include web search
            "free": ":free"         # Use free tier
        }

        # Cache available models
        self.available_models = None
        self._model_pricing = {}

    async def complete(self, request: LLMRequest) -> LLMResponse:
        # Apply routing mode based on optimization
        model_name = request.model
        if request.optimize_for in self.routing_modes:
            model_name = f"{model_name}{self.routing_modes[request.optimize_for]}"

        params = {
            "model": model_name,
            "messages": [msg.dict() for msg in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
            "transforms": ["middle-out"],  # OpenRouter optimization
            "route": "fallback"  # Enable automatic fallback
        }

        # Add provider-specific parameters
        if request.tools:
            params["tools"] = request.tools
            params["tool_choice"] = request.tool_choice

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=params
        )

        data = response.json()

        # OpenRouter provides actual provider used
        actual_provider = data.get("provider", "unknown")

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=f"{data['model']} (via {actual_provider})",
            provider="openrouter",
            usage=Usage(**data["usage"]),
            cost=data.get("usage", {}).get("total_cost", 0) * 1.055,  # Add 5.5% fee
            finish_reason=data["choices"][0]["finish_reason"]
        )

    async def get_models(self) -> List[Dict]:
        """Fetch available models with current pricing"""
        if not self.available_models:
            response = await self.client.get(f"{self.base_url}/models")
            self.available_models = response.json()["data"]

            # Cache pricing
            for model in self.available_models:
                self._model_pricing[model["id"]] = {
                    "input": model.get("pricing", {}).get("prompt", 0),
                    "output": model.get("pricing", {}).get("completion", 0)
                }

        return self.available_models
```

##### Kimi K2 Provider

```python
# apps/backend/src/infrastructure/llm/providers/kimi_provider_v2.py

import httpx
import os

class KimiProvider(ILLMProvider):
    """
    Kimi K2 (Moonshot AI) provider
    1T parameter MoE model with 256K context
    """

    def __init__(self):
        self.api_key = os.getenv("KIMI_API_KEY")
        self.base_url = "https://api.moonshot.cn/v1"

        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=httpx.Timeout(120.0)
        )

        # 2025 Kimi models
        self.models = {
            "kimi-k2": "moonshot-v1-auto",      # Auto-select best K2 variant
            "kimi-k2-256k": "moonshot-v1-256k",  # Max context
            "kimi-k2-128k": "moonshot-v1-128k",
            "kimi-k2-32k": "moonshot-v1-32k",
            "kimi-k2-8k": "moonshot-v1-8k"
        }

        self.context_windows = {
            "kimi-k2": 256000,
            "kimi-k2-256k": 256000,
            "kimi-k2-128k": 128000,
            "kimi-k2-32k": 32000,
            "kimi-k2-8k": 8000
        }

    async def complete(self, request: LLMRequest) -> LLMResponse:
        model_name = self.models.get(request.model, request.model)

        params = {
            "model": model_name,
            "messages": [msg.dict() for msg in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False
        }

        # Kimi K2 supports advanced tool calling
        if request.tools:
            params["tools"] = request.tools
            params["tool_choice"] = request.tool_choice or "auto"
            params["parallel_tool_calls"] = request.parallel_tool_calls

        # Enable search if requested
        if request.enable_search:
            params["enable_search"] = True

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=params
        )

        data = response.json()

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data["model"],
            provider="kimi",
            usage=Usage(**data["usage"]),
            cost=self._calculate_cost(model_name, data["usage"]),
            finish_reason=data["choices"][0]["finish_reason"],
            tool_calls=data["choices"][0]["message"].get("tool_calls"),
            search_results=data.get("search_results")
        )

    def _calculate_cost(self, model: str, usage: Dict) -> float:
        """Calculate cost based on 2025 Kimi pricing"""
        # Direct pricing from Moonshot AI
        pricing = {
            "moonshot-v1-256k": {"input": 0.00058, "output": 0.00229},
            "moonshot-v1-128k": {"input": 0.00058, "output": 0.00229},
            "moonshot-v1-32k": {"input": 0.00015, "output": 0.00250, "cached": 0.00015},
            "moonshot-v1-8k": {"input": 0.00015, "output": 0.00250}
        }

        if model not in pricing:
            return 0

        rates = pricing[model]

        # Check for cached pricing
        if "cached" in rates and usage.get("cache_hits", 0) > 0:
            input_cost = usage["prompt_tokens"] * rates["cached"] / 1000000
        else:
            input_cost = usage["prompt_tokens"] * rates["input"] / 1000000

        output_cost = usage["completion_tokens"] * rates["output"] / 1000000

        return input_cost + output_cost
```

## Configuration Management

### Environment Configuration (2025)

```env
# .env.development

# LiteLLM v1.74 Configuration
LITELLM_API_KEY=optional_key
LITELLM_API_BASE=optional_base
LITELLM_ENABLE_CACHE=true
LITELLM_CACHE_TYPE=redis
LITELLM_MCP_ENABLED=true
LITELLM_MCP_TOOL_TRACKING=true

# OpenAI Configuration (GPT-5 & o3)
OPENAI_API_KEY=sk-xxx
OPENAI_ORGANIZATION=org-xxx
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_DEFAULT_REASONING=medium

# Claude/Anthropic Configuration (Opus 4.1)
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_API_VERSION=2025-05-01
ANTHROPIC_MAX_RETRIES=3
ANTHROPIC_ENABLE_BETA=true

# OpenRouter Configuration (400+ models)
OPENROUTER_API_KEY=sk-or-xxx
OPENROUTER_SITE_URL=https://infinitescribe.ai
OPENROUTER_SITE_NAME=InfiniteScribe
OPENROUTER_DEFAULT_ROUTING=fallback

# Kimi K2 Configuration
KIMI_API_KEY=sk-xxx
KIMI_API_BASE=https://api.moonshot.cn/v1
KIMI_DEFAULT_MODEL=kimi-k2

# Dashscope (Alibaba Qwen)
DASHSCOPE_API_KEY=sk-xxx

# Provider Settings
LLM_DEFAULT_PROVIDER=litellm
LLM_FALLBACK_PROVIDERS=openai,claude,openrouter,kimi
LLM_TIMEOUT_SECONDS=120
LLM_MAX_RETRIES=3
LLM_ENABLE_STREAMING=true

# Cost Management
LLM_MAX_COST_PER_REQUEST=5.0
LLM_MAX_COST_PER_USER_PER_DAY=50.0
LLM_TRACK_COSTS=true
LLM_ALERT_COST_THRESHOLD=100.0

# Performance
LLM_CACHE_ENABLED=true
LLM_CACHE_TTL_SECONDS=3600
LLM_RATE_LIMIT_PER_MINUTE=100
LLM_CONNECTION_POOL_SIZE=100

# Feature Flags
FF_ENABLE_REASONING_MODELS=true
FF_ENABLE_TOOL_CALLING=true
FF_ENABLE_MCP_INTEGRATION=true
FF_ENABLE_HYBRID_REASONING=true
```

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

1. **Base Abstractions**
   - Implement enhanced ILLMProvider interface with reasoning support
   - Create request/response models with 2025 fields
   - Setup provider registry with model groups

2. **Configuration System**
   - Environment variable management
   - Provider configuration schemas
   - Feature flag system

### Phase 2: Provider Implementations (Week 2-3)

1. **Priority 1: LiteLLM v1.74**
   - MCP integration
   - Tool cost tracking
   - Model group routing

2. **Priority 2: OpenAI (GPT-5/o3)**
   - Reasoning level support
   - Extended context handling
   - Streaming with reasoning tokens

3. **Priority 3: Claude 4**
   - Hybrid reasoning implementation
   - 1M context support
   - Tool use during thinking

4. **Priority 4: OpenRouter**
   - 400+ model catalog
   - Routing modes (:nitro, :floor, :online)
   - Automatic fallback

5. **Priority 5: Kimi K2**
   - 256K context support
   - Advanced tool calling
   - Search integration

### Phase 3: Advanced Features (Week 4)

1. **Reasoning Optimization**
   - Dynamic reasoning level selection
   - Cost/quality trade-offs
   - Thinking budget management

2. **Performance Enhancement**
   - O(1) model routing
   - Connection pooling with HTTP/2
   - Semantic caching layer

3. **Observability & Monitoring**
   - Prometheus metrics
   - Distributed tracing
   - Cost alerting

## Testing Strategy

### Unit Tests

```python
# tests/unit/infrastructure/llm/test_providers_2025.py

@pytest.mark.asyncio
async def test_gpt5_reasoning_levels():
    """Test GPT-5 reasoning level support"""
    provider = OpenAIProvider()

    for level in [ReasoningLevel.MINIMAL, ReasoningLevel.HIGH]:
        request = LLMRequest(
            model="gpt-5",
            messages=[Message(role=MessageRole.USER, content="Solve this problem")],
            reasoning_effort=level
        )

        response = await provider.complete(request)

        if level == ReasoningLevel.MINIMAL:
            assert response.usage.reasoning_tokens == 0
        else:
            assert response.usage.reasoning_tokens > 0

@pytest.mark.asyncio
async def test_claude4_hybrid_reasoning():
    """Test Claude 4 hybrid reasoning"""
    provider = ClaudeProvider()

    request = LLMRequest(
        model="claude-opus-4.1",
        messages=[Message(role=MessageRole.USER, content="Complex task")],
        thinking_budget=1000
    )

    response = await provider.complete(request)
    assert response.thinking_content is not None
```

### Integration Tests

```python
# tests/integration/infrastructure/llm/test_llm_service_2025.py

@pytest.mark.integration
async def test_model_routing_optimization():
    """Test intelligent model routing"""
    service = LLMService()

    # Test cost optimization
    request = LLMRequest(
        model="auto",
        messages=[Message(role=MessageRole.USER, content="Simple question")],
        optimize_for="cost"
    )

    response = await service.complete(request)
    assert response.model in ["gpt-5-mini", "claude-3-haiku", "kimi-k2-8k"]

@pytest.mark.integration
async def test_mcp_tool_integration():
    """Test LiteLLM MCP tool support"""
    service = LLMService()

    request = LLMRequest(
        model="gpt-5",
        messages=[Message(role=MessageRole.USER, content="Search for information")],
        mcp_tools=["web_search"],
        tools=[{"type": "function", "function": {...}}]
    )

    response = await service.complete(request)
    assert response.cost > 0  # Includes MCP tool cost
```

## Cost Optimization Matrix (2025)

### Model Selection by Use Case

| Use Case | Recommended Model | Cost/1M tokens | Reasoning |
|----------|------------------|----------------|-----------|
| Simple Q&A | Claude 3 Haiku | $0.25/$1.25 | Fast, cheap |
| Code Generation | Claude Sonnet 4 | $3/$15 | SWE-bench leader |
| Complex Reasoning | GPT-5 (high) | Variable | Best performance |
| Long Context | Kimi K2-256K | $0.58/$2.29 | 256K context |
| Multimodal | GPT-5 | Variable | Native vision |
| Budget Tasks | OpenRouter:free | $0 | Free tier models |
| Chinese Content | Kimi K2 | $0.58/$2.29 | Optimized for Chinese |

## Security & Compliance

### Enhanced Security Measures (2025)

1. **API Key Vault Integration**
   - HashiCorp Vault support
   - AWS Secrets Manager
   - Azure Key Vault

2. **Request Signing**
   - HMAC-SHA256 request signing
   - Request replay prevention
   - IP whitelisting

3. **Compliance**
   - GDPR data residency
   - SOC 2 Type II
   - HIPAA compliance mode

## Migration Strategy

### From 2024 to 2025 Models

```python
# Automatic model migration
MODEL_MIGRATION_MAP = {
    # OpenAI
    "gpt-4-turbo": "gpt-5-mini",
    "gpt-4": "gpt-5-mini",
    "gpt-3.5-turbo": "gpt-5-nano",

    # Claude
    "claude-3-opus": "claude-opus-4",
    "claude-3-sonnet": "claude-sonnet-4",

    # Kimi
    "moonshot-v1-128k": "kimi-k2-128k"
}

def migrate_model(old_model: str) -> str:
    """Automatically migrate to newer models"""
    return MODEL_MIGRATION_MAP.get(old_model, old_model)
```

## Performance Benchmarks (2025)

### Response Times

| Model | Time to First Token | Throughput (tokens/s) |
|-------|-------------------|---------------------|
| GPT-5 (minimal) | 200ms | 150-200 |
| GPT-5 (high) | 2-5s | 50-75 |
| Claude Opus 4.1 | 500ms | 100-150 |
| Kimi K2 | 300ms | 120-180 |
| o3 | 1-3s | 60-80 |

## Conclusion

This 2025 design leverages the latest advancements in LLM technology:

1. **Reasoning Models**: GPT-5 and Claude 4 with thinking capabilities
2. **Extended Context**: Up to 1M tokens (Claude Sonnet 4) and 256K (Kimi K2)
3. **Cost Efficiency**: Multiple free tiers and aggressive pricing from Kimi
4. **Enhanced Performance**: O(1) routing, HTTP/2, and improved caching
5. **Advanced Features**: MCP support, hybrid reasoning, tool calling

The architecture is designed to scale with the rapid evolution of LLM capabilities while maintaining backward compatibility and cost efficiency.