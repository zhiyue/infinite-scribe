"""
Genesis process related models.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from .base import BaseDBModel
from .enums import GenesisStatus, GenesisStage


class ConceptTemplateModel(BaseDBModel):
    """立意模板表模型 - 存储抽象的哲学立意供用户选择"""

    id: UUID
    core_idea: str = Field(..., max_length=200, description="核心抽象思想,如'知识与无知的深刻对立'")
    description: str = Field(..., max_length=800, description="立意的深层含义阐述")

    # 哲学维度
    philosophical_depth: str = Field(..., max_length=1000, description="哲学思辨的深度表达")
    emotional_core: str = Field(..., max_length=500, description="情感核心与内在冲突")

    # 分类标签(抽象层面)
    philosophical_category: str | None = Field(
        None, max_length=100, description="哲学类别,如'存在主义','人道主义','理想主义'"
    )
    thematic_tags: list[str] = Field(
        default_factory=list, description="主题标签,如['成长','选择','牺牲','真理']"
    )
    complexity_level: str = Field(
        default="medium", max_length=20, description="思辨复杂度,如'simple','medium','complex'"
    )

    # 适用性
    universal_appeal: bool = Field(default=True, description="是否具有普遍意义")
    cultural_specificity: str | None = Field(
        None, max_length=100, description="文化特异性,如'东方哲学','西方哲学','普世价值'"
    )

    # 元数据
    is_active: bool = Field(default=True, description="是否启用")
    created_by: str | None = Field(None, max_length=50, description="创建者,如'system','admin'")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )


class GenesisSessionModel(BaseDBModel):
    """创世会话表模型"""

    id: UUID
    novel_id: UUID | None = Field(None, description="流程完成后关联的小说ID")
    user_id: UUID | None = Field(None, description="用户ID")
    status: GenesisStatus = Field(default=GenesisStatus.IN_PROGRESS, description="会话状态")
    current_stage: GenesisStage = Field(
        default=GenesisStage.CONCEPT_SELECTION, description="当前阶段"
    )
    confirmed_data: dict[str, Any] | None = Field(None, description="存储每个阶段已确认的最终数据")
    version: int = Field(default=1, ge=1, description="乐观锁版本号")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )