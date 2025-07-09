"""
角色更新相关的 Pydantic 模型
"""

from pydantic import Field, model_validator

from src.schemas.base import BaseSchema


class CharacterUpdateRequest(BaseSchema):
    """角色更新请求 - 所有字段可选"""

    name: str | None = Field(None, max_length=255, description="角色名称")
    role: str | None = Field(None, max_length=50, description="角色定位")
    description: str | None = Field(None, description="角色外貌、性格等简述")
    background_story: str | None = Field(None, description="角色背景故事")
    personality_traits: list[str] | None = Field(None, description="性格特点列表")
    goals: list[str] | None = Field(None, description="角色的主要目标列表")

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """确保至少有一个字段被设置"""
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("至少需要提供一个字段进行更新")
        return self
