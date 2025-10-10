from __future__ import annotations

from src.external.clients.llm.types import ToolFunctionSpec, ToolSpec


def get_writer_tool_specs() -> list[ToolSpec]:
    """Return tool specs available to WriterAgent for function calling.

    Tools:
    - kb_search(keyword: string, limit?: integer)
    - get_character_profile(name?: string, character_id?: string)
    - get_glossary(keyword: string, limit?: integer)
    - outline_expand(outline: string, style?: string)
    """

    kb_search = ToolSpec(
        function=ToolFunctionSpec(
            name="kb_search",
            description="Search knowledge base worldview entries by keyword.",
            parameters={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Search keywords"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 3},
                },
                "required": ["keyword"],
            },
        )
    )

    get_character_profile = ToolSpec(
        function=ToolFunctionSpec(
            name="get_character_profile",
            description="Get character profile by name or id. One of name or character_id is required.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "character_id": {"type": "string"},
                },
                "anyOf": [
                    {"required": ["name"]},
                    {"required": ["character_id"]},
                ],
            },
        )
    )

    get_glossary = ToolSpec(
        function=ToolFunctionSpec(
            name="get_glossary",
            description="Get glossary terms by keyword.",
            parameters={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                },
                "required": ["keyword"],
            },
        )
    )

    outline_expand = ToolSpec(
        function=ToolFunctionSpec(
            name="outline_expand",
            description="Expand outline points according to a given style.",
            parameters={
                "type": "object",
                "properties": {
                    "outline": {"type": "string"},
                    "style": {"type": "string", "default": "文风"},
                },
                "required": ["outline"],
            },
        )
    )

    return [kb_search, get_character_profile, get_glossary, outline_expand]
