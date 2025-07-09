"""
工作流创建相关的 Pydantic 模型
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from src.schemas.base import BaseSchema
from src.schemas.enums import CommandStatus, HandleStatus, OutboxStatus, TaskStatus


class CommandInboxCreate(BaseSchema):
    """命令收件箱创建请求"""

    session_id: UUID = Field(..., description="关联的会话ID")
    command_type: str = Field(..., description="命令类型")
    idempotency_key: str = Field(..., description="用于防止重复的幂等键")
    payload: dict[str, Any] | None = Field(None, description="命令的参数")
    status: CommandStatus = Field(default=CommandStatus.RECEIVED, description="命令处理状态")
    error_message: str | None = Field(None, description="处理失败时的错误信息")
    retry_count: int = Field(default=0, ge=0, description="重试次数")


class AsyncTaskCreate(BaseSchema):
    """异步任务创建请求"""

    task_type: str = Field(..., description="任务类型")
    triggered_by_command_id: UUID | None = Field(None, description="触发此任务的命令ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务执行状态")
    progress: Decimal = Field(default=Decimal("0.00"), description="任务进度(0.00 - 100.00)")
    input_data: dict[str, Any] | None = Field(None, description="任务的输入参数")
    result_data: dict[str, Any] | None = Field(None, description="任务成功后的结果")
    error_data: dict[str, Any] | None = Field(None, description="任务失败时的错误信息")
    execution_node: str | None = Field(None, description="执行此任务的节点或服务实例标识")
    retry_count: int = Field(default=0, ge=0, description="重试次数")
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")
    started_at: datetime | None = Field(None, description="任务开始执行时间")
    completed_at: datetime | None = Field(None, description="任务完成时间")


class EventOutboxCreate(BaseSchema):
    """事件发件箱创建请求"""

    topic: str = Field(..., description="目标Kafka主题")
    key: str | None = Field(None, description="Kafka消息的Key")
    partition_key: str | None = Field(None, description="分区键")
    payload: dict[str, Any] = Field(..., description="消息的完整内容")
    headers: dict[str, Any] | None = Field(None, description="消息头信息")
    status: OutboxStatus = Field(default=OutboxStatus.PENDING, description="消息发送状态")
    retry_count: int = Field(default=0, ge=0, description="重试次数")
    max_retries: int = Field(default=5, ge=0, description="最大重试次数")
    last_error: str | None = Field(None, description="最后一次发送失败的错误信息")
    scheduled_at: datetime | None = Field(None, description="计划发送时间")
    sent_at: datetime | None = Field(None, description="实际发送成功时间")


class FlowResumeHandleCreate(BaseSchema):
    """工作流恢复句柄创建请求"""

    correlation_id: str = Field(..., description="用于查找的关联ID")
    flow_run_id: str | None = Field(None, description="Prefect工作流运行ID")
    task_name: str | None = Field(None, description="暂停的任务名称")
    resume_handle: dict[str, Any] = Field(..., description="Prefect提供的用于恢复的完整JSON对象")
    status: HandleStatus = Field(default=HandleStatus.PENDING_PAUSE, description="回调句柄的状态")
    resume_payload: dict[str, Any] | None = Field(None, description="用于存储提前到达的恢复数据")
    timeout_seconds: int | None = Field(None, gt=0, description="句柄超时时间(秒)")
    context_data: dict[str, Any] | None = Field(None, description="额外的上下文信息")
    expires_at: datetime | None = Field(None, description="过期时间")
    resumed_at: datetime | None = Field(None, description="实际恢复时间")
