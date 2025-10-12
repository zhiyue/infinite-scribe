"""通用类型定义模块

本模块提供整个后端系统使用的通用类型定义，包括：
- 事件相关类型 (events.py)
- 消息相关类型 (messages.py)

这些类型可以被任何 agent 或服务使用，无需依赖特定的组件实现。
"""

# 导出事件相关类型
from src.common.types.events import (
    DomainEvent,
    DomainEventMetadata,
    DomainEventPayload,
    EventActionType,
    EventMetadata,
    EventOutboxHeaders,
    EventPayloadData,
    ScopeInfo,
    ScopeType,
    TargetType,
)

# 导出消息相关类型
from src.common.types.messages import (
    CapabilityEventData,
    CapabilityEventMessage,
    CapabilityTaskMessage,
    ContentData,
    GenerationData,
    MessageContext,
    MessageType,
    TaskCompletionPayload,
    TaskInput,
    TaskResultData,
)

__all__ = [
    # 事件类型
    "EventActionType",
    "TargetType",
    "ScopeType",
    "EventMetadata",
    "DomainEventMetadata",
    "ScopeInfo",
    "EventPayloadData",
    "DomainEventPayload",
    "EventOutboxHeaders",
    "DomainEvent",
    # 消息类型
    "MessageType",
    "MessageContext",
    "ContentData",
    "GenerationData",
    "TaskInput",
    "CapabilityTaskMessage",
    "TaskResultData",
    "TaskCompletionPayload",
    "CapabilityEventData",
    "CapabilityEventMessage",
]
