"""Pydantic schemas for Genesis stage session association operations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.enums import GenesisStage, StageSessionStatus, StageStatus
from src.schemas.novel.dialogue import SessionStatus


class CreateStageSessionRequest(BaseModel):
    """Request schema for creating a stage session association."""

    session_id: UUID | None = Field(default=None, description="Existing session ID to bind (optional)")
    novel_id: UUID = Field(..., description="Novel ID for scope validation")
    is_primary: bool = Field(default=False, description="Whether this should be the primary session")
    session_kind: str | None = Field(default=None, description="Session classification")


class UpdateStageSessionRequest(BaseModel):
    """Request schema for updating a stage session association."""

    status: StageSessionStatus | None = Field(default=None, description="New association status")
    is_primary: bool | None = Field(default=None, description="Whether this should be the primary session")
    session_kind: str | None = Field(default=None, description="Session classification")


class StageSessionResponse(BaseModel):
    """Response schema for stage session association operations."""

    id: UUID = Field(..., description="Association ID")
    stage_id: UUID = Field(..., description="Stage record ID")
    session_id: UUID = Field(..., description="Conversation session ID")
    status: StageSessionStatus = Field(..., description="Association status")
    is_primary: bool = Field(..., description="Whether this is the primary session")
    session_kind: str | None = Field(..., description="Session classification")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class SessionInfo(BaseModel):
    """Simplified session information for aggregated view."""

    id: UUID = Field(..., description="Conversation session ID")
    scope_type: str = Field(..., description="Session scope type")
    scope_id: str = Field(..., description="Session scope ID")
    status: SessionStatus = Field(..., description="Session status")
    version: int = Field(..., description="Session version")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Session last update timestamp")


class StageInfo(BaseModel):
    """Simplified stage information for aggregated view."""

    id: UUID = Field(..., description="Stage record ID")
    flow_id: UUID = Field(..., description="Genesis flow ID")
    stage: GenesisStage = Field(..., description="Stage type")
    status: StageStatus = Field(..., description="Stage status")
    config: dict[str, Any] | None = Field(None, description="Stage configuration")
    result: dict[str, Any] | None = Field(None, description="Stage result data")
    iteration_count: int = Field(..., description="Iteration count")
    metrics: dict[str, Any] | None = Field(None, description="Stage metrics")
    started_at: datetime | None = Field(None, description="Stage start timestamp")
    completed_at: datetime | None = Field(None, description="Stage completion timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class StageWithActiveSessionResponse(BaseModel):
    """Aggregated response containing stage info with its active session."""

    stage: StageInfo = Field(..., description="Stage information")
    active_session: SessionInfo | None = Field(None, description="Active session for this stage")
    association: StageSessionResponse | None = Field(None, description="Stage-session association details")

    class Config:
        from_attributes = True
