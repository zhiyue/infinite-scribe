"""
角色创建相关的 Pydantic 模型
"""

from uuid import UUID

from pydantic import Field

from src.schemas.base import BaseSchema


class CharacterCreateRequest(BaseSchema):
    """角色创建请求"""

    novel_id: UUID = Field(..., description="所属小说的ID")
    name: str = Field(..., max_length=255, description="角色名称")
    role: str | None = Field(None, max_length=50, description="角色定位")
    description: str | None = Field(None, description="角色外貌、性格等简述")
    background_story: str | None = Field(None, description="角色背景故事")
    personality_traits: list[str] | None = Field(None, description="性格特点列表")
    goals: list[str] | None = Field(None, description="角色的主要目标列表")
