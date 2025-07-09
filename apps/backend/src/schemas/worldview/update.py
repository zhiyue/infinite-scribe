"""
世界观更新相关的 Pydantic 模型
"""

from pydantic import Field, model_validator

from src.schemas.base import BaseSchema
from src.schemas.enums import WorldviewEntryType


class WorldviewEntryUpdateRequest(BaseSchema):
    """世界观条目更新请求 - 所有字段可选"""

    entry_type: WorldviewEntryType | None = Field(None, description="条目类型")
    name: str | None = Field(None, max_length=255, description="条目名称")
    description: str | None = Field(None, description="详细描述")
    tags: list[str] | None = Field(None, description="标签, 用于分类和检索")

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """确保至少有一个字段被设置"""
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("至少需要提供一个字段进行更新")
        return self


class StoryArcUpdateRequest(BaseSchema):
    """故事弧更新请求 - 所有字段可选"""

    title: str | None = Field(None, max_length=255, description="故事弧标题")
    summary: str | None = Field(None, description="故事弧摘要")
    start_chapter_number: int | None = Field(None, ge=1, description="开始章节号")
    end_chapter_number: int | None = Field(None, ge=1, description="结束章节号")
    status: str | None = Field(None, max_length=50, description="状态")

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """确保至少有一个字段被设置"""
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("至少需要提供一个字段进行更新")
        return self

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
