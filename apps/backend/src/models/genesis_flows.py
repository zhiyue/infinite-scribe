"""Genesis流程解耦模型定义

Genesis阶段与对话会话解耦后的专用模型，管理Genesis业务状态。
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.schemas.enums import GenesisStage, GenesisStatus, StageSessionStatus, StageStatus


class GenesisFlow(Base):
    """创世流程实例表 - 管理某部小说的总进度和全局状态"""

    __tablename__ = "genesis_flows"
    __table_args__ = (
        UniqueConstraint("novel_id", name="ux_genesis_flows_novel"),
        Index("idx_genesis_flows_novel_status", "novel_id", "status"),
        Index("idx_genesis_flows_current_stage", "current_stage"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="流程实例唯一标识符"
    )
    novel_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("novels.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属小说ID，外键关联novels表，级联删除",
    )
    status: Mapped[GenesisStatus] = mapped_column(
        SQLEnum(GenesisStatus), nullable=False, comment="流程状态：IN_PROGRESS/COMPLETED/ABANDONED/PAUSED"
    )
    current_stage: Mapped[GenesisStage | None] = mapped_column(
        SQLEnum(GenesisStage), comment="当前所在阶段：INITIAL_PROMPT/WORLDVIEW/CHARACTERS/PLOT_OUTLINE/FINISHED"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="流程版本号，用于乐观并发控制")
    state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, comment="全局聚合与跨阶段元数据，JSON格式存储")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="流程创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="流程最后更新时间",
    )

    # 关系
    stage_records: Mapped[list["GenesisStageRecord"]] = relationship(
        back_populates="flow", cascade="all, delete-orphan"
    )


class GenesisStageRecord(Base):
    """阶段业务记录表 - 管理每个Genesis阶段的配置、结果、指标、状态和迭代"""

    __tablename__ = "genesis_stage_records"
    __table_args__ = (
        Index("idx_stage_records_flow_stage", "flow_id", "stage", "created_at"),
        Index("idx_stage_records_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="阶段记录唯一标识符"
    )
    flow_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("genesis_flows.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属流程ID，外键关联genesis_flows表",
    )
    stage: Mapped[GenesisStage] = mapped_column(
        SQLEnum(GenesisStage), nullable=False, comment="阶段类型：INITIAL_PROMPT/WORLDVIEW/CHARACTERS/PLOT_OUTLINE"
    )
    status: Mapped[StageStatus] = mapped_column(
        SQLEnum(StageStatus), nullable=False, comment="阶段状态：RUNNING/COMPLETED/FAILED/PAUSED"
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, comment="阶段参数与用户选择，JSON格式存储")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, comment="阶段产出索引/摘要：如世界观条目/角色ID列表等")
    iteration_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="迭代次数，支持阶段重复执行"
    )
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, comment="阶段指标：tokens/cost/latency等聚合数据")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="阶段开始时间")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="阶段完成时间")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="记录创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="记录最后更新时间",
    )

    # 关系
    flow: Mapped[GenesisFlow] = relationship(back_populates="stage_records")
    stage_sessions: Mapped[list["GenesisStageSession"]] = relationship(
        back_populates="stage_record", cascade="all, delete-orphan"
    )


class GenesisStageSession(Base):
    """阶段会话关联表 - 管理阶段与对话会话的多对多关系，支持主会话标记"""

    __tablename__ = "genesis_stage_sessions"
    __table_args__ = (
        UniqueConstraint("stage_id", "session_id", name="ux_stage_session"),
        # 可选：仅允许一个主会话（如果需要严格唯一性）
        # UniqueConstraint("stage_id", name="ux_stage_primary", where="is_primary = true"),
        Index("idx_stage_sessions_stage", "stage_id"),
        Index("idx_stage_sessions_session", "session_id"),
        Index("idx_stage_sessions_primary", "stage_id", "is_primary"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="关联记录唯一标识符"
    )
    stage_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("genesis_stage_records.id", ondelete="CASCADE"),
        nullable=False,
        comment="阶段记录ID，外键关联genesis_stage_records表",
    )
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        comment="对话会话ID，外键关联conversation_sessions表",
    )
    status: Mapped[StageSessionStatus] = mapped_column(
        SQLEnum(StageSessionStatus),
        nullable=False,
        default=StageSessionStatus.ACTIVE,
        comment="关联状态：ACTIVE/ARCHIVED/CLOSED",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否为主会话，用于默认展示"
    )
    session_kind: Mapped[str | None] = mapped_column(
        String(64), comment="会话类别：user_interaction/review/agent_autonomous等"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="关联创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="关联最后更新时间",
    )

    # 关系
    stage_record: Mapped[GenesisStageRecord] = relationship(back_populates="stage_sessions")
    # 注意：这里不直接定义与ConversationSession的关系，避免循环导入
    # session: Mapped["ConversationSession"] = relationship()
