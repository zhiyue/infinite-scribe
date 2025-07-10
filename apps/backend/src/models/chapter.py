"""
章节相关的 SQLAlchemy ORM 模型
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.sql.base import Base
from src.schemas.enums import AgentType, ChapterStatus

if TYPE_CHECKING:
    from src.models.novel import Novel


class Chapter(Base):
    """章节元数据表 - 存储章节的元数据,与具体的版本内容分离"""

    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("novel_id", "chapter_number"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="章节唯一标识符，自动生成的UUID"
    )
    novel_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("novels.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属小说ID，外键关联novels表，级联删除",
    )
    chapter_number: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="章节序号，从1开始递增，同一小说内唯一"
    )
    title: Mapped[str | None] = mapped_column(String(255), comment="章节标题，可选字段")
    status: Mapped[ChapterStatus] = mapped_column(
        SQLEnum(ChapterStatus),
        nullable=False,
        default=ChapterStatus.DRAFT,
        comment="章节当前状态，使用chapter_status枚举",
    )
    published_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), comment="指向当前已发布版本的ID，外键将在chapter_versions表创建后添加"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="乐观锁版本号，用于并发控制")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="章节创建时间"
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="章节最后更新时间",
    )

    # 关系
    novel: Mapped[Novel] = relationship(back_populates="chapters")
    versions: Mapped[list[ChapterVersion]] = relationship(
        back_populates="chapter", foreign_keys="ChapterVersion.chapter_id"
    )
    published_version: Mapped[ChapterVersion | None] = relationship(
        primaryjoin="Chapter.published_version_id == ChapterVersion.id",
        foreign_keys=[published_version_id],
        post_update=True,
    )
    reviews: Mapped[list[Review]] = relationship(back_populates="chapter", cascade="all, delete-orphan")


class ChapterVersion(Base):
    """章节版本表 - 存储一个章节的每一次具体内容的迭代版本,实现版本控制"""

    __tablename__ = "chapter_versions"
    __table_args__ = (UniqueConstraint("chapter_id", "version_number"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="章节版本的唯一标识符"
    )
    chapter_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的章节ID，外键关联chapters表",
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, comment="版本号，从1开始递增，同一章节内唯一")
    content_url: Mapped[str] = mapped_column(Text, nullable=False, comment="指向MinIO中该版本内容的URL")
    word_count: Mapped[int | None] = mapped_column(Integer, comment="该版本的字数统计")
    created_by_agent_type: Mapped[AgentType] = mapped_column(
        SQLEnum(AgentType), nullable=False, comment="创建此版本的AI智能体类型"
    )
    change_reason: Mapped[str | None] = mapped_column(Text, comment='修改原因说明，如"根据评论家意见修改"')
    parent_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("chapter_versions.id", ondelete="SET NULL"),
        comment="指向上一个版本的ID，形成版本链",
    )
    version_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, comment="存储与此版本相关的额外元数据，JSONB格式"
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="版本创建时间"
    )

    # 关系
    chapter: Mapped[Chapter] = relationship(back_populates="versions", foreign_keys=[chapter_id])
    parent_version: Mapped[ChapterVersion | None] = relationship(remote_side=[id])
    reviews: Mapped[list[Review]] = relationship(back_populates="chapter_version", cascade="all, delete-orphan")


class Review(Base):
    """评审记录表 - 记录每一次对章节草稿的评审结果"""

    __tablename__ = "reviews"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="评审记录唯一标识符"
    )
    chapter_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        comment="被评审的章节ID，外键关联chapters表",
    )
    chapter_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("chapter_versions.id", ondelete="CASCADE"),
        nullable=False,
        comment="评审针对的具体章节版本ID，外键关联chapter_versions表",
    )
    agent_type: Mapped[AgentType] = mapped_column(SQLEnum(AgentType), nullable=False, comment="执行评审的AI智能体类型")
    review_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="评审类型，如CRITIC(评论家审查)、FACT_CHECK(事实核查)"
    )
    score: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), comment="评分，范围0.0-10.0，保留一位小数")
    comment: Mapped[str | None] = mapped_column(Text, comment="评审意见和建议的详细文本")
    is_consistent: Mapped[bool | None] = mapped_column(Boolean, comment="是否与小说设定一致，用于事实核查")
    issues_found: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), comment='发现的问题列表，如["时间线冲突", "角色性格不一致"]'
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="评审创建时间，不会更新"
    )

    # 关系
    chapter: Mapped[Chapter] = relationship(back_populates="reviews")
    chapter_version: Mapped[ChapterVersion] = relationship(back_populates="reviews")
