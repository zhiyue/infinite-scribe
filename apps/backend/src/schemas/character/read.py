"""
角色查询响应相关的 Pydantic 模型
"""

from uuid import UUID

from pydantic import Field

from src.schemas.base import BaseSchema, TimestampMixin


class CharacterResponse(BaseSchema, TimestampMixin):
    """角色响应模型"""

    id: UUID = Field(..., description="角色唯一标识符")
    novel_id: UUID = Field(..., description="所属小说的ID")
    name: str = Field(..., description="角色名称")
    role: str | None = Field(None, description="角色定位")
    description: str | None = Field(None, description="角色外貌、性格等简述")
    background_story: str | None = Field(None, description="角色背景故事")
    personality_traits: list[str] | None = Field(None, description="性格特点列表")
    goals: list[str] | None = Field(None, description="角色的主要目标列表")
    version: int = Field(..., description="乐观锁版本号")
