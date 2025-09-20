"""Unified Event Mapping Configuration

This module provides centralized mapping for all event-related transformations:
- Task type normalization (suffix to base action mapping)
- Event-payload class mapping
- Command-event mapping
- Event validation utilities

Following the Event Mapping Unification strategy to avoid scattered mapping logic.
"""

from typing import Final

from src.schemas.enums import GenesisEventType
from src.schemas.genesis_events import (
    AIGenerationCompletedPayload,
    AIGenerationStartedPayload,
    ConceptSelectedPayload,
    FeedbackProvidedPayload,
    GenesisEventPayload,
    InspirationGeneratedPayload,
    NovelCreatedFromGenesisPayload,
    StageCompletedPayload,
    StageEnteredPayload,
)

# ==================== Task Type Normalization ====================

# Map action suffixes to base action types for AsyncTask task_type field
TASK_TYPE_SUFFIX_MAPPING: Final[dict[str, str]] = {
    "GenerationRequested": "Generation",
    "Generated": "Generation",
    "EvaluationRequested": "Evaluation",
    "Evaluated": "Evaluation",
    "CheckRequested": "Check",
    "Checked": "Check",
    "AnalysisRequested": "Analysis",
    "Analyzed": "Analysis",
    "ValidationRequested": "Validation",
    "Validated": "Validation",
    "RevisionRequested": "Revision",
    "Revised": "Revision",
    "Requested": "Request",
    "Started": "Start",
    "Completed": "Complete",
    "Result": "Result",
}


def normalize_task_type(event_type: str) -> str:
    """Normalize capability event/task type to a base task_type for AsyncTask.

    Maps action suffixes to base action types, ensuring three-segment format:
    Capability.Entity.Action

    Examples:
      - "Character.Design.GenerationRequested" -> "Character.Design.Generation"
      - "Outliner.Theme.Generated" -> "Outliner.Theme.Generation"
      - "Review.Quality.EvaluationRequested" -> "Review.Quality.Evaluation"
      - "Review.Consistency.CheckRequested" -> "Review.Consistency.Check"

    Args:
        event_type: The event type string to normalize

    Returns:
        Normalized task type with base action suffix
    """
    if not event_type:
        return ""

    parts = event_type.split(".")
    if not parts:
        return event_type

    last_part = parts[-1]
    if last_part in TASK_TYPE_SUFFIX_MAPPING and len(parts) >= 2:
        parts[-1] = TASK_TYPE_SUFFIX_MAPPING[last_part]
        return ".".join(parts)

    return event_type


# ==================== Event-Payload Mapping ====================

# Event type to payload class mapping (covers high-frequency events)
EVENT_PAYLOAD_MAPPING: Final[dict[str, type]] = {
    "STAGE_ENTERED": StageEnteredPayload,
    "STAGE_COMPLETED": StageCompletedPayload,
    "CONCEPT_SELECTED": ConceptSelectedPayload,
    "INSPIRATION_GENERATED": InspirationGeneratedPayload,
    "FEEDBACK_PROVIDED": FeedbackProvidedPayload,
    "AI_GENERATION_STARTED": AIGenerationStartedPayload,
    "AI_GENERATION_COMPLETED": AIGenerationCompletedPayload,
    "NOVEL_CREATED_FROM_GENESIS": NovelCreatedFromGenesisPayload,
}


def get_event_payload_class(event_type: str | GenesisEventType) -> type:
    """Get the appropriate payload class for an event type.

    Falls back to generic GenesisEventPayload for unmapped events.

    Args:
        event_type: Event type as string or enum

    Returns:
        Payload class for the event type
    """
    key = event_type.value if isinstance(event_type, GenesisEventType) else str(event_type)
    return EVENT_PAYLOAD_MAPPING.get(key, GenesisEventPayload)


# ==================== Command-Event Mapping ====================

# Command to event action mapping
COMMAND_EVENT_MAPPING: Final[dict[str, str]] = {
    "Character.Request": "Character.Requested",
    "Character.Requested": "Character.Requested",
    "CHARACTER_REQUEST": "Character.Requested",
    "Command.Genesis.Session.Character.Request": "Character.Requested",
    "Theme.Request": "Theme.Requested",
    "THEME_REQUEST": "Theme.Requested",
    "Command.Genesis.Session.Theme.Request": "Theme.Requested",
    "Seed.Request": "Seed.Requested",
    "SEED_REQUEST": "Seed.Requested",
    "Command.Genesis.Session.Seed.Request": "Seed.Requested",
    "World.Request": "World.Requested",
    "WORLD_REQUEST": "World.Requested",
    "Command.Genesis.Session.World.Request": "World.Requested",
    "Plot.Request": "Plot.Requested",
    "PLOT_REQUEST": "Plot.Requested",
    "Command.Genesis.Session.Plot.Request": "Plot.Requested",
    "Details.Request": "Details.Requested",
    "DETAILS_REQUEST": "Details.Requested",
    "Command.Genesis.Session.Details.Request": "Details.Requested",
    # Additional command mappings for complete Genesis workflow
    "Command.Genesis.Session.Theme.Revise": "Theme.Revised",
    "Command.Genesis.Session.Theme.Confirm": "Theme.Confirmed",
    "Command.Genesis.Session.World.Update": "World.Updated",
    "Command.Genesis.Session.World.Confirm": "World.Confirmed",
    "Command.Genesis.Session.Character.Update": "Character.Updated",
    "Command.Genesis.Session.Character.Confirm": "Character.Confirmed",
    "Command.Genesis.Session.CharacterNetwork.Create": "CharacterNetwork.Created",
    "Command.Genesis.Session.Plot.Update": "Plot.Updated",
    "Command.Genesis.Session.Plot.Confirm": "Plot.Confirmed",
    "Command.Genesis.Session.Details.Confirm": "Details.Confirmed",
    # Session-level commands (note: avoiding duplicate "Session" in final event type)
    "Command.Genesis.Session.Start": "Genesis.Started",
    "Command.Genesis.Session.Stage.Complete": "Genesis.StageCompleted",
    "Command.Genesis.Session.Finish": "Genesis.Finished",
    "Command.Genesis.Session.Fail": "Genesis.Failed",
    "Command.Genesis.Session.Branch.Create": "Genesis.BranchCreated",
    "Stage.Validate": "Stage.ValidationRequested",
    "Stage.Lock": "Stage.LockRequested",
    "Outline.Request": "Outline.Requested",
    "Review.Quality.Request": "Review.Quality.Requested",
    "Review.Consistency.Request": "Review.Consistency.Requested",
}


def get_event_by_command(command: str) -> str | None:
    """Get event action from command type.

    Args:
        command: Command type string

    Returns:
        Event action string or None if not mapped
    """
    return COMMAND_EVENT_MAPPING.get(command)


# ==================== Event Categories ====================

# Event category mapping for routing and organization
EVENT_CATEGORY_MAPPING: Final[dict[str, str]] = {
    "STAGE_ENTERED": "stage_lifecycle",
    "STAGE_COMPLETED": "stage_lifecycle",
    "STAGE_CONFIRMED": "stage_lifecycle",
    "CONCEPT_SELECTED": "content_generation",
    "INSPIRATION_GENERATED": "content_generation",
    "FEEDBACK_PROVIDED": "content_generation",
    "AI_GENERATION_STARTED": "ai_interaction",
    "AI_GENERATION_COMPLETED": "ai_interaction",
    "AI_GENERATION_FAILED": "ai_interaction",
    "USER_INPUT_REQUESTED": "user_interaction",
    "USER_INPUT_RECEIVED": "user_interaction",
    "USER_FEEDBACK_RECEIVED": "user_interaction",
    "NOVEL_CREATION_INITIATED": "novel_creation",
    "NOVEL_CREATED_FROM_GENESIS": "novel_creation",
    "GENESIS_SESSION_STARTED": "session_lifecycle",
    "GENESIS_SESSION_COMPLETED": "session_lifecycle",
    "GENESIS_SESSION_ABANDONED": "session_lifecycle",
    "GENESIS_SESSION_PAUSED": "session_lifecycle",
    "GENESIS_SESSION_RESUMED": "session_lifecycle",
}


def get_event_category(event_type: str | GenesisEventType) -> str:
    """Get the category for an event type.

    Args:
        event_type: Event type as string or enum

    Returns:
        Event category string, defaults to "general"
    """
    key = event_type.value if isinstance(event_type, GenesisEventType) else str(event_type)
    return EVENT_CATEGORY_MAPPING.get(key, "general")


def list_events_by_category(category: str) -> list[str]:
    """List all events in a given category.

    Args:
        category: Event category name

    Returns:
        List of event type strings in the category
    """
    return [event for event, cat in EVENT_CATEGORY_MAPPING.items() if cat == category]


# ==================== Validation Tools ====================


def validate_event_mappings() -> dict[str, list[str]]:
    """Validate mapping completeness and consistency.

    Returns:
        Dictionary of validation issues grouped by type
    """
    issues = {
        "missing_high_frequency_mapping": [],
        "orphaned_payload_mappings": [],
        "orphaned_command_mappings": [],
        "missing_category_mapping": [],
    }

    # Define high-frequency events that should have dedicated payload classes
    high_frequency_events = [
        "STAGE_ENTERED",
        "STAGE_COMPLETED",
        "AI_GENERATION_STARTED",
        "AI_GENERATION_COMPLETED",
        "CONCEPT_SELECTED",
    ]

    # Check high-frequency events have payload mapping
    for event in high_frequency_events:
        if event not in EVENT_PAYLOAD_MAPPING:
            issues["missing_high_frequency_mapping"].append(event)

    # Check for orphaned payload mappings (mapped but not in enum)
    valid_events = {event.value for event in GenesisEventType}
    for mapped_event in EVENT_PAYLOAD_MAPPING.keys():
        if mapped_event not in valid_events:
            issues["orphaned_payload_mappings"].append(mapped_event)

    # Check for orphaned command mappings (target events not in enum)
    valid_event_actions = set(COMMAND_EVENT_MAPPING.values())
    # Note: Command event actions are domain event actions, not GenesisEventType values
    # This is intentional as they map to different event spaces

    # Check events have category mapping
    for event in GenesisEventType:
        if event.value not in EVENT_CATEGORY_MAPPING:
            issues["missing_category_mapping"].append(event.value)

    # Filter out empty issue lists
    return {k: v for k, v in issues.items() if v}


def get_all_task_type_mappings() -> dict[str, str]:
    """Get all task type suffix mappings for debugging/documentation.

    Returns:
        Copy of the task type suffix mapping dictionary
    """
    return TASK_TYPE_SUFFIX_MAPPING.copy()


def get_all_event_payload_mappings() -> dict[str, str]:
    """Get all event-payload mappings for debugging/documentation.

    Returns:
        Dictionary mapping event types to payload class names
    """
    return {k: v.__name__ for k, v in EVENT_PAYLOAD_MAPPING.items()}


def get_mapping_statistics() -> dict[str, int]:
    """Get statistics about current mappings.

    Returns:
        Dictionary with mapping counts
    """
    return {
        "total_task_type_mappings": len(TASK_TYPE_SUFFIX_MAPPING),
        "total_event_payload_mappings": len(EVENT_PAYLOAD_MAPPING),
        "total_command_event_mappings": len(COMMAND_EVENT_MAPPING),
        "total_event_categories": len(set(EVENT_CATEGORY_MAPPING.values())),
        "total_categorized_events": len(EVENT_CATEGORY_MAPPING),
        "total_genesis_event_types": len(GenesisEventType),
    }


# ==================== Exports ====================

__all__ = [
    # Core mapping functions
    "normalize_task_type",
    "get_event_payload_class",
    "get_event_by_command",
    "get_event_category",
    "list_events_by_category",
    # Validation and debugging
    "validate_event_mappings",
    "get_all_task_type_mappings",
    "get_all_event_payload_mappings",
    "get_mapping_statistics",
    # Constants (for advanced usage)
    "TASK_TYPE_SUFFIX_MAPPING",
    "EVENT_PAYLOAD_MAPPING",
    "COMMAND_EVENT_MAPPING",
    "EVENT_CATEGORY_MAPPING",
]
