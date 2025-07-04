"""
Database models for PostgreSQL tables - Legacy compatibility file.

This file has been refactored for maintainability. All models are now
split into smaller, focused modules:

- enums.py: All enumeration types
- base.py: Base model class with common functionality  
- entities.py: Core business entity models (Novel, Chapter, Character, etc.)
- infrastructure.py: Architecture models (Events, Commands, Tasks)
- genesis.py: Genesis process specific models

This file maintains backward compatibility by re-exporting all models.
"""

# Import all models from split modules for wildcard export
from .enums import *
from .base import BaseDBModel
from .entities import *
from .infrastructure import *
from .genesis import *

# Legacy compatibility - explicit imports for type checking
from .enums import (
    AgentType,
    NovelStatus,
    ChapterStatus,
    GenesisStatus,
    GenesisStage,
    CommandStatus,
    TaskStatus,
    OutboxStatus,
    HandleStatus,
    WorkflowStatus,
    WorldviewEntryType
)

from .entities import (
    NovelModel,
    ChapterModel,
    ChapterVersionModel,
    CharacterModel,
    WorldviewEntryModel,
    StoryArcModel,
    ReviewModel
)

from .infrastructure import (
    DomainEventModel,
    CommandInboxModel,
    AsyncTaskModel,
    EventOutboxModel,
    FlowResumeHandleModel
)

from .genesis import (
    ConceptTemplateModel,
    GenesisSessionModel
)

# Utility functions
from typing import Any
from uuid import UUID

def get_all_models() -> list[type[BaseDBModel]]:
    """Get all database model classes."""
    return [
        # Core entities
        NovelModel,
        ChapterModel,
        ChapterVersionModel,
        CharacterModel,
        WorldviewEntryModel,
        StoryArcModel,
        ReviewModel,
        # Infrastructure
        DomainEventModel,
        CommandInboxModel,
        AsyncTaskModel,
        EventOutboxModel,
        FlowResumeHandleModel,
        # Genesis
        ConceptTemplateModel,
        GenesisSessionModel,
    ]

def get_core_entity_models() -> list[type[BaseDBModel]]:
    """Get core business entity models."""
    return [
        NovelModel,
        ChapterModel,
        ChapterVersionModel,
        CharacterModel,
        WorldviewEntryModel,
        StoryArcModel,
        ReviewModel,
    ]

def get_infrastructure_models() -> list[type[BaseDBModel]]:
    """Get infrastructure/architecture models."""
    return [
        DomainEventModel,
        CommandInboxModel,
        AsyncTaskModel,
        EventOutboxModel,
        FlowResumeHandleModel,
    ]

def validate_model_data(model_class: type[BaseDBModel], data: dict) -> BaseDBModel:
    """Validate data against a model class."""
    return model_class(**data)

# Legacy compatibility - maintain original __all__ export list
__all__ = [
    # Enums
    "AgentType",
    "CommandStatus",
    "TaskStatus",
    "OutboxStatus",
    "HandleStatus",
    "WorldviewEntryType",
    "NovelStatus",
    "ChapterStatus",
    "GenesisStatus",
    "GenesisStage",
    "WorkflowStatus",
    # Base
    "BaseDBModel",
    # Core entities
    "NovelModel",
    "ChapterModel",
    "ChapterVersionModel",
    "CharacterModel",
    "WorldviewEntryModel",
    "StoryArcModel",
    "ReviewModel",
    # Infrastructure
    "DomainEventModel",
    "CommandInboxModel",
    "AsyncTaskModel",
    "EventOutboxModel",
    "FlowResumeHandleModel",
    # Genesis
    "ConceptTemplateModel",
    "GenesisSessionModel",
    # Utility functions
    "get_all_models",
    "get_core_entity_models",
    "get_infrastructure_models",
    "validate_model_data",
]