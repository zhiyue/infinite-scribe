"""
Genesis workflow domain event models and utilities
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.schemas.base import BaseSchema
from src.schemas.enums import GenesisEventType, GenesisStage


class GenesisEventPayload(BaseModel):
    """Base class for genesis event payloads"""

    session_id: UUID = Field(..., description="Genesis session identifier")
    user_id: UUID | None = Field(None, description="User identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")


class GenesisSessionStartedPayload(GenesisEventPayload):
    """Payload for genesis session started event"""

    mode: str = Field(..., description="Genesis mode: 'guided' or 'free-form'")
    initial_stage: GenesisStage = Field(..., description="Initial stage of the session")
    session_metadata: dict[str, Any] | None = Field(None, description="Additional session metadata")


class StageEnteredPayload(GenesisEventPayload):
    """Payload for stage entered event"""

    stage: GenesisStage = Field(..., description="Stage that was entered")
    previous_stage: GenesisStage | None = Field(None, description="Previous stage")
    context_data: dict[str, Any] | None = Field(None, description="Context data for the stage")


class StageCompletedPayload(GenesisEventPayload):
    """Payload for stage completed event"""

    stage: GenesisStage = Field(..., description="Stage that was completed")
    stage_data: dict[str, Any] = Field(..., description="Data generated/confirmed in this stage")
    next_stage: GenesisStage | None = Field(None, description="Next stage to proceed to")


class ConceptSelectedPayload(GenesisEventPayload):
    """Payload for concept selected event"""

    concept_id: str = Field(..., description="Selected concept identifier")
    concept_data: dict[str, Any] = Field(..., description="Selected concept data")
    selection_metadata: dict[str, Any] | None = Field(None, description="Selection metadata")


class InspirationGeneratedPayload(GenesisEventPayload):
    """Payload for inspiration generated event"""

    inspiration_type: str = Field(..., description="Type of inspiration generated")
    inspiration_content: dict[str, Any] = Field(..., description="Generated inspiration content")
    generation_metadata: dict[str, Any] | None = Field(None, description="Generation metadata")


class FeedbackProvidedPayload(GenesisEventPayload):
    """Payload for feedback provided event"""

    feedback_type: str = Field(..., description="Type of feedback")
    feedback_content: str = Field(..., description="Feedback content")
    target_stage: GenesisStage = Field(..., description="Stage the feedback is for")
    feedback_metadata: dict[str, Any] | None = Field(None, description="Feedback metadata")


class AIGenerationStartedPayload(GenesisEventPayload):
    """Payload for AI generation started event"""

    generation_type: str = Field(..., description="Type of AI generation")
    input_data: dict[str, Any] = Field(..., description="Input data for generation")
    correlation_id: UUID = Field(..., description="Correlation ID for tracking")


class AIGenerationCompletedPayload(GenesisEventPayload):
    """Payload for AI generation completed event"""

    generation_type: str = Field(..., description="Type of AI generation")
    output_data: dict[str, Any] = Field(..., description="Generated output data")
    correlation_id: UUID = Field(..., description="Correlation ID for tracking")
    generation_duration: float | None = Field(None, description="Generation duration in seconds")


class NovelCreatedFromGenesisPayload(GenesisEventPayload):
    """Payload for novel created from genesis event"""

    novel_id: UUID = Field(..., description="Created novel identifier")
    novel_data: dict[str, Any] = Field(..., description="Novel creation data")
    genesis_data: dict[str, Any] = Field(..., description="Genesis session data used for creation")


# Union type for all genesis event payloads
GenesisEventPayloadUnion = (
    GenesisSessionStartedPayload
    | StageEnteredPayload
    | StageCompletedPayload
    | ConceptSelectedPayload
    | InspirationGeneratedPayload
    | FeedbackProvidedPayload
    | AIGenerationStartedPayload
    | AIGenerationCompletedPayload
    | NovelCreatedFromGenesisPayload
    | GenesisEventPayload  # Generic payload for other events
)


class GenesisEventCreate(BaseSchema):
    """Genesis domain event creation model"""

    event_id: UUID = Field(default_factory=uuid4, description="Event unique identifier")
    correlation_id: UUID | None = Field(None, description="Correlation ID for tracking related events")
    causation_id: UUID | None = Field(None, description="ID of the event that caused this event")
    event_type: GenesisEventType = Field(..., description="Type of genesis event")
    event_version: int = Field(default=1, description="Event schema version")
    aggregate_type: str = Field(default="GenesisSession", description="Aggregate type")
    aggregate_id: str = Field(..., description="Genesis session ID as string")
    payload: dict[str, Any] = Field(..., description="Event payload data")
    metadata: dict[str, Any] | None = Field(None, description="Event metadata")


class GenesisEventResponse(BaseSchema):
    """Genesis domain event response model"""

    id: int = Field(..., description="Auto-increment ID for ordering")
    event_id: UUID = Field(..., description="Event unique identifier")
    correlation_id: UUID | None = Field(None, description="Correlation ID for tracking related events")
    causation_id: UUID | None = Field(None, description="ID of the event that caused this event")
    event_type: str = Field(..., description="Type of genesis event")
    event_version: int = Field(..., description="Event schema version")
    aggregate_type: str = Field(..., description="Aggregate type")
    aggregate_id: str = Field(..., description="Genesis session ID as string")
    payload: dict[str, Any] | None = Field(None, description="Event payload data")
    metadata: dict[str, Any] | None = Field(None, description="Event metadata")
    created_at: datetime = Field(..., description="Event creation timestamp")


class EventSerializationUtils:
    """Utilities for event serialization and deserialization"""

    @staticmethod
    def serialize_payload(payload: GenesisEventPayloadUnion) -> dict[str, Any]:
        """Serialize event payload to dictionary"""
        if isinstance(payload, BaseModel):
            return payload.model_dump(exclude_unset=True)
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def deserialize_payload(event_type: GenesisEventType, payload_data: dict[str, Any]) -> GenesisEventPayloadUnion:
        """Deserialize payload data based on event type"""

        payload_map = {
            GenesisEventType.GENESIS_SESSION_STARTED: GenesisSessionStartedPayload,
            GenesisEventType.STAGE_ENTERED: StageEnteredPayload,
            GenesisEventType.STAGE_COMPLETED: StageCompletedPayload,
            GenesisEventType.CONCEPT_SELECTED: ConceptSelectedPayload,
            GenesisEventType.INSPIRATION_GENERATED: InspirationGeneratedPayload,
            GenesisEventType.FEEDBACK_PROVIDED: FeedbackProvidedPayload,
            GenesisEventType.AI_GENERATION_STARTED: AIGenerationStartedPayload,
            GenesisEventType.AI_GENERATION_COMPLETED: AIGenerationCompletedPayload,
            GenesisEventType.NOVEL_CREATED_FROM_GENESIS: NovelCreatedFromGenesisPayload,
        }

        payload_class = payload_map.get(event_type, GenesisEventPayload)

        try:
            return payload_class(**payload_data)
        except Exception:
            # Fallback to generic payload if deserialization fails
            return GenesisEventPayload(**payload_data)

    @staticmethod
    def create_genesis_event(
        event_type: GenesisEventType,
        session_id: UUID,
        payload: GenesisEventPayloadUnion,
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GenesisEventCreate:
        """Create a genesis event with proper structure"""

        return GenesisEventCreate(
            event_type=event_type,
            aggregate_id=str(session_id),
            payload=EventSerializationUtils.serialize_payload(payload),
            correlation_id=correlation_id,
            causation_id=causation_id,
            metadata=metadata or {},
        )


__all__ = [
    "GenesisEventPayload",
    "GenesisSessionStartedPayload",
    "StageEnteredPayload",
    "StageCompletedPayload",
    "ConceptSelectedPayload",
    "InspirationGeneratedPayload",
    "FeedbackProvidedPayload",
    "AIGenerationStartedPayload",
    "AIGenerationCompletedPayload",
    "NovelCreatedFromGenesisPayload",
    "GenesisEventPayloadUnion",
    "GenesisEventCreate",
    "GenesisEventResponse",
    "EventSerializationUtils",
]
