"""事件相关的通用类型定义

本模块包含所有与事件相关的通用类型，用于整个后端系统的事件处理。
这些类型可以被任何 agent 或服务使用，无需依赖特定的编排器实现。

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

# =============================================================================
# 字面量类型定义
# =============================================================================

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

# =============================================================================
# 统一事件元数据模型
# =============================================================================


class EventMetadata(BaseModel):
    """统一的事件元数据模型 - 合并所有元数据字段并消除重复定义

    这个类定义了事件系统中所有元数据的标准结构，用于：
    - 事件标识和分类
    - 业务流程关联和追踪
    - 技术调用链监控
    - 系统间数据传递

    字段说明：

    核心标识字段：
    - event_id: 事件唯一标识符，通常为UUID格式，用于事件去重、引用、审计追踪
      示例：'550e8400-e29b-41d4-a716-446655440000'

    - event_type: 事件类型标识，遵循层次化命名约定
      格式：Domain.Aggregate.Action（如：Genesis.Character.Generated）
      用途：事件分类、路由、处理器匹配
      注意：统一使用event_type而不是type，避免Python关键字冲突

    - aggregate_type: 聚合根类型，DDD概念中的聚合标识
      格式：通常为单个名词（如：Genesis、Character、Session）
      用途：数据分区、事件分组、业务边界定义

    - aggregate_id: 聚合根实例ID，通常对应具体的业务实体
      格式：UUID或业务ID（如：session_id、user_id）
      用途：事件与具体业务实体关联、数据分片

    业务关联字段：
    - correlation_id: 业务流程关联ID，用于串联完整的业务操作
      作用域：单一业务请求的完整生命周期
      用途：业务流程追踪、事件幂等性保证、跨服务的业务操作关联
      示例：'user-char-gen-20241201-001'
      生命周期：用户发起请求 → 多个领域事件 → 业务完成

    - causation_id: 因果关系ID，指向触发当前事件的上游事件
      用途：事件链追踪（Event A → Event B → Event C）、调试复杂业务流程、审计和回溯分析
      示例：当前事件由event_id='abc-123'的事件触发，则causation_id='abc-123'
      注意：形成有向无环图(DAG)，避免循环引用

    时间字段：
    - created_at: 事件创建时间戳，ISO 8601格式
      格式：'2024-12-01T10:30:00.123Z'
      用途：事件排序和时间线重建、性能分析和SLA监控、数据归档和清理策略
      注意：建议使用UTC时间避免时区问题

    版本字段：
    - event_version: 事件schema版本号，用于事件结构演进
      用途：事件格式向后兼容、系统升级和迁移、反序列化版本控制
      示例：v1=1, v2=2（递增整数）

    - version: 字符串版本标识，兼容现有系统的version字段
      格式：'v1', 'v2.1', '1.0.0'等
      用途：与外部系统集成时的版本兼容
      注意：建议新系统使用event_version（整数），此字段用于过渡

    分布式追踪字段：
    - trace_id: 分布式追踪ID，用于跨服务调用链监控
      作用域：完整的技术调用链（可能跨越多个业务操作）
      用途：性能监控和APM、错误排查和调试、系统观测性(Observability)、调用链分析
      示例：'jaeger-trace-550e8400e29b41d4a716446655440000'
      传播：通过HTTP Headers、消息队列属性等技术手段
      与correlation_id区别：trace_id关注技术维度的系统调用，correlation_id关注业务维度的业务流程

    - span_id: 调用链段标识，标识trace中的具体操作段
      用途：细粒度的调用监控、性能瓶颈定位、调用链可视化
      示例：'span-abc123def456'
      关系：trace_id包含多个span_id，形成调用树

    - source: 事件来源标识，标识产生事件的系统或组件
      用途：事件溯源和审计、系统间集成调试、权限和安全控制
      示例：'orchestrator', 'api-gateway', 'character-service'
      建议：使用标准化的服务名称

    扩展元数据：
    - metadata: 通用元数据字典，存储额外的上下文信息
      用途：存储不适合标准字段的附加信息、系统特定的扩展数据、临时性的调试信息
      示例：{'user_id': 'user-123', 'session_type': 'character_generation', 'experiment_id': 'exp-001'}
      注意：避免存储敏感信息、保持结构简单、考虑大小限制
    """

    # 核心标识字段
    event_id: str | None = None
    event_type: str | None = None
    aggregate_type: str | None = None
    aggregate_id: str | None = None

    # 业务关联字段
    correlation_id: str | None = None
    causation_id: str | None = None

    # 时间字段
    created_at: str | None = None

    # 版本字段
    event_version: int | None = None
    version: str | None = None

    # 分布式追踪字段
    trace_id: str | None = None
    span_id: str | None = None
    source: str | None = None

    # 扩展元数据
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        extra="allow",  # 允许额外字段以保持向后兼容
        validate_assignment=True,
    )


class ScopeInfo(BaseModel):
    """作用域信息 - 严格验证作用域类型"""

    topic: str
    scope_prefix: str
    scope_type: str = Field(default="GENESIS")

    model_config = ConfigDict(extra="forbid")  # 严格模式：不允许额外字段


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


class EventOutboxHeaders(BaseModel):
    """事件 Outbox 头部信息 - 运行时验证的结构化数据"""

    event_type: str | None = None
    version: int = Field(default=1, ge=1)
    correlation_id: str | None = None
    causation_id: str | None = None  # 因果关系ID
    aggregate_id: str | None = None  # 聚合ID
    aggregate_type: str | None = None  # 聚合类型
    content_type: str = Field(default="application/json")  # 内容类型
    schema_version: str = Field(default="v1")  # 架构版本
    timestamp: str | None = None  # 时间戳
    user_id: str | None = None  # 用户ID
    novel_id: str | None = None  # 小说ID
    session_id: str | None = None  # 会话ID
    source: str | None = None  # 事件源
    trace_id: str | None = None  # 追踪ID
    agent: str | None = None
    type: str | None = None  # 兼容现有代码

    @field_validator("version", mode="before")
    @classmethod
    def normalize_version(cls, v: Any) -> int:
        """允许传入字符串版本（如'v1'），统一转换为整数。"""
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            digits = "".join(ch for ch in v if ch.isdigit())
            if digits:
                return int(digits)
        return 1

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


class DomainEvent(BaseModel):
    """领域事件完整结构"""

    event_type: str
    aggregate_id: str
    payload: EventPayloadData
    metadata: EventMetadata = Field(default_factory=EventMetadata)
    user_id: str | None = None
    created_at: str | None = None
    event_id: str | None = None

    model_config = ConfigDict(extra="allow")


# 向后兼容的别名
DomainEventMetadata = EventMetadata


__all__ = [
    # 字面量类型
    "EventActionType",
    "TargetType",
    "ScopeType",
    # 元数据和上下文
    "EventMetadata",
    "DomainEventMetadata",
    "ScopeInfo",
    # 事件结构
    "EventPayloadData",
    "DomainEventPayload",
    "EventOutboxHeaders",
    "DomainEvent",
]
