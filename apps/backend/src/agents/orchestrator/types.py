"""类型定义模块

使用 Pydantic 实现"ultrathink"级别的类型安全性：
- 运行时验证
- 自动类型转换
- 优秀的错误信息
- 与 FastAPI 完美集成
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# === 字符串字面量类型 - 编译时和运行时都检查 ===

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

EventActionType = Literal[
    "Character.Proposed",
    "Theme.Proposed",
    "Character.Confirmed",
    "Theme.Confirmed",
    "Character.Failed",
    "Theme.Failed",
    "Character.RegenerationRequested",
    "Theme.RegenerationRequested",
    "Stage.Confirmed",
    "Stage.Failed",
]

TargetType = Literal["character", "theme", "content"]
ScopeType = Literal["GENESIS"]


# === Pydantic 模型 - 运行时类型安全 ===


class EventMetadata(BaseModel):
    """事件元数据 - 自动验证和转换"""

    correlation_id: str | None = None
    event_id: str | None = None
    type: str | None = None

    model_config = ConfigDict(extra="allow")  # 允许额外字段以保持向后兼容


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


class ScopeInfo(BaseModel):
    """作用域信息 - 严格验证作用域类型"""

    topic: str
    scope_prefix: str
    scope_type: str = Field(default="GENESIS")

    model_config = ConfigDict(extra="forbid")  # 严格模式：不允许额外字段


# === 基础数据模型 - 所有数据类型的共同字段 ===


class BaseEventData(BaseModel):
    """事件数据基类 - 包含所有事件的共同字段"""

    session_id: str | None = None
    aggregate_id: str | None = None
    correlation_id: str | None = None
    event_id: str | None = None
    type: str | None = None

    model_config = ConfigDict(extra="allow")


class ContentData(BaseModel):
    """内容数据 - 用于替代泛型字典"""

    text: str | None = None
    title: str | None = None
    description: str | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class GenerationData(BaseEventData):
    """生成数据 - 内容生成的标准格式"""

    content: ContentData | None = None

    model_config = ConfigDict(extra="allow")


class QualityReviewData(BaseEventData):
    """质量审查数据 - 评分和阈值系统"""

    score: float | None = None
    quality_score: float | None = None
    attempts: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    threshold: float = Field(default=7.5, ge=0.0, le=10.0)
    target_type: str | None = None
    entity: str | None = None

    @field_validator("score", "quality_score", mode="before")
    @classmethod
    def convert_score(cls, v: Any) -> Any:
        """确保分数是有效的浮点数"""
        if v is not None:
            return float(v)
        return v

    model_config = ConfigDict(extra="allow")


class ConsistencyCheckData(BaseEventData):
    """一致性检查数据 - 布尔和评分双重判断"""

    ok: bool | None = None
    passed: bool | None = None
    score: float | None = None
    threshold: float = Field(default=1.0, ge=0.0)

    @field_validator("score", mode="before")
    @classmethod
    def convert_score(cls, v: Any) -> Any:
        """确保分数是有效的浮点数"""
        if v is not None:
            return float(v)
        return v

    model_config = ConfigDict(extra="allow")


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


class EventPayloadData(BaseModel):
    """事件负载数据 - 用于替代泛型字典"""

    entity_id: str | None = None
    entity_type: str | None = None
    action_data: dict[str, Any] | None = None
    result: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class DomainEventPayload(BaseModel):
    """领域事件负载 - 严格的事件格式"""

    scope_type: str
    session_id: str
    event_action: str
    payload: EventPayloadData
    correlation_id: str | None = None
    causation_id: str | None = None

    model_config = ConfigDict(extra="forbid")


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


class ProcessingResult(BaseModel):
    """处理结果 - 编排器响应格式"""

    action: Any  # EventAction，避免循环导入
    msg_type: str
    session_id: str
    correlation_id: str | None = None

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


class DomainEventMetadata(BaseModel):
    """领域事件元数据 - 用于替代泛型字典"""

    source: str | None = None
    version: str | None = None
    trace_id: str | None = None
    span_id: str | None = None

    model_config = ConfigDict(extra="allow")


class EventOutboxHeaders(BaseModel):
    """事件 Outbox 头部信息 - 运行时验证的结构化数据"""

    event_type: str | None = None
    version: int = Field(default=1, ge=1)
    correlation_id: str | None = None
    causation_id: str | None = None  # 因果关系ID
    aggregate_id: str | None = None   # 聚合ID
    aggregate_type: str | None = None # 聚合类型
    content_type: str = Field(default="application/json") # 内容类型
    schema_version: str = Field(default="v1") # 架构版本
    timestamp: str | None = None      # 时间戳
    user_id: str | None = None       # 用户ID
    source: str | None = None        # 事件源
    trace_id: str | None = None      # 追踪ID
    agent: str | None = None
    type: str | None = None  # 兼容现有代码

    @field_validator("correlation_id")
    @classmethod
    def validate_correlation_id(cls, v: str | None) -> str | None:
        """验证 correlation_id 格式 - 优雅处理无效 UUID"""
        if v is not None and v.strip():
            try:
                UUID(v)
                return v
            except ValueError:
                return None  # 优雅处理无效 UUID，不抛出异常
        return v

    @field_validator("causation_id")
    @classmethod
    def validate_causation_id(cls, v: str | None) -> str | None:
        """验证 causation_id 格式"""
        if v is not None and v.strip():
            try:
                UUID(v)
                return v
            except ValueError:
                return None  # 优雅处理无效 UUID，不抛出异常
        return v

    model_config = ConfigDict(extra="forbid")  # 严格模式


class OutboxPayload(BaseModel):
    """Outbox 有效负载 - 运行时验证的结构化数据"""

    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    domain_payload: dict[str, Any] | None = None  # 冲突字段容器
    created_at: str | None = None

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """验证 event_id 格式"""
        try:
            UUID(v)  # 验证是否为有效 UUID
            return v
        except ValueError as err:
            raise ValueError(f"Invalid event_id format: {v}") from err

    model_config = ConfigDict(extra="allow")  # 支持额外字段


class DomainEvent(BaseModel):
    """领域事件完整结构"""

    event_type: str
    aggregate_id: str
    payload: EventPayloadData
    metadata: DomainEventMetadata = Field(default_factory=DomainEventMetadata)
    user_id: str | None = None
    created_at: str | None = None
    event_id: str | None = None

    model_config = ConfigDict(extra="allow")


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

    def to_typed_data(self) -> GenerationData | QualityReviewData | ConsistencyCheckData:
        """智能转换为具体类型"""
        if not self.data or not self.data.processed_data:
            return GenerationData()

        data_dict = self.data.processed_data
        # 根据数据内容判断类型
        if "score" in data_dict or "quality_score" in data_dict:
            return QualityReviewData(**data_dict)
        elif "ok" in data_dict or "passed" in data_dict:
            return ConsistencyCheckData(**data_dict)
        else:
            return GenerationData(**data_dict)

    model_config = ConfigDict(extra="allow")


# === 类型安全的工厂函数 - 支持更强的类型验证 ===


def create_message_context(**kwargs: Any) -> MessageContext:
    """创建类型安全的消息上下文"""
    return MessageContext(**kwargs)


def create_generation_data(**kwargs: Any) -> GenerationData:
    """创建类型安全的生成数据"""
    return GenerationData(**kwargs)


def create_quality_review_data(**kwargs: Any) -> QualityReviewData:
    """创建类型安全的质量审查数据"""
    return QualityReviewData(**kwargs)


def create_consistency_check_data(**kwargs: Any) -> ConsistencyCheckData:
    """创建类型安全的一致性检查数据"""
    return ConsistencyCheckData(**kwargs)


def create_capability_task_message(**kwargs: Any) -> CapabilityTaskMessage:
    """创建类型安全的能力任务消息"""
    return CapabilityTaskMessage(**kwargs)


def create_capability_event_message(**kwargs: Any) -> CapabilityEventMessage:
    """创建类型安全的能力事件消息"""
    return CapabilityEventMessage(**kwargs)


def create_processing_result(**kwargs: Any) -> ProcessingResult:
    """创建类型安全的处理结果"""
    return ProcessingResult(**kwargs)


# === 向后兼容的工厂函数 - 接受字典参数 ===


def create_message_context_from_dict(data: dict[str, Any]) -> MessageContext:
    """从字典创建消息上下文（向后兼容）"""
    return MessageContext(**data)


def create_generation_data_from_dict(data: dict[str, Any]) -> GenerationData:
    """从字典创建生成数据（向后兼容）"""
    return GenerationData(**data)


def create_quality_review_data_from_dict(data: dict[str, Any]) -> QualityReviewData:
    """从字典创建质量审查数据（向后兼容）"""
    return QualityReviewData(**data)


def create_consistency_check_data_from_dict(data: dict[str, Any]) -> ConsistencyCheckData:
    """从字典创建一致性检查数据（向后兼容）"""
    return ConsistencyCheckData(**data)


def create_capability_task_message_from_dict(data: dict[str, Any]) -> CapabilityTaskMessage:
    """从字典创建能力任务消息（向后兼容）"""
    return CapabilityTaskMessage(**data)


def create_capability_event_message_from_dict(data: dict[str, Any]) -> CapabilityEventMessage:
    """从字典创建能力事件消息（向后兼容）"""
    return CapabilityEventMessage(**data)


def create_processing_result_from_dict(data: dict[str, Any]) -> ProcessingResult:
    """从字典创建处理结果（向后兼容）"""
    return ProcessingResult(**data)
