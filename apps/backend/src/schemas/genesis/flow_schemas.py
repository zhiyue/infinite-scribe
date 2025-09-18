"""Pydantic schemas for Genesis flow operations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.enums import GenesisStage, GenesisStatus


class CreateFlowRequest(BaseModel):
    """Request schema for creating a Genesis flow."""

    novel_id: UUID = Field(..., description="Novel ID")
    status: GenesisStatus = Field(default=GenesisStatus.IN_PROGRESS, description="Initial flow status")
    current_stage: GenesisStage | None = Field(default=None, description="Initial stage")
    state: dict[str, Any] | None = Field(default=None, description="Initial global state")


class UpdateFlowRequest(BaseModel):
    """Request schema for updating a Genesis flow."""

    status: GenesisStatus | None = Field(default=None, description="New flow status")
    current_stage: GenesisStage | None = Field(default=None, description="New current stage")
    state: dict[str, Any] | None = Field(default=None, description="New global state")


class FlowResponse(BaseModel):
    """Response schema for Genesis flow operations."""

    id: UUID = Field(..., description="Flow ID")
    novel_id: UUID = Field(..., description="Novel ID")
    status: GenesisStatus = Field(..., description="Flow status")
    current_stage: GenesisStage | None = Field(..., description="Current stage")
    current_stage_id: UUID | None = Field(..., description="Current stage record ID")
    stage_ids: dict[GenesisStage, UUID] = Field(default_factory=dict, description="Mapping of all stages to their record IDs")
    version: int = Field(..., description="Version for optimistic concurrency control")
    state: dict[str, Any] | None = Field(..., description="Global state")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
