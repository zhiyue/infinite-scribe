"""
世界观创建相关的 Pydantic 模型
"""

from uuid import UUID

from pydantic import Field, model_validator

from src.schemas.base import BaseSchema
from src.schemas.enums import WorldviewEntryType


class WorldviewEntryCreateRequest(BaseSchema):
    """世界观条目创建请求"""

    novel_id: UUID = Field(..., description="所属小说的ID")
    entry_type: WorldviewEntryType = Field(..., description="条目类型")
    name: str = Field(..., max_length=255, description="条目名称")
    description: str | None = Field(None, description="详细描述")
    tags: list[str] | None = Field(None, description="标签, 用于分类和检索")


class StoryArcCreateRequest(BaseSchema):
    """故事弧创建请求"""

    novel_id: UUID = Field(..., description="所属小说的ID")
    title: str = Field(..., max_length=255, description="故事弧标题")
    summary: str | None = Field(None, description="故事弧摘要")
    start_chapter_number: int | None = Field(None, ge=1, description="开始章节号")
    end_chapter_number: int | None = Field(None, ge=1, description="结束章节号")
    status: str = Field(default="PLANNED", max_length=50, description="状态")

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
