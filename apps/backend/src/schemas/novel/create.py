"""
创建小说的请求 schemas
"""

from pydantic import Field

from src.schemas.base import BaseSchema


class NovelCreateRequest(BaseSchema):
    """创建小说请求"""

    title: str = Field(..., max_length=255, description="小说标题")
    theme: str | None = Field(None, description="小说主题，如'科幻冒险'、'都市言情'等")
    writing_style: str | None = Field(None, description="写作风格，如'幽默诙谐'、'严肃写实'等")
    target_chapters: int = Field(default=10, ge=1, le=1000, description="目标章节数")
