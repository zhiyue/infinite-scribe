"""
工作流更新相关的 Pydantic 模型
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, model_validator

from src.schemas.base import BaseSchema
from src.schemas.enums import CommandStatus, HandleStatus, OutboxStatus, TaskStatus


class CommandInboxUpdate(BaseSchema):
    """命令收件箱更新请求 - 所有字段可选"""

    status: CommandStatus | None = Field(None, description="命令处理状态")
    error_message: str | None = Field(None, description="处理失败时的错误信息")
    retry_count: int | None = Field(None, ge=0, description="重试次数")

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """确保至少有一个字段被设置"""
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("至少需要提供一个字段进行更新")
        return self


class AsyncTaskUpdate(BaseSchema):
    """异步任务更新请求 - 所有字段可选"""

    status: TaskStatus | None = Field(None, description="任务执行状态")
    progress: Decimal | None = Field(None, description="任务进度(0.00 - 100.00)")
    result_data: dict[str, Any] | None = Field(None, description="任务成功后的结果")
    error_data: dict[str, Any] | None = Field(None, description="任务失败时的错误信息")
    execution_node: str | None = Field(None, description="执行此任务的节点或服务实例标识")
    retry_count: int | None = Field(None, ge=0, description="重试次数")
    started_at: datetime | None = Field(None, description="任务开始执行时间")
    completed_at: datetime | None = Field(None, description="任务完成时间")

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """确保至少有一个字段被设置"""
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("至少需要提供一个字段进行更新")
        return self


class EventOutboxUpdate(BaseSchema):
    """事件发件箱更新请求 - 所有字段可选"""

    status: OutboxStatus | None = Field(None, description="消息发送状态")
    retry_count: int | None = Field(None, ge=0, description="重试次数")
    last_error: str | None = Field(None, description="最后一次发送失败的错误信息")
    sent_at: datetime | None = Field(None, description="实际发送成功时间")

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """确保至少有一个字段被设置"""
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("至少需要提供一个字段进行更新")
        return self


class FlowResumeHandleUpdate(BaseSchema):
    """工作流恢复句柄更新请求 - 所有字段可选"""

    status: HandleStatus | None = Field(None, description="回调句柄的状态")
    resume_payload: dict[str, Any] | None = Field(None, description="用于存储提前到达的恢复数据")
    resumed_at: datetime | None = Field(None, description="实际恢复时间")

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """确保至少有一个字段被设置"""
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("至少需要提供一个字段进行更新")
        return self
