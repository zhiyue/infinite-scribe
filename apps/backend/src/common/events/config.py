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
    ScopeType.GENESIS.value: "GenesisFlow",  # Updated from GenesisSession to GenesisFlow
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


# ==================== Strategy Configuration ====================

# Message type configuration for common patterns
MESSAGE_TYPE_CONFIG: Final[dict[str, str]] = {
    "quality_review": "Review.Quality.EvaluationRequested",
    "character_generation": "Character.Design.GenerationRequested",
    "theme_generation": "Outliner.Theme.GenerationRequested",
}

# Strategy configuration for orchestrator command mapping
STRATEGY_CONFIG: Final[dict[str, dict[str, str]]] = {
    "character": {
        "base_topic": "character",
        "capability_type": "Character.Design.GenerationRequested",
        "requested_action": "Character.Requested",
    },
    "theme": {
        "base_topic": "outline",
        "capability_type": "Outliner.Theme.GenerationRequested",
        "requested_action": "Theme.Requested",
    },
    "seed": {
        "base_topic": "outline",
        "capability_type": "Outliner.Concept.GenerationRequested",
        "requested_action": "Seed.Requested",
    },
    "world": {
        "base_topic": "world",
        "capability_type": "Worldbuilder.World.GenerationRequested",
        "requested_action": "World.Requested",
    },
    "plot": {
        "base_topic": "plot",
        "capability_type": "Plot.Structure.GenerationRequested",
        "requested_action": "Plot.Requested",
    },
    "details": {
        "base_topic": "writer",
        "capability_type": "Writer.Content.GenerationRequested",
        "requested_action": "Details.Requested",
    },
    "stage_validation": {
        "base_topic": "review",
        "capability_type": "Review.Consistency.CheckRequested",
        "requested_action": "Stage.ValidationRequested",
    },
    "stage_lock": {
        "base_topic": "review",
        "capability_type": "Review.Consistency.CheckRequested",
        "requested_action": "Stage.LockRequested",
    },
    "inquiry": {
        "base_topic": "inquiry",
        "capability_type": "Inquiry.Query.ProcessRequested",
        "requested_action": "Inquiry.Requested",
    },
}

# Event pattern constants
EVENT_PATTERNS: Final[dict[str, str | list[str]]] = {
    "command_received_suffix": ".Command.Received",
    "generation_completed_patterns": [
        "Character.Design.Generated",
        "Character.Generated",
        "Outliner.Theme.Generated",
        "Theme.Generated",
        "Inquiry.Response.Generated",
    ],
    "quality_review_patterns": [
        "Review.Quality.Evaluated",
        "Review.Quality.Result",
    ],
    "state_change_suffixes": [
        ".Confirmed",
        ".Updated",
        ".Revised",
        ".Completed",
        ".Created",
    ],
}

# Default values
DEFAULT_VALUES: Final[dict[str, str]] = {
    "scope_prefix": "Genesis",
    "scope_type": "GENESIS",
    "domain_topic": DEFAULT_DOMAIN_TOPIC,
}


def get_strategy_config(strategy_key: str) -> dict[str, str] | None:
    """Get strategy configuration by key.

    Args:
        strategy_key: Strategy key (e.g., "character", "theme")

    Returns:
        Strategy configuration dict or None if not found
    """
    return STRATEGY_CONFIG.get(strategy_key)


def get_strategy_keys() -> list[str]:
    """Get all available strategy keys.

    Returns:
        List of strategy configuration keys
    """
    return list(STRATEGY_CONFIG.keys())


def is_command_received_event(event_type: str) -> bool:
    """Check if event type is a command received event.

    Args:
        event_type: Event type string

    Returns:
        True if it's a command received event
    """
    return event_type.endswith(EVENT_PATTERNS["command_received_suffix"])


def is_state_change_event(event_type: str) -> bool:
    """Check if event type represents a state change that doesn't require capability tasks.

    Args:
        event_type: Event type string

    Returns:
        True if it's a state-only change event
    """
    suffixes = EVENT_PATTERNS["state_change_suffixes"]
    if isinstance(suffixes, list):
        return any(event_type.endswith(suffix) for suffix in suffixes)
    return False


def get_message_type(message_key: str) -> str:
    """Get message type from configuration.

    Args:
        message_key: Key for message type (e.g., "quality_review", "character_generation")

    Returns:
        Message type string
    """
    return MESSAGE_TYPE_CONFIG.get(message_key, "Unknown.MessageType")


__all__ = [
    "get_domain_prefix",
    "get_aggregate_type",
    "get_domain_topic",
    "build_event_type",
    "get_strategy_config",
    "get_strategy_keys",
    "is_command_received_event",
    "is_state_change_event",
    "get_message_type",
    "STRATEGY_CONFIG",
    "MESSAGE_TYPE_CONFIG",
    "EVENT_PATTERNS",
    "DEFAULT_VALUES",
]
