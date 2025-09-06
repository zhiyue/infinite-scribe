"""对话读取相关的Schema定义（CQRS - Read）"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from src.schemas.base import BaseSchema

from .enums import DialogueRole, ScopeType, SessionStatus

# ---------- 核心对话响应Schema ----------


class ConversationSessionResponse(BaseSchema):
    """对话会话响应"""

    id: UUID = Field(..., description="会话ID")
    scope_type: ScopeType = Field(..., description="对话范围类型")
    scope_id: str = Field(..., description="业务实体ID")
    status: SessionStatus = Field(..., description="当前会话状态")
    stage: str | None = Field(None, description="当前阶段")
    state: dict[str, Any] = Field(default_factory=dict, description="会话聚合状态")
    version: int = Field(..., ge=1, description="乐观并发控制版本")
    created_at: datetime = Field(..., description="会话创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")

    @field_validator("state", mode="before")
    @classmethod
    def ensure_dict(cls, v):
        """确保state始终是字典"""
        return v if isinstance(v, dict) else {}


class ConversationRoundResponse(BaseSchema):
    """对话轮次响应"""

    session_id: UUID = Field(..., description="父会话ID")
    round_path: str = Field(..., description="分层轮次路径")
    role: DialogueRole = Field(..., description="参与者角色")
    input: dict[str, Any] = Field(..., description="轮次输入")
    output: dict[str, Any] | None = Field(None, description="轮次输出")
    tool_calls: list[dict[str, Any]] | None = Field(None, description="工具调用")
    model: str = Field(..., description="使用的LLM模型")
    tokens_in: int | None = Field(None, ge=0, description="输入token数量")
    tokens_out: int | None = Field(None, ge=0, description="输出token数量")
    latency_ms: int | None = Field(None, ge=0, description="响应延迟")
    cost: Decimal | None = Field(None, description="轮次成本")
    correlation_id: str | None = Field(None, description="请求相关ID")
    created_at: datetime = Field(..., description="轮次创建时间")

    @field_validator("round_path")
    @classmethod
    def validate_round_path(cls, v: str) -> str:
        """验证分层轮次路径格式"""
        import re

        if not re.match(r"^(\d+)(\.(\d+))*$", v):
            raise ValueError(f"无效的轮次路径格式: {v}")
        return v


class DialogueHistory(BaseSchema):
    """会话的对话历史"""

    session: ConversationSessionResponse = Field(..., description="会话信息")
    rounds: list[ConversationRoundResponse] = Field(default_factory=list, description="按时间顺序的对话轮次")
    total_tokens_in: int = Field(0, ge=0, description="总输入token")
    total_tokens_out: int = Field(0, ge=0, description="总输出token")
    total_cost: Decimal = Field(Decimal("0.0"), ge=0, description="总成本")

    @model_validator(mode="after")
    def calculate_totals(self):
        """从轮次计算总指标"""
        self.total_tokens_in = sum(r.tokens_in or 0 for r in self.rounds)
        self.total_tokens_out = sum(r.tokens_out or 0 for r in self.rounds)
        self.total_cost = Decimal(sum(r.cost or Decimal("0.0") for r in self.rounds))
        return self


class DialogueCache(BaseSchema):
    """缓存的对话会话数据"""

    session_id: UUID = Field(..., description="会话ID")
    scope_type: ScopeType = Field(..., description="对话范围类型")
    scope_id: str = Field(..., description="业务实体ID")
    status: SessionStatus = Field(..., description="会话状态")
    state: dict[str, Any] = Field(..., description="会话状态")
    last_round_path: str | None = Field(None, description="最后轮次的路径")
    ttl_seconds: int = Field(2592000, ge=0, description="缓存TTL (默认30天)")

    @property
    def cache_key(self) -> str:
        """生成Redis缓存键"""
        return f"dialogue:session:{self.session_id}"


# ---------- API兼容的响应Schema ----------


class SessionResponse(BaseSchema):
    """会话响应 (API兼容)"""

    id: UUID
    scope_type: ScopeType
    scope_id: str
    status: SessionStatus
    stage: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)
    version: int
    created_at: str
    updated_at: str
    novel_id: UUID | None = None


class RoundResponse(BaseSchema):
    """轮次响应 (API兼容)"""

    session_id: UUID
    round_path: str
    role: DialogueRole
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    model: str | None = None
    correlation_id: str | None = None
    created_at: str


class CommandStatusResponse(BaseSchema):
    """命令状态响应"""

    command_id: UUID
    type: str
    status: str
    submitted_at: str
    correlation_id: str
