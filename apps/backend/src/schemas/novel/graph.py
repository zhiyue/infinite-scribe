"""
Knowledge graph schemas based on ADR-005

This module defines schemas for the Neo4j graph database structure,
supporting hierarchical world-building with network relationships.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from src.schemas.base import BaseSchema


class NodeType(str, Enum):
    """Graph node types"""

    NOVEL = "Novel"
    WORLD_DIMENSION = "WorldDimension"
    WORLD_RULE = "WorldRule"
    RULE_DETAIL = "RuleDetail"
    LOCATION = "Location"
    CHARACTER = "Character"
    CHAPTER = "Chapter"
    SCENE = "Scene"
    EVENT = "Event"
    CHARACTER_STATE = "CharacterState"
    CONSTRAINT = "Constraint"
    CONFLICT = "Conflict"


class RelationshipType(str, Enum):
    """Graph relationship types"""

    # Character relationships
    RELATES_TO = "RELATES_TO"  # Character to character

    # Location hierarchy
    LOCATED_IN = "LOCATED_IN"  # Location to parent location

    # Rule application
    APPLIES_TO = "APPLIES_TO"  # Rule to dimension/location/character

    # Scene participation
    PARTICIPATES_IN = "PARTICIPATES_IN"  # Character to scene

    # Event relationships
    HAPPENS_IN = "HAPPENS_IN"  # Event to scene
    TRIGGERS = "TRIGGERS"  # Event to event (causality)
    AFFECTS = "AFFECTS"  # Event to character

    # Structural relationships
    BELONGS_TO = "BELONGS_TO"  # Generic ownership/membership
    CONTAINS = "CONTAINS"  # Chapter contains scenes
    HAS_STATE = "HAS_STATE"  # Character to character state

    # Conflict relationships
    VIOLATES = "VIOLATES"  # Conflict violates constraint
    INVOLVES = "INVOLVES"  # Conflict involves entities


class CharacterRole(str, Enum):
    """Character role types"""

    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    MINOR = "minor"
    BACKGROUND = "background"


class LocationType(str, Enum):
    """Location hierarchy types"""

    UNIVERSE = "universe"
    GALAXY = "galaxy"
    SOLAR_SYSTEM = "solar_system"
    PLANET = "planet"
    CONTINENT = "continent"
    COUNTRY = "country"
    REGION = "region"
    CITY = "city"
    DISTRICT = "district"
    BUILDING = "building"
    ROOM = "room"
    AREA = "area"  # Generic area


class ConflictSeverity(str, Enum):
    """Conflict severity levels"""

    LOW = "low"  # Minor inconsistency
    MEDIUM = "medium"  # Notable issue
    HIGH = "high"  # Major problem
    CRITICAL = "critical"  # Story-breaking


# Base Node Schemas


class GraphNodeBase(BaseSchema):
    """Base schema for graph nodes"""

    app_id: str = Field(..., description="Unique identifier across the system")
    novel_id: UUID = Field(..., description="Novel scope identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# Novel and World-Building Nodes


class NovelNode(GraphNodeBase):
    """Root novel node"""

    title: str = Field(..., max_length=255, description="Novel title")
    theme: str | None = Field(None, description="Novel theme")
    genre: str | None = Field(None, description="Novel genre")
    setting: str | None = Field(None, description="General setting description")

    class Config:
        json_schema_extra = {"node_type": NodeType.NOVEL}


class WorldDimensionNode(GraphNodeBase):
    """World-building dimension category"""

    name: str = Field(..., description="Dimension name (e.g., 'Magic System', 'Technology')")
    description: str = Field(..., description="Dimension description")
    importance: int = Field(5, ge=1, le=10, description="Importance level (1-10)")

    class Config:
        json_schema_extra = {"node_type": NodeType.WORLD_DIMENSION}


class WorldRuleNode(GraphNodeBase):
    """Specific world rule or law"""

    dimension_id: str = Field(..., description="Parent dimension app_id")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    constraints: list[str] = Field(default_factory=list, description="Rule constraints")
    examples: list[str] = Field(default_factory=list, description="Rule examples")

    class Config:
        json_schema_extra = {"node_type": NodeType.WORLD_RULE}


# Location Nodes


class LocationNode(GraphNodeBase):
    """Hierarchical location"""

    name: str = Field(..., description="Location name")
    type: LocationType = Field(..., description="Location type")
    description: str | None = Field(None, description="Location description")
    parent_id: str | None = Field(None, description="Parent location app_id")
    coordinates: dict[str, float] | None = Field(None, description="Optional coordinates")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Location attributes")

    class Config:
        json_schema_extra = {"node_type": NodeType.LOCATION}

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        """Validate coordinate format"""
        if v is not None:
            required_keys = {"lat", "lon"}
            if not all(k in v for k in required_keys):
                raise ValueError("Coordinates must include 'lat' and 'lon'")
        return v


# Character Nodes


class CharacterNode(GraphNodeBase):
    """Character with 8 dimensions"""

    # Basic attributes
    name: str = Field(..., description="Character name")
    role: CharacterRole = Field(..., description="Character role")
    age: int | None = Field(None, ge=0, le=999, description="Character age")
    gender: str | None = Field(None, description="Character gender")

    # 8 Character dimensions
    appearance: dict[str, Any] = Field(default_factory=dict, description="Physical appearance details")
    personality: dict[str, Any] = Field(default_factory=dict, description="Personality traits and characteristics")
    background: dict[str, Any] = Field(default_factory=dict, description="Character background and history")
    motivation: dict[str, Any] = Field(default_factory=dict, description="Character motivations and drives")
    goals: dict[str, list[str]] = Field(
        default_factory=lambda: {"short_term": [], "mid_term": [], "long_term": []},
        description="Character goals (short/mid/long term)",
    )
    obstacles: dict[str, list[str]] = Field(
        default_factory=lambda: {"internal": [], "external": [], "environmental": []}, description="Character obstacles"
    )
    arc: dict[str, Any] = Field(default_factory=dict, description="Character development arc")
    secrets: list[str] = Field(default_factory=list, description="Character secrets and hidden information")

    class Config:
        json_schema_extra = {"node_type": NodeType.CHARACTER}

    @field_validator("goals", "obstacles")
    @classmethod
    def validate_structure(cls, v: dict) -> dict:
        """Validate dictionary structure"""
        return v


# Story Structure Nodes


class ChapterNode(GraphNodeBase):
    """Story chapter"""

    chapter_number: int = Field(..., ge=1, description="Chapter number")
    title: str = Field(..., description="Chapter title")
    summary: str | None = Field(None, description="Chapter summary")
    word_count: int = Field(0, ge=0, description="Chapter word count")
    status: str = Field("draft", description="Chapter status")

    class Config:
        json_schema_extra = {"node_type": NodeType.CHAPTER}


class SceneNode(GraphNodeBase):
    """Chapter scene"""

    chapter_id: str = Field(..., description="Parent chapter app_id")
    scene_number: int = Field(..., ge=1, description="Scene number within chapter")
    location_id: str | None = Field(None, description="Scene location app_id")
    time: str | None = Field(None, description="Scene time/date")
    description: str = Field(..., description="Scene description")
    mood: str | None = Field(None, description="Scene mood/atmosphere")

    class Config:
        json_schema_extra = {"node_type": NodeType.SCENE}


class EventNode(GraphNodeBase):
    """Plot event"""

    scene_id: str = Field(..., description="Scene app_id where event occurs")
    event_type: str = Field(..., description="Event type/category")
    description: str = Field(..., description="Event description")
    timestamp: str | None = Field(None, description="In-story timestamp")
    impact_level: int = Field(5, ge=1, le=10, description="Event impact (1-10)")

    class Config:
        json_schema_extra = {"node_type": NodeType.EVENT}


# State and Constraint Nodes


class CharacterStateNode(GraphNodeBase):
    """Character state at specific chapter"""

    character_id: str = Field(..., description="Character app_id")
    chapter_id: str = Field(..., description="Chapter app_id")
    physical_state: dict[str, Any] = Field(default_factory=dict, description="Physical state/condition")
    emotional_state: dict[str, Any] = Field(default_factory=dict, description="Emotional state")
    location_id: str | None = Field(None, description="Character location app_id")
    possessions: list[str] = Field(default_factory=list, description="Character possessions")
    relationships: dict[str, str] = Field(default_factory=dict, description="Relationship states with other characters")

    class Config:
        json_schema_extra = {"node_type": NodeType.CHARACTER_STATE}


class ConstraintNode(GraphNodeBase):
    """Consistency constraint"""

    constraint_type: str = Field(..., description="Constraint type")
    description: str = Field(..., description="Constraint description")
    scope: str = Field(..., description="Constraint scope (global/local)")
    rules: list[str] = Field(..., description="Constraint rules")

    class Config:
        json_schema_extra = {"node_type": NodeType.CONSTRAINT}


class ConflictNode(GraphNodeBase):
    """Detected consistency conflict"""

    conflict_type: str = Field(..., description="Conflict type")
    description: str = Field(..., description="Conflict description")
    severity: ConflictSeverity = Field(..., description="Conflict severity")
    entities: list[str] = Field(..., description="Involved entity app_ids")
    constraint_id: str | None = Field(None, description="Violated constraint app_id")
    resolution: str | None = Field(None, description="Suggested resolution")
    resolved: bool = Field(False, description="Whether conflict is resolved")

    class Config:
        json_schema_extra = {"node_type": NodeType.CONFLICT}


# Relationship Schemas


class RelationshipBase(BaseSchema):
    """Base relationship schema"""

    from_id: str = Field(..., description="Source node app_id")
    to_id: str = Field(..., description="Target node app_id")
    relationship_type: RelationshipType = Field(..., description="Relationship type")
    properties: dict[str, Any] = Field(default_factory=dict, description="Relationship properties")
    created_at: datetime = Field(..., description="Creation timestamp")


class CharacterRelationship(RelationshipBase):
    """Character to character relationship"""

    relationship_type: RelationshipType = Field(RelationshipType.RELATES_TO)
    relationship_name: str = Field(..., description="Relationship name (e.g., 'friend', 'enemy')")
    strength: int = Field(0, ge=-10, le=10, description="Relationship strength (-10 to +10)")
    history: str | None = Field(None, description="Relationship history")

    @model_validator(mode="after")
    def validate_relationship(self):
        """Add relationship details to properties"""
        self.properties.update({"name": self.relationship_name, "strength": self.strength, "history": self.history})
        return self


class SceneParticipation(RelationshipBase):
    """Character participation in scene"""

    relationship_type: RelationshipType = Field(RelationshipType.PARTICIPATES_IN)
    role_in_scene: str = Field(..., description="Character's role in the scene")
    importance: int = Field(5, ge=1, le=10, description="Importance in scene (1-10)")

    @model_validator(mode="after")
    def validate_participation(self):
        """Add participation details to properties"""
        self.properties.update({"role": self.role_in_scene, "importance": self.importance})
        return self


class EventCausality(RelationshipBase):
    """Event causality chain"""

    relationship_type: RelationshipType = Field(RelationshipType.TRIGGERS)
    causality_type: str = Field(..., description="Type of causality (direct/indirect)")
    probability: float = Field(1.0, ge=0.0, le=1.0, description="Causality probability")
    delay: str | None = Field(None, description="Time delay between events")

    @model_validator(mode="after")
    def validate_causality(self):
        """Add causality details to properties"""
        self.properties.update({"type": self.causality_type, "probability": self.probability, "delay": self.delay})
        return self


# Query Result Schemas


class GraphQueryResult(BaseSchema):
    """Generic graph query result"""

    nodes: list[dict[str, Any]] = Field(default_factory=list, description="Query result nodes")
    relationships: list[dict[str, Any]] = Field(default_factory=list, description="Query result relationships")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Query metadata")


class CharacterNetwork(BaseSchema):
    """Character relationship network"""

    central_character_id: str = Field(..., description="Central character app_id")
    characters: list[CharacterNode] = Field(..., description="Network characters")
    relationships: list[CharacterRelationship] = Field(..., description="Character relationships")
    network_density: float = Field(0.0, ge=0.0, le=1.0, description="Network density metric")

    @model_validator(mode="after")
    def calculate_density(self):
        """Calculate network density"""
        n = len(self.characters)
        if n > 1:
            max_relationships = n * (n - 1) / 2
            actual_relationships = len(self.relationships)
            self.network_density = actual_relationships / max_relationships if max_relationships > 0 else 0.0
        return self


class LocationHierarchy(BaseSchema):
    """Location hierarchy tree"""

    root_location: LocationNode = Field(..., description="Root location")
    locations: list[LocationNode] = Field(..., description="All locations in hierarchy")
    hierarchy: dict[str, list[str]] = Field(
        default_factory=dict, description="Parent-child relationships (parent_id -> [child_ids])"
    )

    def get_path(self, location_id: str) -> list[str]:
        """Get path from root to location"""
        path = []
        current = location_id
        location_map = {loc.app_id: loc for loc in self.locations}

        while current:
            path.append(current)
            loc = location_map.get(current)
            current = loc.parent_id if loc else None

        return list(reversed(path))


class StoryTimeline(BaseSchema):
    """Story timeline with events"""

    chapters: list[ChapterNode] = Field(..., description="Story chapters")
    scenes: list[SceneNode] = Field(..., description="All scenes")
    events: list[EventNode] = Field(..., description="All events")
    causality_chains: list[EventCausality] = Field(default_factory=list, description="Event causality relationships")

    def get_chapter_events(self, chapter_id: str) -> list[EventNode]:
        """Get all events in a chapter"""
        chapter_scenes = {s.app_id for s in self.scenes if s.chapter_id == chapter_id}
        return [e for e in self.events if e.scene_id in chapter_scenes]
