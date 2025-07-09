"""
章节更新相关的 Pydantic 模型
"""

from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import Field, model_validator

from src.schemas.base import BaseSchema
from src.schemas.enums import ChapterStatus


class ChapterUpdateRequest(BaseSchema):
    """章节更新请求 - 所有字段可选"""

    title: str | None = Field(None, max_length=255, description="章节标题")
    status: ChapterStatus | None = Field(None, description="章节当前状态")
    published_version_id: UUID | None = Field(None, description="指向当前已发布版本的ID")

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """确保至少有一个字段被设置"""
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("至少需要提供一个字段进行更新")
        return self


class ChapterVersionUpdate(BaseSchema):
    """章节版本更新请求 - 所有字段可选"""

    content_url: str | None = Field(None, description="指向MinIO中该版本内容的URL")
    word_count: int | None = Field(None, ge=0, description="该版本的字数")
    change_reason: str | None = Field(None, description="修改原因")
    metadata: dict[str, Any] | None = Field(None, description="版本相关的额外元数据")

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """确保至少有一个字段被设置"""
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("至少需要提供一个字段进行更新")
        return self


class ReviewUpdate(BaseSchema):
    """评审记录更新请求 - 所有字段可选"""

    score: (
        Annotated[
            Decimal, Field(max_digits=3, decimal_places=1, ge=Decimal("0"), le=Decimal("10"), description="评论家评分")
        ]
        | None
    ) = None
    comment: str | None = Field(None, description="评论家评语")
    is_consistent: bool | None = Field(None, description="事实核查员判断是否一致")
    issues_found: list[str] | None = Field(None, description="事实核查员发现的问题列表")

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """确保至少有一个字段被设置"""
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("至少需要提供一个字段进行更新")
        return self
