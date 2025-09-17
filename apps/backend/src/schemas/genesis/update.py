"""
创世流程更新相关的 Pydantic 模型
"""

from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from src.schemas.base import BaseSchema
from src.schemas.enums import GenesisStage, GenesisStatus


class ConceptTemplateUpdateRequest(BaseSchema):
    """立意模板更新请求 - 所有字段可选"""

    core_idea: str | None = Field(None, max_length=200, description="核心抽象思想")
    description: str | None = Field(None, max_length=800, description="立意的深层含义阐述")
    philosophical_depth: str | None = Field(None, max_length=1000, description="哲学思辨的深度表达")
    emotional_core: str | None = Field(None, max_length=500, description="情感核心与内在冲突")
    philosophical_category: str | None = Field(None, max_length=100, description="哲学类别")
    thematic_tags: list[str] | None = Field(None, description="主题标签")
    complexity_level: str | None = Field(None, max_length=20, description="思辨复杂度")
    universal_appeal: bool | None = Field(None, description="是否具有普遍意义")
    cultural_specificity: str | None = Field(None, max_length=100, description="文化特异性")
    is_active: bool | None = Field(None, description="是否启用")

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """确保至少有一个字段被设置"""
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("至少需要提供一个字段进行更新")
        return self


# GenesisSessionUpdateRequest removed - replaced by GenesisFlow and GenesisStageRecord schemas
