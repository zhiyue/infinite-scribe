"""
Kafka event schemas

All event models for inter-agent communication via Kafka.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """事件模型基类"""

    event_id: UUID = Field(..., description="事件唯一标识")
    event_type: str = Field(..., description="事件类型")
    timestamp: datetime = Field(..., description="事件时间戳")
    source_agent: str = Field(..., description="发送事件的Agent")
    novel_id: UUID = Field(..., description="相关小说ID")
    correlation_id: UUID | None = Field(None, description="关联ID用于追踪相关事件")

    model_config = {"validate_assignment": True}


# TODO: Task 3 - 在此文件中定义Kafka事件Schema
# 事件类型将在后续tasks中实现:
# - NovelCreatedEvent
# - GenesisStepCompletedEvent
# - CharacterCreatedEvent
# - WorldviewUpdatedEvent
# - ChapterGeneratedEvent
