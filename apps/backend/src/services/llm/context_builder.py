from __future__ import annotations

import json
from typing import Any

from src.services.kb.service import KnowledgeBaseService


class PreContextBuilder:
    """Lightweight pre-context builder for LLM prompts.

    Fetches knowledge from internal KB services before invoking LLM, to reduce
    tool calls and improve determinism/cost.
    """

    @staticmethod
    async def build_for_writer(user_prompt: dict[str, Any]) -> dict[str, Any]:
        task = user_prompt.get("task", "")
        pre: dict[str, Any] = {"task": task}

        # Heuristic keywords
        kw = None
        if task == "write_chapter" and user_prompt.get("outline"):
            kw = str(user_prompt.get("outline"))[:32]
        if not kw and user_prompt.get("scene_data"):
            kw = str(user_prompt.get("scene_data"))[:32]
        if not kw and user_prompt.get("extra"):
            kw = str(user_prompt.get("extra"))[:32]

        # Worldview
        try:
            pre["worldview"] = await KnowledgeBaseService.search_worldview(kw or "小说世界", limit=3)
        except Exception:
            pre["worldview"] = {"query": kw, "items": []}

        # Characters: accept names/ids from prompt if present
        pre_chars: list[dict[str, Any]] = []
        for char in (user_prompt.get("characters") or []):
            name = char.get("name")
            cid = char.get("id") or char.get("character_id")
            try:
                profile = await KnowledgeBaseService.get_character_profile(name=name, character_id=cid)
            except Exception:
                profile = {"found": False, "reason": "lookup_error"}
            pre_chars.append(profile)
        pre["characters"] = pre_chars

        # Glossary terms by style/tone
        gloss_kw = user_prompt.get("style") or user_prompt.get("tone") or kw or ""
        try:
            pre["glossary"] = await KnowledgeBaseService.get_glossary(str(gloss_kw), limit=5)
        except Exception:
            pre["glossary"] = {"query": gloss_kw, "terms": []}

        return pre

    @staticmethod
    def as_system_context(pre: dict[str, Any]) -> str:
        """Render pre-context as a compact JSON block for system message."""
        blob = json.dumps(pre, ensure_ascii=False)
        return (
            "You are a helpful writing assistant. Use the provided context first; "
            "if insufficient, you may ask for clarification.\n"
            f"Context JSON: {blob}"
        )

