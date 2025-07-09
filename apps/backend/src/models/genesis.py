"""
创世流程相关的 SQLAlchemy ORM 模型
"""

from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.sql.base import Base
from src.schemas.enums import GenesisStage, GenesisStatus


class GenesisSession(Base):
    """创世会话表 - 作为创世流程的"状态快照",用于高效查询当前流程的状态"""

    __tablename__ = "genesis_sessions"
    __table_args__ = (
        CheckConstraint(
            """
            (current_stage = 'CONCEPT_SELECTION' AND status = 'IN_PROGRESS') OR
            (current_stage = 'STORY_CONCEPTION' AND status = 'IN_PROGRESS') OR
            (current_stage = 'WORLDVIEW' AND status = 'IN_PROGRESS') OR
            (current_stage = 'CHARACTERS' AND status = 'IN_PROGRESS') OR
            (current_stage = 'PLOT_OUTLINE' AND status = 'IN_PROGRESS') OR
            (current_stage = 'FINISHED' AND status IN ('COMPLETED', 'ABANDONED'))
            """,
            name="check_genesis_stage_progression",
        ),
        CheckConstraint(
            "(status != 'COMPLETED') OR (status = 'COMPLETED' AND novel_id IS NOT NULL)",
            name="check_completed_has_novel",
        ),
        Index("idx_genesis_sessions_user_id", "user_id"),
        Index("idx_genesis_sessions_status", "status"),
        Index("idx_genesis_sessions_current_stage", "current_stage"),
        Index("idx_genesis_sessions_novel_id", "novel_id"),
        Index("idx_genesis_sessions_user_status", "user_id", "status"),
        Index("idx_genesis_sessions_status_stage", "status", "current_stage"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="创世会话的唯一标识符")
    novel_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("novels.id", ondelete="SET NULL"),
        comment="流程完成后关联的小说ID，允许为空（流程未完成时）",
    )
    user_id = Column(PGUUID(as_uuid=True), comment="发起创世流程的用户ID，用于权限控制和用户关联")
    status = Column(
        Enum(GenesisStatus),
        nullable=False,
        default=GenesisStatus.IN_PROGRESS,
        comment="整个创世会话的状态，使用genesis_status枚举",
    )
    current_stage = Column(
        Enum(GenesisStage),
        nullable=False,
        default=GenesisStage.CONCEPT_SELECTION,
        comment="当前所处的业务阶段，使用genesis_stage枚举",
    )
    confirmed_data = Column(JSONB, comment="存储每个阶段已确认的最终数据，JSONB格式，包含各阶段的输出结果")
    version = Column(Integer, nullable=False, default=1, comment="乐观锁版本号，用于并发控制")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创世会话创建时间")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="创世会话最后更新时间",
    )

    # 关系
    novel = relationship("Novel", back_populates="genesis_sessions")


class ConceptTemplate(Base):
    """立意模板表 - 存储抽象的哲学立意供用户选择"""

    __tablename__ = "concept_templates"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="立意模板的唯一标识符")
    core_idea = Column(String(200), nullable=False, comment='核心抽象思想，如"知识与无知的深刻对立"')
    description = Column(String(800), nullable=False, comment="立意的深层含义阐述，不超过800字符")
    philosophical_depth = Column(String(1000), nullable=False, comment="哲学思辨的深度表达，探讨存在、认知、道德等层面")
    emotional_core = Column(String(500), nullable=False, comment="情感核心与内在冲突，描述人物可能面临的情感挑战")
    philosophical_category = Column(String(100), comment='哲学类别，如"存在主义"、"人道主义"、"理想主义"')
    thematic_tags = Column(
        JSONB, nullable=False, default=list, comment='主题标签，如["成长","选择","牺牲","真理"]，JSON数组格式'
    )
    complexity_level = Column(
        String(20), nullable=False, default="medium", comment="思辨复杂度：simple, medium, complex"
    )
    universal_appeal = Column(Boolean, nullable=False, default=True, comment="是否具有普遍意义，跨文化的普适性")
    cultural_specificity = Column(String(100), comment='文化特异性，如"东方哲学"、"西方哲学"、"普世价值"')
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用，用于管理可用的立意模板")
    created_by = Column(String(50), server_default="system", comment='创建者，如"system"、"admin"或具体用户')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
