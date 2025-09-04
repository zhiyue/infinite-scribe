"""
创世流程相关的 SQLAlchemy ORM 模型
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.db.sql.base import Base


class ConceptTemplate(Base):
    """立意模板表 - 存储抽象的哲学立意供用户选择"""

    __tablename__ = "concept_templates"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="立意模板的唯一标识符"
    )
    core_idea: Mapped[str] = mapped_column(
        String(200), nullable=False, comment='核心抽象思想，如"知识与无知的深刻对立"'
    )
    description: Mapped[str] = mapped_column(String(800), nullable=False, comment="立意的深层含义阐述，不超过800字符")
    philosophical_depth: Mapped[str] = mapped_column(
        String(1000), nullable=False, comment="哲学思辨的深度表达，探讨存在、认知、道德等层面"
    )
    emotional_core: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="情感核心与内在冲突，描述人物可能面临的情感挑战"
    )
    philosophical_category: Mapped[str | None] = mapped_column(
        String(100), comment='哲学类别，如"存在主义"、"人道主义"、"理想主义"'
    )
    thematic_tags: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=list, comment='主题标签，如["成长","选择","牺牲","真理"]，JSON数组格式'
    )
    complexity_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium", comment="思辨复杂度：simple, medium, complex"
    )
    universal_appeal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否具有普遍意义，跨文化的普适性"
    )
    cultural_specificity: Mapped[str | None] = mapped_column(
        String(100), comment='文化特异性，如"东方哲学"、"西方哲学"、"普世价值"'
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用，用于管理可用的立意模板"
    )
    created_by: Mapped[str | None] = mapped_column(
        String(50), server_default="system", comment='创建者，如"system"、"admin"或具体用户'
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
