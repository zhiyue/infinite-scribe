"""对话创建相关的Schema定义（CQRS - Create）"""

from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from src.schemas.base import BaseSchema

from .enums import DialogueRole, ScopeType

# ---------- 核心对话创建Schema ----------


class ConversationSessionCreate(BaseSchema):
    """创建新的对话会话"""

    scope_type: ScopeType = Field(..., description="对话范围类型")
    scope_id: str = Field(..., description="业务实体ID (例如: novel_id, chapter_id)")
    stage: str | None = Field(None, description="范围内的可选阶段")
    initial_state: dict[str, Any] = Field(default_factory=dict, description="初始会话状态/上下文")


class ConversationRoundCreate(BaseSchema):
    """创建新的对话轮次/回合"""

    session_id: UUID = Field(..., description="父会话ID")
    round_path: str = Field(
        ..., description="分层轮次路径 (例如: '1', '2', '2.1', '2.1.1')", pattern=r"^(\d+)(\.(\d+))*$"
    )
    role: DialogueRole = Field(..., description="参与者角色")
    input: dict[str, Any] = Field(..., description="轮次输入/提示")
    model: str = Field(..., description="使用的LLM模型")
    correlation_id: str | None = Field(None, description="请求相关ID，用于幂等性")

    @field_validator("round_path")
    @classmethod
    def validate_round_path(cls, v: str) -> str:
        """验证分层轮次路径格式"""
        import re

        if not re.match(r"^(\d+)(\.(\d+))*$", v):
            raise ValueError(f"无效的轮次路径格式: {v}")
        return v


# ---------- API兼容的创建Schema ----------


class CreateSessionRequest(BaseSchema):
    """创建会话请求 (API兼容)"""

    scope_type: ScopeType = Field(..., description="对话范围类型", examples=["GENESIS"])
    scope_id: str = Field(..., description="业务实体ID，例如 novel_id")
    stage: str | None = Field(None, description="范围内的可选阶段")
    initial_state: dict[str, Any] = Field(default_factory=dict, description="初始会话状态")


class RoundCreateRequest(BaseSchema):
    """轮次创建请求 (API兼容)"""

    role: DialogueRole = Field(..., description="轮次角色")
    input: dict[str, Any] = Field(..., description="轮次输入/提示")
    model: str | None = Field(None, description="使用的LLM模型")
    correlation_id: str | None = Field(None, description="客户端提供的correlation id")


class CommandRequest(BaseSchema):
    """命令请求"""

    type: str = Field(..., description="命令类型")
    payload: dict[str, Any] = Field(default_factory=dict)


class ContentSearchRequest(BaseSchema):
    """内容搜索请求"""

    query: str | None = None
    stage: str | None = None
    type: str | None = None
    page: int = 1
    limit: int = 20


class VersionCreateRequest(BaseSchema):
    """版本创建请求"""

    base_version: int
    label: str
    description: str | None = None


class VersionMergeRequest(BaseSchema):
    """版本合并请求"""

    source: str
    target: str
    strategy: str | None = None
