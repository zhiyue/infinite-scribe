"""
创世流程查询响应相关的 Pydantic 模型
"""

from typing import Any
from uuid import UUID

from pydantic import Field

from src.schemas.base import BaseSchema, TimestampMixin
from src.schemas.enums import GenesisStage, GenesisStatus


class ConceptTemplateResponse(BaseSchema, TimestampMixin):
    """立意模板响应模型"""

    id: UUID = Field(..., description="模板唯一标识符")
    core_idea: str = Field(..., description="核心抽象思想")
    description: str = Field(..., description="立意的深层含义阐述")

    # 哲学维度
    philosophical_depth: str = Field(..., description="哲学思辨的深度表达")
    emotional_core: str = Field(..., description="情感核心与内在冲突")

    # 分类标签
    philosophical_category: str | None = Field(None, description="哲学类别")
    thematic_tags: list[str] = Field(..., description="主题标签")
    complexity_level: str = Field(..., description="思辨复杂度")

    # 适用性
    universal_appeal: bool = Field(..., description="是否具有普遍意义")
    cultural_specificity: str | None = Field(None, description="文化特异性")

    # 元数据
    is_active: bool = Field(..., description="是否启用")
    created_by: str | None = Field(None, description="创建者")


# GenesisSessionResponse removed - replaced by GenesisFlow and GenesisStageRecord schemas
