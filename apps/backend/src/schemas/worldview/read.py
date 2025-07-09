"""
世界观查询响应相关的 Pydantic 模型
"""

from uuid import UUID

from pydantic import Field

from src.schemas.base import BaseSchema, TimestampMixin
from src.schemas.enums import WorldviewEntryType


class WorldviewEntryResponse(BaseSchema, TimestampMixin):
    """世界观条目响应模型"""

    id: UUID = Field(..., description="条目唯一标识符")
    novel_id: UUID = Field(..., description="所属小说的ID")
    entry_type: WorldviewEntryType = Field(..., description="条目类型")
    name: str = Field(..., description="条目名称")
    description: str | None = Field(None, description="详细描述")
    tags: list[str] | None = Field(None, description="标签, 用于分类和检索")
    version: int = Field(..., description="乐观锁版本号")


class StoryArcResponse(BaseSchema, TimestampMixin):
    """故事弧响应模型"""

    id: UUID = Field(..., description="故事弧唯一标识符")
    novel_id: UUID = Field(..., description="所属小说的ID")
    title: str = Field(..., description="故事弧标题")
    summary: str | None = Field(None, description="故事弧摘要")
    start_chapter_number: int | None = Field(None, description="开始章节号")
    end_chapter_number: int | None = Field(None, description="结束章节号")
    status: str = Field(..., description="状态")
    version: int = Field(..., description="乐观锁版本号")
