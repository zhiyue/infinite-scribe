from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from ...base_http import BaseHttpClient
from ...errors import handle_connection_error, handle_http_error
from ..base import ProviderAdapter
from ..types import LLMRequest, LLMResponse, LLMStreamEvent, TokenUsage


class LiteLLMAdapter(ProviderAdapter, BaseHttpClient):
    """LiteLLM adapter using OpenAI-compatible endpoints.

    - Base URL should point to the LiteLLM Proxy host (without trailing '/v1').
    - Uses `/v1/chat/completions` for non-streaming; `/v1/chat/completions` with
      `stream=True` for streaming.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 30.0,
        max_keepalive_connections: int = 5,
        max_connections: int = 10,
        enable_retry: bool = True,
        retry_attempts: int = 3,
        retry_min_wait: float = 1.0,
        retry_max_wait: float = 10.0,
    ) -> None:
        ProviderAdapter.__init__(self, name="litellm")
        BaseHttpClient.__init__(
            self,
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            max_keepalive_connections=max_keepalive_connections,
            max_connections=max_connections,
            enable_retry=enable_retry,
            retry_attempts=retry_attempts,
            retry_min_wait=retry_min_wait,
            retry_max_wait=retry_max_wait,
        )
        self._api_key = api_key

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        return headers

    @staticmethod
    def _to_openai_messages(messages: list[dict[str, Any]] | list) -> list[dict[str, Any]]:
        # Already dict-like? Return as-is; otherwise, convert from ChatMessage models
        out: list[dict[str, Any]] = []
        for m in messages:
            if isinstance(m, dict):
                out.append(m)
            else:
                role = getattr(m, "role", None)
                content = getattr(m, "content", None)
                out.append({"role": role, "content": content})
        return out

    @staticmethod
    def _to_openai_tools(tools: list | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        result: list[dict[str, Any]] = []
        for t in tools:
            if isinstance(t, dict):
                result.append(t)
            else:
                fn = getattr(t, "function", None)
                result.append(
                    {
                        "type": "function",
                        "function": {
                            "name": getattr(fn, "name", None),
                            "description": getattr(fn, "description", None),
                            "parameters": getattr(fn, "parameters", {}) or {},
                        },
                    }
                )
        return result

    async def generate(self, req: LLMRequest) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": req.model,
            "messages": self._to_openai_messages(req.messages),
            "stream": False,
        }
        if req.temperature is not None:
            payload["temperature"] = req.temperature
        if req.top_p is not None:
            payload["top_p"] = req.top_p
        if req.max_tokens is not None:
            payload["max_tokens"] = req.max_tokens
        if req.stop is not None:
            payload["stop"] = req.stop
        tools = self._to_openai_tools(req.tools)
        if tools:
            payload["tools"] = tools
        if req.tool_choice is not None:
            payload["tool_choice"] = req.tool_choice

        try:
            resp = await self.post("/v1/chat/completions", json_data=payload, headers=self._build_headers())
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise handle_http_error(self.name, e) from e
        except Exception as e:
            raise handle_connection_error(self.name, e) from e

        content = ""
        tool_calls: list = []
        usage = None
        try:
            choices = data.get("choices") or []
            if choices:
                msg = choices[0].get("message", {})
                content = msg.get("content") or ""
                tool_calls = msg.get("tool_calls") or []
            u = data.get("usage") or {}
            usage = TokenUsage(
                prompt_tokens=int(u.get("prompt_tokens", 0) or 0),
                completion_tokens=int(u.get("completion_tokens", 0) or 0),
            )
        except Exception:
            # Be resilient to schema differences; keep defaults
            usage = usage or TokenUsage()

        return LLMResponse(
            content=content or "",
            tool_calls=tool_calls,
            usage=usage,
            provider=self.name,
            model=req.model,
            retries=0,
        )

    async def stream(self, req: LLMRequest) -> AsyncGenerator[LLMStreamEvent, None]:
        payload: dict[str, Any] = {
            "model": req.model,
            "messages": self._to_openai_messages(req.messages),
            "stream": True,
        }
        tools = self._to_openai_tools(req.tools)
        if tools:
            payload["tools"] = tools
        if req.tool_choice is not None:
            payload["tool_choice"] = req.tool_choice
        if req.temperature is not None:
            payload["temperature"] = req.temperature
        if req.top_p is not None:
            payload["top_p"] = req.top_p
        if req.max_tokens is not None:
            payload["max_tokens"] = req.max_tokens
        if req.stop is not None:
            payload["stop"] = req.stop

        # Ensure client exists for streaming
        if not await self.ensure_connected():
            raise RuntimeError("HTTP client not connected")
        assert self._client is not None

        url = f"{self.base_url}/v1/chat/completions"
        headers = self._build_headers()
        try:
            async with self._client.stream("POST", url, json=payload, headers=headers, timeout=self._timeout) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[len("data: ") :].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            obj = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        # OpenAI delta format
                        for ch in obj.get("choices", []):
                            delta = ch.get("delta", {})
                            if delta.get("content"):
                                yield {"type": "delta", "data": {"content": delta["content"]}}
                            # tool_calls streaming not fully implemented here
                yield {"type": "complete", "data": {"content": ""}}
        except httpx.HTTPStatusError as e:
            raise handle_http_error(self.name, e) from e
        except Exception as e:
            raise handle_connection_error(self.name, e) from e
