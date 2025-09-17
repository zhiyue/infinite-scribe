"""Pydantic schemas for Genesis stage session association operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.enums import StageSessionStatus


class CreateStageSessionRequest(BaseModel):
    """Request schema for creating a stage session association."""

    stage_id: UUID = Field(..., description="Stage record ID")
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