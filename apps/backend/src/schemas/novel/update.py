"""
更新小说的请求 schemas
"""

from pydantic import Field, model_validator

from src.schemas.base import BaseSchema
from src.schemas.enums import NovelStatus


class NovelUpdateRequest(BaseSchema):
    """更新小说请求 - 所有字段可选"""

    title: str | None = Field(None, max_length=255, description="小说标题")
    theme: str | None = Field(None, description="小说主题")
    writing_style: str | None = Field(None, description="写作风格")
    status: NovelStatus | None = Field(None, description="小说状态")
    target_chapters: int | None = Field(None, ge=1, le=1000, description="目标章节数")
    version: int | None = Field(None, description="版本号，用于乐观锁")

    @model_validator(mode="after")
    def at_least_one_field(self):
        """确保至少有一个字段被更新"""
        # Don't count version field for the "at least one field" validation
        values_without_version = {k: v for k, v in self.model_dump().items() if k != "version"}
        if all(value is None for value in values_without_version.values()):
            raise ValueError("至少需要提供一个要更新的字段")
        return self
