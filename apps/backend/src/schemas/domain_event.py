"""
领域事件相关的 Pydantic 模型
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from src.schemas.base import BaseSchema


class DomainEventCreate(BaseSchema):
    """领域事件创建请求"""

    event_id: UUID = Field(default_factory=uuid4, description="事件的全局唯一标识符")
    correlation_id: UUID | None = Field(None, description="用于追踪一个完整的业务流程或请求链")
    causation_id: UUID | None = Field(None, description="指向触发此事件的上一个事件的event_id")
    event_type: str = Field(..., description="事件的唯一类型标识")
    event_version: int = Field(default=1, description="事件模型的版本号")
    aggregate_type: str = Field(..., description="聚合根类型")
    aggregate_id: str = Field(..., description="聚合根的ID")
    payload: dict[str, Any] | None = Field(None, description="事件的具体数据")
    metadata: dict[str, Any] | None = Field(None, description="附加元数据")


class DomainEventResponse(BaseSchema):
    """领域事件响应模型"""

    id: int = Field(..., description="自增序号, 保证严格的时间顺序")
    event_id: UUID = Field(..., description="事件的全局唯一标识符")
    correlation_id: UUID | None = Field(None, description="用于追踪一个完整的业务流程或请求链")
    causation_id: UUID | None = Field(None, description="指向触发此事件的上一个事件的event_id")
    event_type: str = Field(..., description="事件的唯一类型标识")
    event_version: int = Field(..., description="事件模型的版本号")
    aggregate_type: str = Field(..., description="聚合根类型")
    aggregate_id: str = Field(..., description="聚合根的ID")
    payload: dict[str, Any] | None = Field(None, description="事件的具体数据")
    metadata: dict[str, Any] | None = Field(None, description="附加元数据")
    created_at: datetime = Field(..., description="事件创建时间")


__all__ = ["DomainEventCreate", "DomainEventResponse"]
