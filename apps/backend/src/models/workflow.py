"""
工作流和任务相关的 SQLAlchemy ORM 模型
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.sql.base import Base
from src.schemas.enums import CommandStatus, HandleStatus, OutboxStatus, TaskStatus


class CommandInbox(Base):
    """命令收件箱表 - 接收和存储待处理的命令,用于CQRS架构的命令侧"""

    __tablename__ = "command_inbox"
    __table_args__ = (
        Index("idx_command_inbox_unique_pending_command", "session_id", "command_type", unique=True),
        UniqueConstraint("idempotency_key"),
        CheckConstraint("retry_count >= 0", name="check_retry_count_non_negative"),
        CheckConstraint(
            "(status != 'FAILED') OR (status = 'FAILED' AND error_message IS NOT NULL)",
            name="check_failed_has_error_message",
        ),
        Index("idx_command_inbox_session_id", "session_id"),
        Index("idx_command_inbox_status", "status"),
        Index("idx_command_inbox_command_type", "command_type"),
        Index("idx_command_inbox_created_at", "created_at"),
        Index("idx_command_inbox_session_status", "session_id", "status"),
        Index("idx_command_inbox_status_created", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="命令唯一标识符")
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, comment="会话ID，关联到genesis_sessions或其他业务会话"
    )
    command_type: Mapped[str] = mapped_column(
        Text, nullable=False, comment='命令类型，如"ConfirmStoryConception"、"GenerateWorldview"'
    )
    idempotency_key: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, comment="幂等键，确保同一命令不会被重复处理"
    )
    payload: Mapped[dict | None] = mapped_column(JSONB, comment="命令载荷，包含命令执行所需的所有数据")
    status: Mapped[CommandStatus] = mapped_column(
        SQLEnum(CommandStatus),
        nullable=False,
        default=CommandStatus.RECEIVED,
        comment="命令状态，使用command_status枚举",
    )
    error_message: Mapped[str | None] = mapped_column(Text, comment="错误信息，当状态为FAILED时必填")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="重试次数，用于失败重试机制")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="命令接收时间"
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="最后更新时间"
    )

    # 关系
    async_tasks: Mapped[list[AsyncTask]] = relationship(back_populates="command")


class AsyncTask(Base):
    """异步任务表 - 跟踪和管理系统中的所有异步任务执行"""

    __tablename__ = "async_tasks"
    __table_args__ = (
        CheckConstraint("progress >= 0.0 AND progress <= 100.0", name="check_progress_range"),
        CheckConstraint("retry_count >= 0 AND retry_count <= max_retries", name="check_retry_count_valid"),
        CheckConstraint("max_retries >= 0", name="check_max_retries_non_negative"),
        CheckConstraint(
            "(status NOT IN ('COMPLETED', 'FAILED')) OR (status IN ('COMPLETED', 'FAILED') AND completed_at IS NOT NULL)",
            name="check_completed_has_timestamp",
        ),
        CheckConstraint(
            "(status != 'RUNNING') OR (status = 'RUNNING' AND started_at IS NOT NULL)",
            name="check_running_has_started",
        ),
        CheckConstraint(
            "(status != 'FAILED') OR (status = 'FAILED' AND error_data IS NOT NULL)", name="check_failed_has_error"
        ),
        CheckConstraint(
            "(status != 'COMPLETED') OR (status = 'COMPLETED' AND result_data IS NOT NULL)",
            name="check_completed_has_result",
        ),
        Index("idx_async_tasks_status", "status"),
        Index("idx_async_tasks_task_type", "task_type"),
        Index("idx_async_tasks_created_at", "created_at"),
        Index("idx_async_tasks_command_id", "triggered_by_command_id"),
        Index("idx_async_tasks_status_type", "status", "task_type"),
        Index("idx_async_tasks_status_created", "status", "created_at"),
        Index("idx_async_tasks_type_created", "task_type", "created_at"),
        Index("idx_async_tasks_execution_node", "execution_node"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="任务唯一标识符")
    task_type: Mapped[str] = mapped_column(
        Text, nullable=False, comment='任务类型，如"GenerateChapter"、"AnalyzeWorldview"'
    )
    triggered_by_command_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("command_inbox.id", ondelete="SET NULL"),
        comment="触发此任务的命令ID，外键关联command_inbox表",
    )
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING, comment="任务状态，使用task_status枚举"
    )
    progress: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00"), comment="任务进度百分比，0.00-100.00"
    )
    input_data: Mapped[dict | None] = mapped_column(JSONB, comment="任务输入数据，JSON格式")
    result_data: Mapped[dict | None] = mapped_column(JSONB, comment="任务执行结果，完成时必填")
    error_data: Mapped[dict | None] = mapped_column(JSONB, comment="错误信息详情，失败时必填")
    execution_node: Mapped[str | None] = mapped_column(Text, comment="执行任务的节点标识，用于分布式任务调度")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="当前重试次数")
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3, comment="最大重试次数，默认3次")
    started_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), comment="任务开始执行时间，状态为RUNNING时必填"
    )
    completed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), comment="任务完成时间，状态为COMPLETED或FAILED时必填"
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="任务创建时间"
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="最后更新时间"
    )

    # 关系
    command: Mapped[CommandInbox | None] = relationship(back_populates="async_tasks")


class EventOutbox(Base):
    """事件发件箱表 - 确保事件可靠发布到消息队列的事务性发件箱模式实现"""

    __tablename__ = "event_outbox"
    __table_args__ = (
        CheckConstraint("retry_count >= 0 AND retry_count <= max_retries", name="check_retry_count_valid"),
        CheckConstraint("max_retries >= 0", name="check_max_retries_non_negative"),
        CheckConstraint(
            "(status != 'SENT') OR (status = 'SENT' AND sent_at IS NOT NULL)", name="check_sent_has_timestamp"
        ),
        CheckConstraint("scheduled_at IS NULL OR scheduled_at >= created_at", name="check_scheduled_at_future"),
        Index("idx_event_outbox_status", "status"),
        Index("idx_event_outbox_topic", "topic"),
        Index("idx_event_outbox_created_at", "created_at"),
        Index("idx_event_outbox_pending_scheduled", "status", "scheduled_at"),
        Index("idx_event_outbox_retry_count", "retry_count"),
        Index("idx_event_outbox_topic_status", "topic", "status"),
        Index("idx_event_outbox_status_created", "status", "created_at"),
        Index("idx_event_outbox_key", "key"),
        Index("idx_event_outbox_partition_key", "partition_key"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="消息唯一标识符")
    topic: Mapped[str] = mapped_column(
        Text, nullable=False, comment='消息主题/队列名称，如"novel.events"、"chapter.updates"'
    )
    key: Mapped[str | None] = mapped_column(Text, comment="消息键，用于消息分区和顺序保证")
    partition_key: Mapped[str | None] = mapped_column(Text, comment="分区键，用于Kafka等消息系统的分区路由")
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, comment="消息载荷，包含事件的完整数据")
    headers: Mapped[dict | None] = mapped_column(JSONB, comment="消息头，包含元数据如事件类型、版本、追踪ID等")
    status: Mapped[OutboxStatus] = mapped_column(
        SQLEnum(OutboxStatus), nullable=False, default=OutboxStatus.PENDING, comment="消息状态，使用outbox_status枚举"
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="当前重试次数")
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=5, comment="最大重试次数，默认5次")
    last_error: Mapped[str | None] = mapped_column(Text, comment="最后一次发送失败的错误信息")
    scheduled_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), comment="计划发送时间，用于延迟消息")
    sent_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), comment="实际发送成功时间，状态为SENT时必填"
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="消息创建时间"
    )


class FlowResumeHandle(Base):
    """工作流恢复句柄表 - 支持长时间运行的工作流暂停和恢复机制"""

    __tablename__ = "flow_resume_handles"
    __table_args__ = (
        Index("idx_flow_resume_handles_unique_correlation", "correlation_id", unique=True),
        CheckConstraint("timeout_seconds IS NULL OR timeout_seconds > 0", name="check_timeout_positive"),
        CheckConstraint("expires_at IS NULL OR expires_at > created_at", name="check_expires_after_created"),
        CheckConstraint(
            "(status != 'RESUMED') OR (status = 'RESUMED' AND resumed_at IS NOT NULL)",
            name="check_resumed_has_timestamp",
        ),
        CheckConstraint(
            "(status NOT IN ('PAUSED', 'RESUMED')) OR (status IN ('PAUSED', 'RESUMED') AND resume_handle IS NOT NULL)",
            name="check_paused_has_handle",
        ),
        Index("idx_flow_resume_handles_correlation_id", "correlation_id"),
        Index("idx_flow_resume_handles_status", "status"),
        Index("idx_flow_resume_handles_flow_run_id", "flow_run_id"),
        Index("idx_flow_resume_handles_expires_at", "expires_at"),
        Index("idx_flow_resume_handles_status_expires", "status", "expires_at"),
        Index("idx_flow_resume_handles_correlation_status", "correlation_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="句柄唯一标识符")
    correlation_id: Mapped[str] = mapped_column(Text, nullable=False, comment="关联ID，唯一标识一个可恢复的工作流实例")
    flow_run_id: Mapped[str | None] = mapped_column(Text, comment="工作流运行ID，关联到具体的工作流执行实例")
    task_name: Mapped[str | None] = mapped_column(Text, comment='暂停的任务名称，如"WaitForUserConfirmation"')
    resume_handle: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="恢复句柄数据，包含恢复工作流所需的状态信息"
    )
    status: Mapped[HandleStatus] = mapped_column(
        SQLEnum(HandleStatus),
        nullable=False,
        default=HandleStatus.PENDING_PAUSE,
        comment="句柄状态，使用handle_status枚举",
    )
    resume_payload: Mapped[dict | None] = mapped_column(JSONB, comment="恢复时的载荷数据，包含用户输入或外部事件数据")
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, comment="超时时间（秒），超时后工作流将自动恢复或失败")
    context_data: Mapped[dict | None] = mapped_column(JSONB, comment="上下文数据，存储工作流暂停时的业务上下文")
    expires_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), comment="句柄过期时间，过期后不能再恢复"
    )
    resumed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), comment="实际恢复时间，状态为RESUMED时必填"
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="句柄创建时间"
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="最后更新时间"
    )
