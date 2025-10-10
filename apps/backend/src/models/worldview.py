"""
世界观相关的 SQLAlchemy ORM 模型
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.sql.base import Base
from src.schemas.enums import WorldviewEntryType

if TYPE_CHECKING:
    from src.models.novel import Novel


class WorldviewEntry(Base):
    """世界观条目表 - 存储世界观中的所有设定条目,如地点、组织、物品等"""

    __tablename__ = "worldview_entries"
    __table_args__ = (UniqueConstraint("novel_id", "name", "entry_type"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="条目唯一标识符，与Neo4j图数据库中节点的app_id属性对应",
    )
    novel_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("novels.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属小说ID，外键关联novels表",
    )
    entry_type: Mapped[WorldviewEntryType] = mapped_column(
        SQLEnum(WorldviewEntryType), nullable=False, comment="条目类型，使用worldview_entry_type枚举"
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment='条目名称，如"魔法学院"、"时空传送门"等，同一小说内按类型唯一'
    )
    description: Mapped[str | None] = mapped_column(Text, comment="条目详细描述，包含其特征、作用、历史等信息")
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), comment='标签数组，用于分类和快速检索，如["魔法", "禁地", "古代遗迹"]'
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="乐观锁版本号，用于并发控制")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="条目创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="条目最后更新时间",
    )

    # 关系
    novel: Mapped[Novel] = relationship(back_populates="worldview_entries")


class StoryArc(Base):
    """故事弧表 - 存储主要的情节线或故事阶段的规划"""

    __tablename__ = "story_arcs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="故事弧唯一标识符")
    novel_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("novels.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属小说ID，外键关联novels表",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment='故事弧标题，如"主角觉醒篇"、"魔王讨伐篇"')
    summary: Mapped[str | None] = mapped_column(Text, comment="故事弧概要，描述这条线索的主要内容和发展")
    start_chapter_number: Mapped[int | None] = mapped_column(Integer, comment="故事弧开始的章节号")
    end_chapter_number: Mapped[int | None] = mapped_column(Integer, comment="故事弧结束的章节号")
    status: Mapped[str | None] = mapped_column(
        String(50), default="PLANNED", comment="故事弧状态，如PLANNED(已规划)、ACTIVE(进行中)、COMPLETED(已完成)"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="乐观锁版本号，用于并发控制")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="故事弧创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="故事弧最后更新时间",
    )

    # 关系
    novel: Mapped[Novel] = relationship(back_populates="story_arcs")
