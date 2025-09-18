"""Pydantic schemas for Genesis stage record operations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, model_validator

from src.schemas.enums import GenesisStage, StageStatus

from .stage_config_schemas import validate_stage_config


class CreateStageRequest(BaseModel):
    """Request schema for creating a Genesis stage record."""

    stage: GenesisStage = Field(..., description="Stage type")
    config: dict[str, Any] | None = Field(default=None, description="Stage configuration")
    iteration_count: int = Field(default=0, description="Iteration count for repeated stages")

    @model_validator(mode="after")
    def validate_config_for_stage(self):
        """验证配置是否符合阶段要求"""
        if self.config is not None and self.stage != GenesisStage.FINISHED:
            try:
                validated = validate_stage_config(self.stage, self.config)
                self.config = validated.model_dump()
            except (ValidationError, ValueError) as exc:
                raise ValueError(f"Invalid config for stage {self.stage.value}: {exc!s}") from exc
        return self


class UpdateStageRequest(BaseModel):
    """Request schema for updating a Genesis stage record."""

    status: StageStatus | None = Field(default=None, description="New stage status")
    config: dict[str, Any] | None = Field(default=None, description="New stage configuration")
    result: dict[str, Any] | None = Field(default=None, description="Stage result data")
    metrics: dict[str, Any] | None = Field(default=None, description="Stage metrics")

    def validate_with_stage(self, stage: GenesisStage):
        """在已知阶段类型的情况下验证配置"""
        if self.config is not None and stage != GenesisStage.FINISHED:
            try:
                validated = validate_stage_config(stage, self.config)
                self.config = validated.model_dump()
            except (ValidationError, ValueError) as exc:
                raise ValueError(f"Invalid config for stage {stage.value}: {exc!s}") from exc


class StageResponse(BaseModel):
    """Response schema for Genesis stage record operations."""

    id: UUID = Field(..., description="Stage record ID")
    flow_id: UUID = Field(..., description="Genesis flow ID")
    stage: GenesisStage = Field(..., description="Stage type")
    status: StageStatus = Field(..., description="Stage status")
    config: dict[str, Any] | None = Field(..., description="Stage configuration")
    result: dict[str, Any] | None = Field(..., description="Stage result data")
    iteration_count: int = Field(..., description="Iteration count")
    metrics: dict[str, Any] | None = Field(..., description="Stage metrics")
    started_at: datetime | None = Field(..., description="Stage start timestamp")
    completed_at: datetime | None = Field(..., description="Stage completion timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
