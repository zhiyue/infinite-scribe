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


class GenesisSessionResponse(BaseSchema, TimestampMixin):
    """创世会话响应模型"""

    id: UUID = Field(..., description="会话唯一标识符")
    novel_id: UUID | None = Field(None, description="流程完成后关联的小说ID")
    user_id: UUID | None = Field(None, description="用户ID")
    status: GenesisStatus = Field(..., description="会话状态")
    current_stage: GenesisStage = Field(..., description="当前阶段")
    confirmed_data: dict[str, Any] | None = Field(None, description="存储每个阶段已确认的最终数据")
    version: int = Field(..., description="乐观锁版本号")
