"""类型定义模块

定义具体的结构化数据类型，提供真正的类型安全性。
"""

from __future__ import annotations

from typing import Any, TypedDict


class EventMetadata(TypedDict, total=False):
    """事件元数据结构"""
    correlation_id: str
    event_id: str
    type: str


class MessageContext(TypedDict, total=False):
    """消息上下文结构"""
    topic: str
    meta: EventMetadata


class ScopeInfo(TypedDict):
    """作用域信息结构"""
    topic: str
    scope_prefix: str
    scope_type: str


class GenerationData(TypedDict, total=False):
    """生成数据结构 - 包含生成的内容"""
    session_id: str
    content: dict[str, Any]


class QualityReviewData(TypedDict, total=False):
    """质量审查数据结构"""
    score: float
    quality_score: float
    attempts: int
    max_attempts: int
    threshold: float
    target_type: str
    entity: str


class ConsistencyCheckData(TypedDict, total=False):
    """一致性检查数据结构"""
    ok: bool
    passed: bool
    score: float
    threshold: float


class DomainEventPayload(TypedDict):
    """领域事件负载结构"""
    scope_type: str
    session_id: str
    event_action: str
    payload: dict[str, Any]
    correlation_id: str | None
    causation_id: str | None


class TaskCompletionPayload(TypedDict):
    """任务完成负载结构"""
    correlation_id: str | None
    expect_task_prefix: str
    result_data: dict[str, Any]


class CapabilityTaskMessage(TypedDict):
    """能力任务消息结构"""
    type: str
    session_id: str
    input: dict[str, Any]
    _topic: str
    _key: str


class ProcessingResult(TypedDict):
    """处理结果结构"""
    action: Any  # EventAction，避免循环导入
    msg_type: str
    session_id: str
    correlation_id: str | None
