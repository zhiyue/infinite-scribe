"""消息相关的通用类型定义

本模块包含所有与消息传递相关的通用类型，用于整个后端系统的消息处理。
这些类型可以被任何 agent 或服务使用，无需依赖特定的编排器实现。

使用 Pydantic 实现"ultrathink"级别的类型安全性：
- 运行时验证
- 自动类型转换
- 优秀的错误信息
- 与 FastAPI 完美集成
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.common.types.events import EventMetadata

# =============================================================================
# 字面量类型定义
# =============================================================================

MessageType = Literal[
    "Character.Design.Generated",
    "Character.Generated",
    "Outliner.Theme.Generated",
    "Theme.Generated",
    "Review.Quality.Evaluated",
    "Review.Quality.Result",
    "Review.Consistency.Checked",
    "Consistency.Checked",
    "Character.Design.GenerationRequested",
    "Outliner.Theme.GenerationRequested",
    "Review.Quality.EvaluationRequested",
]

# =============================================================================
# 消息上下文和基础数据模型
# =============================================================================


class MessageContext(BaseModel):
    """消息上下文 - 包含主题和元数据"""

    topic: str | None = None
    meta: EventMetadata | None = None

    @field_validator("meta", mode="before")
    @classmethod
    def parse_meta(cls, v: Any) -> Any:
        """自动转换字典为 EventMetadata"""
        if isinstance(v, dict):
            return EventMetadata(**v)
        return v

    model_config = ConfigDict(extra="allow")


class ContentData(BaseModel):
    """内容数据 - 用于替代泛型字典"""

    text: str | None = None
    title: str | None = None
    description: str | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class GenerationData(BaseModel):
    """生成数据 - 内容生成的标准格式"""

    content: ContentData | None = None

    model_config = ConfigDict(extra="allow")


# =============================================================================
# 任务相关消息类型
# =============================================================================


class TaskInput(BaseModel):
    """任务输入数据 - 用于替代泛型字典"""

    prompt: str | None = None
    context: str | None = None
    parameters: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class CapabilityTaskMessage(BaseModel):
    """能力任务消息 - 精确的任务类型"""

    type: str
    session_id: str
    input: TaskInput = Field(default_factory=TaskInput)
    topic: str = Field(alias="_topic")
    key: str = Field(alias="_key")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class TaskResultData(BaseModel):
    """任务结果数据 - 用于替代泛型字典"""

    status: str | None = None
    output: Any | None = None
    error_message: str | None = None
    metrics: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class TaskCompletionPayload(BaseModel):
    """任务完成负载 - 任务状态管理"""

    correlation_id: str | None = None
    expect_task_prefix: str
    result_data: TaskResultData

    model_config = ConfigDict(extra="forbid")


# =============================================================================
# 能力事件消息类型
# =============================================================================


class CapabilityEventData(BaseModel):
    """能力事件数据 - 用于替代泛型字典"""

    raw_data: Any | None = None
    processed_data: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class CapabilityEventMessage(BaseModel):
    """能力事件消息完整结构"""

    type: str | None = None
    data: CapabilityEventData | None = None
    session_id: str | None = None
    correlation_id: str | None = None

    @field_validator("data", mode="before")
    @classmethod
    def ensure_data_is_dict(cls, v: Any) -> CapabilityEventData:
        """确保数据是正确格式"""
        if v is None:
            return CapabilityEventData()
        if isinstance(v, dict):
            return CapabilityEventData(processed_data=v)
        return CapabilityEventData(raw_data=v)

    def to_typed_data(self) -> GenerationData:
        """转换为GenerationData类型"""
        if not self.data or not self.data.processed_data:
            return GenerationData()

        data_dict = self.data.processed_data
        return GenerationData(**data_dict)

    model_config = ConfigDict(extra="allow")


__all__ = [
    # 字面量类型
    "MessageType",
    # 消息上下文
    "MessageContext",
    # 内容数据
    "ContentData",
    "GenerationData",
    # 任务消息
    "TaskInput",
    "CapabilityTaskMessage",
    "TaskResultData",
    "TaskCompletionPayload",
    # 能力事件消息
    "CapabilityEventData",
    "CapabilityEventMessage",
]
