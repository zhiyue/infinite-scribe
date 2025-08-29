"""
查询小说的响应 schemas
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from src.schemas.base import BaseSchema
from src.schemas.enums import NovelStatus


class NovelResponse(BaseSchema):
    """小说响应模型 - 完整信息"""

    id: UUID
    title: str = Field(..., max_length=255, description="小说标题")
    theme: str | None = Field(None, description="小说主题")
    writing_style: str | None = Field(None, description="写作风格")
    status: NovelStatus = Field(..., description="当前状态")
    target_chapters: int = Field(..., ge=0, description="目标章节数")
    completed_chapters: int = Field(..., ge=0, description="已完成章节数")
    version: int = Field(..., ge=1, description="乐观锁版本号")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")

    @model_validator(mode="after")
    def validate_completed_chapters(self):
        """验证已完成章节数不能超过目标章节数"""
        if self.completed_chapters > self.target_chapters:
            raise ValueError("已完成章节数不能超过目标章节数")
        return self


class NovelSummary(BaseSchema):
    """小说摘要信息 - 列表展示"""

    id: UUID
    title: str
    status: NovelStatus
    target_chapters: int
    completed_chapters: int
    created_at: datetime


class NovelProgress(BaseSchema):
    """小说进度信息"""

    novel_id: UUID
    completed_chapters: int
    target_chapters: int
    progress_percentage: float = Field(..., ge=0, le=100, description="完成百分比")

    @model_validator(mode="after")
    def calculate_progress(self):
        """计算进度百分比"""
        if self.target_chapters > 0:
            self.progress_percentage = (self.completed_chapters / self.target_chapters) * 100
        else:
            self.progress_percentage = 0
        return self
