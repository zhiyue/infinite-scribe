"""
Dialogue state management schemas based on ADR-001

This module defines schemas for conversation sessions and rounds,
supporting the generic dialogue state management architecture.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from src.schemas.base import BaseSchema


class ScopeType(str, Enum):
    """Dialogue scope types"""

    GENESIS = "GENESIS"  # Novel creation stage
    CHAPTER = "CHAPTER"  # Chapter writing stage
    REVIEW = "REVIEW"  # Review and revision stage
    PLANNING = "PLANNING"  # Planning and outlining stage
    WORLDBUILDING = "WORLDBUILDING"  # World-building stage


class SessionStatus(str, Enum):
    """Session lifecycle status"""

    ACTIVE = "ACTIVE"  # Session is currently active
    COMPLETED = "COMPLETED"  # Session completed successfully
    ABANDONED = "ABANDONED"  # Session was abandoned
    PAUSED = "PAUSED"  # Session is paused


class DialogueRole(str, Enum):
    """Dialogue participant roles"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ConversationSessionCreate(BaseSchema):
    """Create a new conversation session"""

    scope_type: ScopeType = Field(..., description="Type of dialogue scope")
    scope_id: str = Field(..., description="Business entity ID (e.g., novel_id, chapter_id)")
    stage: str | None = Field(None, description="Optional stage within the scope")
    initial_state: dict[str, Any] | None = Field(default_factory=dict, description="Initial session state/context")


class ConversationSessionUpdate(BaseSchema):
    """Update session state"""

    status: SessionStatus | None = Field(None, description="Session status")
    stage: str | None = Field(None, description="Current stage")
    state: dict[str, Any] | None = Field(None, description="Session aggregate state")

    @model_validator(mode="after")
    def at_least_one_field(self):
        """Ensure at least one field is being updated"""
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("At least one field must be provided for update")
        return self


class ConversationSessionResponse(BaseSchema):
    """Conversation session response"""

    id: UUID = Field(..., description="Session ID")
    scope_type: ScopeType = Field(..., description="Type of dialogue scope")
    scope_id: str = Field(..., description="Business entity ID")
    status: SessionStatus = Field(..., description="Current session status")
    stage: str | None = Field(None, description="Current stage")
    state: dict[str, Any] = Field(default_factory=dict, description="Session aggregate state")
    version: int = Field(..., ge=1, description="Version for optimistic concurrency control")
    created_at: datetime = Field(..., description="Session creation time")
    updated_at: datetime = Field(..., description="Last update time")

    @field_validator("state", mode="before")
    @classmethod
    def ensure_dict(cls, v):
        """Ensure state is always a dictionary"""
        return v if isinstance(v, dict) else {}


class ConversationRoundCreate(BaseSchema):
    """Create a new conversation round/turn"""

    session_id: UUID = Field(..., description="Parent session ID")
    round_path: str = Field(
        ..., description="Hierarchical round path (e.g., '1', '2', '2.1', '2.1.1')", pattern=r"^(\d+)(\.(\d+))*$"
    )
    role: DialogueRole = Field(..., description="Participant role")
    input: dict[str, Any] = Field(..., description="Round input/prompt")
    model: str = Field(..., description="LLM model used")
    correlation_id: str | None = Field(None, description="Request correlation ID for idempotency")


class ConversationRoundUpdate(BaseSchema):
    """Update conversation round with response"""

    output: dict[str, Any] = Field(..., description="Round output/response")
    tool_calls: list[dict[str, Any]] | None = Field(None, description="Tool calls made")
    tokens_in: int = Field(..., ge=0, description="Input token count")
    tokens_out: int = Field(..., ge=0, description="Output token count")
    latency_ms: int = Field(..., ge=0, description="Response latency in milliseconds")
    cost: Decimal | None = Field(None, ge=0, decimal_places=4, description="Cost of the round")


class ConversationRoundResponse(BaseSchema):
    """Conversation round response"""

    session_id: UUID = Field(..., description="Parent session ID")
    round_path: str = Field(..., description="Hierarchical round path")
    role: DialogueRole = Field(..., description="Participant role")
    input: dict[str, Any] = Field(..., description="Round input")
    output: dict[str, Any] | None = Field(None, description="Round output")
    tool_calls: list[dict[str, Any]] | None = Field(None, description="Tool calls made")
    model: str = Field(..., description="LLM model used")
    tokens_in: int | None = Field(None, ge=0, description="Input token count")
    tokens_out: int | None = Field(None, ge=0, description="Output token count")
    latency_ms: int | None = Field(None, ge=0, description="Response latency")
    cost: Decimal | None = Field(None, description="Round cost")
    correlation_id: str | None = Field(None, description="Request correlation ID")
    created_at: datetime = Field(..., description="Round creation time")

    @field_validator("round_path")
    @classmethod
    def validate_round_path(cls, v: str) -> str:
        """Validate hierarchical round path format"""
        import re

        if not re.match(r"^(\d+)(\.(\d+))*$", v):
            raise ValueError(f"Invalid round path format: {v}")
        return v


class DialogueHistory(BaseSchema):
    """Dialogue history for a session"""

    session: ConversationSessionResponse = Field(..., description="Session information")
    rounds: list[ConversationRoundResponse] = Field(
        default_factory=list, description="Conversation rounds in chronological order"
    )
    total_tokens_in: int = Field(0, ge=0, description="Total input tokens")
    total_tokens_out: int = Field(0, ge=0, description="Total output tokens")
    total_cost: Decimal = Field(Decimal("0.0"), ge=0, description="Total cost")

    @model_validator(mode="after")
    def calculate_totals(self):
        """Calculate total metrics from rounds"""
        self.total_tokens_in = sum(r.tokens_in or 0 for r in self.rounds)
        self.total_tokens_out = sum(r.tokens_out or 0 for r in self.rounds)
        self.total_cost = Decimal(sum(r.cost or Decimal("0.0") for r in self.rounds))
        return self


class DialogueCache(BaseSchema):
    """Cached dialogue session data"""

    session_id: UUID = Field(..., description="Session ID")
    scope_type: ScopeType = Field(..., description="Dialogue scope type")
    scope_id: str = Field(..., description="Business entity ID")
    status: SessionStatus = Field(..., description="Session status")
    state: dict[str, Any] = Field(..., description="Session state")
    last_round_path: str | None = Field(None, description="Path of the last round")
    ttl_seconds: int = Field(2592000, ge=0, description="Cache TTL (default 30 days)")

    @property
    def cache_key(self) -> str:
        """Generate Redis cache key"""
        return f"dialogue:session:{self.session_id}"
