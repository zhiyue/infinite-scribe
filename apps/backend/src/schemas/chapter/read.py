"""
章节查询响应相关的 Pydantic 模型
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import Field

from src.schemas.base import BaseSchema, TimestampMixin
from src.schemas.enums import AgentType, ChapterStatus


class ChapterResponse(BaseSchema, TimestampMixin):
    """章节响应模型"""

    id: UUID = Field(..., description="章节唯一标识符")
    novel_id: UUID = Field(..., description="所属小说的ID")
    chapter_number: int = Field(..., description="章节序号")
    title: str | None = Field(None, description="章节标题")
    status: ChapterStatus = Field(..., description="章节当前状态")
    published_version_id: UUID | None = Field(None, description="指向当前已发布版本的ID")
    version: int = Field(..., description="乐观锁版本号")


class ChapterSummary(BaseSchema, TimestampMixin):
    """章节摘要模型 - 用于列表展示"""

    id: UUID = Field(..., description="章节唯一标识符")
    novel_id: UUID = Field(..., description="所属小说的ID")
    chapter_number: int = Field(..., description="章节序号")
    title: str | None = Field(None, description="章节标题")
    status: ChapterStatus = Field(..., description="章节当前状态")


class ChapterVersionResponse(BaseSchema):
    """章节版本响应模型"""

    id: UUID = Field(..., description="章节版本的唯一标识符")
    chapter_id: UUID = Field(..., description="关联的章节ID")
    version_number: int = Field(..., description="版本号")
    content_url: str = Field(..., description="指向MinIO中该版本内容的URL")
    word_count: int | None = Field(None, description="该版本的字数")
    created_by_agent_type: AgentType = Field(..., description="创建此版本的Agent类型")
    change_reason: str | None = Field(None, description="修改原因")
    parent_version_id: UUID | None = Field(None, description="指向上一个版本的ID")
    metadata: dict[str, Any] | None = Field(None, description="版本相关的额外元数据")
    created_at: datetime = Field(..., description="版本创建时间")


class ReviewResponse(BaseSchema):
    """评审记录响应模型"""

    id: UUID = Field(..., description="评审记录唯一标识符")
    chapter_id: UUID = Field(..., description="关联的章节ID")
    chapter_version_id: UUID = Field(..., description="评审针对的具体章节版本ID")
    agent_type: AgentType = Field(..., description="执行评审的Agent类型")
    review_type: str = Field(..., description="评审类型")
    score: (
        Annotated[
            Decimal, Field(max_digits=3, decimal_places=1, ge=Decimal("0"), le=Decimal("10"), description="评论家评分")
        ]
        | None
    ) = None
    comment: str | None = Field(None, description="评论家评语")
    is_consistent: bool | None = Field(None, description="事实核查员判断是否一致")
    issues_found: list[str] | None = Field(None, description="事实核查员发现的问题列表")
    created_at: datetime = Field(..., description="评审创建时间")
