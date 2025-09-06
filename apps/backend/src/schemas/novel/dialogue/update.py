"""对话更新相关的Schema定义（CQRS - Update）"""

from decimal import Decimal
from typing import Any

from pydantic import Field, model_validator

from src.schemas.base import BaseSchema

from .enums import SessionStatus

# ---------- 核心对话更新Schema ----------


class ConversationSessionUpdate(BaseSchema):
    """更新会话状态"""

    status: SessionStatus | None = Field(None, description="会话状态")
    stage: str | None = Field(None, description="当前阶段")
    state: dict[str, Any] | None = Field(None, description="会话聚合状态")

    @model_validator(mode="after")
    def at_least_one_field(self):
        """确保至少提供一个字段进行更新"""
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("更新时至少必须提供一个字段")
        return self


class ConversationRoundUpdate(BaseSchema):
    """使用响应更新对话轮次"""

    output: dict[str, Any] = Field(..., description="轮次输出/响应")
    tool_calls: list[dict[str, Any]] | None = Field(None, description="工具调用")
    tokens_in: int = Field(..., ge=0, description="输入token数量")
    tokens_out: int = Field(..., ge=0, description="输出token数量")
    latency_ms: int = Field(..., ge=0, description="响应延迟(毫秒)")
    cost: Decimal | None = Field(None, ge=0, decimal_places=4, description="轮次成本")


# ---------- API兼容的更新Schema ----------


class UpdateSessionRequest(BaseSchema):
    """更新会话请求 (API兼容)"""

    status: SessionStatus | None = None
    stage: str | None = None
    state: dict[str, Any] | None = None
