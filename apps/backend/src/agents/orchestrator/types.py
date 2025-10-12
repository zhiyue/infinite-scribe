"""Orchestrator 特有的类型定义

本模块只包含 Orchestrator 特有的类型。
通用的事件和消息类型已迁移到 src.common.types 模块。

向后兼容性：
为了保持向后兼容，本模块重新导出所有通用类型，
这样现有代码可以继续使用 `from src.agents.orchestrator.types import ...`
而不需要立即修改导入路径。

推荐做法：
新代码应该直接从 src.common.types 导入通用类型：
    from src.common.types import EventMetadata, MessageContext
    from src.agents.orchestrator.types import ProcessingResult
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

# =============================================================================
# 重新导出通用类型以保持向后兼容
# =============================================================================
# 从 common.types 导入所有通用类型
from src.common.types import (
    CapabilityEventData,
    CapabilityEventMessage,
    CapabilityTaskMessage,
    ContentData,
    DomainEvent,
    DomainEventMetadata,
    DomainEventPayload,
    EventActionType,
    EventMetadata,
    EventOutboxHeaders,
    EventPayloadData,
    GenerationData,
    MessageContext,
    MessageType,
    ScopeInfo,
    ScopeType,
    TargetType,
    TaskCompletionPayload,
    TaskInput,
    TaskResultData,
)

# =============================================================================
# Orchestrator 特有的类型定义
# =============================================================================


class ProcessingResult(BaseModel):
    """处理结果 - 编排器响应格式

    这是 Orchestrator 特有的类型，用于封装处理结果和元数据。
    """

    action: Any  # EventAction，避免循环导入
    msg_type: str
    session_id: str
    correlation_id: str | None = None

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


# =============================================================================
# 导出列表
# =============================================================================

__all__ = [
    # Orchestrator 特有类型
    "ProcessingResult",
    # 重新导出的通用事件类型（向后兼容）
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
    # 重新导出的通用消息类型（向后兼容）
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
