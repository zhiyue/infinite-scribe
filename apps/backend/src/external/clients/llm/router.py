from __future__ import annotations

import re
from typing import Mapping

from .types import LLMRequest


class ProviderRouter:
    """Simple regex-based provider router (skeleton).

    - `default_provider`: fallback provider name (e.g., 'litellm')
    - `model_map`: mapping of regex pattern -> provider name
    """

    def __init__(self, default_provider: str = "litellm", model_map: Mapping[str, str] | None = None) -> None:
        self.default_provider = default_provider
        self.model_map = dict(model_map or {})

    def choose_provider(self, req: LLMRequest, override: str | None = None) -> str:
        if override:
            return override
        model = req.model
        for pattern, provider in self.model_map.items():
            if re.match(pattern, model):
                return provider
        return self.default_provider

