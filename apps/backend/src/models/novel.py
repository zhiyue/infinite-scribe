"""
小说相关的 SQLAlchemy ORM 模型
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.sql.base import Base
from src.schemas.enums import NovelStatus


class Novel(Base):
    """小说表 - 存储每个独立小说项目的核心元数据"""

    __tablename__ = "novels"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="小说唯一标识符，自动生成的UUID"
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户ID，外键关联users表"
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="小说标题，必填，最长255个字符")
    theme: Mapped[str | None] = mapped_column(Text, comment='小说主题描述，如"科幻冒险"、"都市言情"等')
    writing_style: Mapped[str | None] = mapped_column(Text, comment='写作风格描述，如"幽默诙谐"、"严肃写实"等')
    status: Mapped[NovelStatus] = mapped_column(
        SQLEnum(NovelStatus), nullable=False, default=NovelStatus.GENESIS, comment="小说生成状态，使用novel_status枚举"
    )
    target_chapters: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="目标章节数，用户设定的计划章节总数"
    )
    completed_chapters: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="已完成章节数，系统自动统计"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="乐观锁版本号，用于并发控制")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间，带时区的时间戳"
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="最后更新时间，通过触发器自动维护",
    )

    # 关系
    user = relationship("User", back_populates="novels")
    chapters = relationship("Chapter", back_populates="novel", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="novel", cascade="all, delete-orphan")
    worldview_entries = relationship("WorldviewEntry", back_populates="novel", cascade="all, delete-orphan")
    story_arcs = relationship("StoryArc", back_populates="novel", cascade="all, delete-orphan")
    # removed legacy relationship to GenesisSession (deleted)
