"""
Domain event configuration and helpers.

Centralizes mapping from dialogue scope to:
- Domain event prefix (dot notation, e.g., "Genesis.Session")
- Aggregate type (e.g., "GenesisSession")
- Domain bus topic (e.g., "genesis.session.events")

This avoids hard-coding Genesis-specific strings in services and
allows extending to CHAPTER/REVIEW/... scopes consistently.
"""

from __future__ import annotations

from typing import Final

from src.schemas.novel.dialogue import ScopeType

# Dot-notation domain prefix per scope (PascalCase + .Session)
SCOPE_EVENT_PREFIX: Final[dict[str, str]] = {
    ScopeType.GENESIS.value: "Genesis.Session",
    ScopeType.CHAPTER.value: "Chapter.Session",
    ScopeType.REVIEW.value: "Review.Session",
    ScopeType.PLANNING.value: "Planning.Session",
    ScopeType.WORLDBUILDING.value: "Worldbuilding.Session",
}

# Aggregate type per scope
SCOPE_AGGREGATE_TYPE: Final[dict[str, str]] = {
    ScopeType.GENESIS.value: "GenesisSession",
    ScopeType.CHAPTER.value: "ChapterSession",
    ScopeType.REVIEW.value: "ReviewSession",
    ScopeType.PLANNING.value: "PlanningSession",
    ScopeType.WORLDBUILDING.value: "WorldbuildingSession",
}

# Domain bus topic per scope (defaults to generic conversation topic)
SCOPE_DOMAIN_TOPIC: Final[dict[str, str]] = {
    ScopeType.GENESIS.value: "genesis.session.events",
    ScopeType.CHAPTER.value: "chapter.session.events",
    ScopeType.REVIEW.value: "review.session.events",
    ScopeType.PLANNING.value: "planning.session.events",
    ScopeType.WORLDBUILDING.value: "worldbuilding.session.events",
}

DEFAULT_DOMAIN_TOPIC: Final[str] = "conversation.session.events"


def get_domain_prefix(scope_type: str | ScopeType) -> str:
    key = scope_type.value if isinstance(scope_type, ScopeType) else str(scope_type)
    key = key.upper()
    return SCOPE_EVENT_PREFIX.get(key, "Conversation.Session")


def get_aggregate_type(scope_type: str | ScopeType) -> str:
    key = scope_type.value if isinstance(scope_type, ScopeType) else str(scope_type)
    key = key.upper()
    return SCOPE_AGGREGATE_TYPE.get(key, "ConversationSession")


def get_domain_topic(scope_type: str | ScopeType) -> str:
    key = scope_type.value if isinstance(scope_type, ScopeType) else str(scope_type)
    key = key.upper()
    return SCOPE_DOMAIN_TOPIC.get(key, DEFAULT_DOMAIN_TOPIC)


def build_event_type(scope_type: str | ScopeType, action: str) -> str:
    """Build full dot-notation event type, e.g., Genesis.Session.Round.Created.

    Args:
        scope_type: Dialogue scope (string or ScopeType enum)
        action: Action part in dot notation, e.g., "Round.Created" or "Command.Received"
    """
    prefix = get_domain_prefix(scope_type)
    action_str = action.strip(".")
    return f"{prefix}.{action_str}"


__all__ = [
    "get_domain_prefix",
    "get_aggregate_type",
    "get_domain_topic",
    "build_event_type",
]
