"""
Core business entity models.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import Field, condecimal, model_validator

from .base import BaseDBModel
from .enums import (
    AgentType,
    NovelStatus,
    ChapterStatus,
    WorldviewEntryType
)


class NovelModel(BaseDBModel):
    """小说表模型"""

    id: UUID
    title: str = Field(..., max_length=255, description="小说标题")
    theme: str | None = Field(None, description="小说主题")
    writing_style: str | None = Field(None, description="写作风格")
    status: NovelStatus = Field(default=NovelStatus.GENESIS, description="当前状态")
    target_chapters: int = Field(default=0, ge=0, description="目标章节数")
    completed_chapters: int = Field(default=0, ge=0, description="已完成章节数")
    version: int = Field(default=1, ge=1, description="乐观锁版本号")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )

    @model_validator(mode="after")
    def validate_completed_chapters(self):
        """验证已完成章节数不能超过目标章节数"""
        if self.target_chapters is not None and self.completed_chapters > self.target_chapters:
            raise ValueError("已完成章节数不能超过目标章节数")
        return self


class ChapterModel(BaseDBModel):
    """章节表模型"""

    id: UUID
    novel_id: UUID = Field(..., description="所属小说的ID")
    chapter_number: int = Field(..., ge=1, description="章节序号")
    title: str | None = Field(None, max_length=255, description="章节标题")
    status: ChapterStatus = Field(default=ChapterStatus.DRAFT, description="章节当前状态")
    published_version_id: UUID | None = Field(None, description="指向当前已发布版本的ID")
    version: int = Field(default=1, ge=1, description="乐观锁版本号")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )


class ChapterVersionModel(BaseDBModel):
    """章节版本表模型"""

    id: UUID
    chapter_id: UUID = Field(..., description="关联的章节ID")
    version_number: int = Field(..., ge=1, description="版本号, 从1开始递增")
    content_url: str = Field(..., description="指向Minio中该版本内容的URL")
    word_count: int | None = Field(None, ge=0, description="该版本的字数")
    created_by_agent_type: AgentType = Field(..., description="创建此版本的Agent类型")
    change_reason: str | None = Field(None, description="修改原因")
    parent_version_id: UUID | None = Field(None, description="指向上一个版本的ID")
    metadata: dict[str, Any] | None = Field(None, description="版本相关的额外元数据")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="版本创建时间"
    )


class CharacterModel(BaseDBModel):
    """角色表模型"""

    id: UUID
    novel_id: UUID = Field(..., description="所属小说的ID")
    name: str = Field(..., max_length=255, description="角色名称")
    role: str | None = Field(None, max_length=50, description="角色定位")
    description: str | None = Field(None, description="角色外貌、性格等简述")
    background_story: str | None = Field(None, description="角色背景故事")
    personality_traits: None | list[str] = Field(None, description="性格特点列表")
    goals: None | list[str] = Field(None, description="角色的主要目标列表")
    version: int = Field(default=1, ge=1, description="乐观锁版本号")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )


class WorldviewEntryModel(BaseDBModel):
    """世界观条目表模型"""

    id: UUID
    novel_id: UUID = Field(..., description="所属小说的ID")
    entry_type: WorldviewEntryType = Field(..., description="条目类型")
    name: str = Field(..., max_length=255, description="条目名称")
    description: str | None = Field(None, description="详细描述")
    tags: None | list[str] = Field(None, description="标签, 用于分类和检索")
    version: int = Field(default=1, ge=1, description="乐观锁版本号")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )


class StoryArcModel(BaseDBModel):
    """故事弧表模型"""

    id: UUID
    novel_id: UUID = Field(..., description="所属小说的ID")
    title: str = Field(..., max_length=255, description="故事弧标题")
    summary: str | None = Field(None, description="故事弧摘要")
    start_chapter_number: int | None = Field(None, ge=1, description="开始章节号")
    end_chapter_number: int | None = Field(None, ge=1, description="结束章节号")
    status: str = Field(default="PLANNED", max_length=50, description="状态")
    version: int = Field(default=1, ge=1, description="乐观锁版本号")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )

    @model_validator(mode="after")
    def validate_chapter_numbers(self):
        """验证结束章节号不能小于开始章节号"""
        if (
            self.start_chapter_number is not None
            and self.end_chapter_number is not None
            and self.end_chapter_number < self.start_chapter_number
        ):
            raise ValueError("结束章节号不能小于开始章节号")
        return self


class ReviewModel(BaseDBModel):
    """评审记录表模型"""

    id: UUID
    chapter_id: UUID = Field(..., description="关联的章节ID")
    chapter_version_id: UUID = Field(..., description="评审针对的具体章节版本ID")
    agent_type: AgentType = Field(..., description="执行评审的Agent类型")
    review_type: str = Field(..., max_length=50, description="评审类型")
    score: Annotated[Decimal, condecimal(max_digits=3, decimal_places=1, ge=0, le=10)] | None = (
        Field(None, description="评论家评分")
    )
    comment: str | None = Field(None, description="评论家评语")
    is_consistent: bool | None = Field(None, description="事实核查员判断是否一致")
    issues_found: None | list[str] = Field(None, description="事实核查员发现的问题列表")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="评审创建时间"
    )