"""能力事件消息封装。

提供 Agent 间异步通信的标准化消息格式，支持能力调用、状态管理和重试机制。

核心组件：
- CapabilityEventEnvelope: 能力事件的标准信封格式
- 支持分布式追踪、重试机制和状态管理

使用场景：
- Agent 间的异步能力调用
- 能力执行状态跟踪
- 消息重试和错误处理
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

# 消息格式常量
ENVELOPE_VERSION = "v1"
DEFAULT_EVENT_TYPE = "unknown"
RESERVED_FIELD_TYPE = "type"
STATUS_OK = "ok"
STATUS_ERROR = "error"


class CapabilityEventEnvelope(BaseModel):
    """能力事件的标准消息封装。

    用于 Agent 间异步通信的结构化消息格式，与 DomainEventEnvelope（领域事件）互补。

    设计理念：
    - 分离元数据（id, ts, type）和业务数据（data），便于路由和监控
    - 支持分布式追踪（correlation_id）构建调用链
    - 支持重试机制（retries）和状态管理（status）
    - 统一的版本管理（version）确保消息格式的演进兼容性

    使用场景：
    - Agent 间的能力调用请求
    - 能力执行结果返回
    - 异步任务状态跟踪
    - 消息重试和错误处理

    对比 DomainEventEnvelope：
    - CapabilityEventEnvelope: 能力调用（请求/响应）
    - DomainEventEnvelope: 领域事件（已发生的业务事实）
    """

    id: str = Field(description="消息唯一标识符（UUID）")
    ts: datetime = Field(description="消息时间戳（UTC）")
    type: str = Field(description="能力事件类型")
    version: str = Field(default=ENVELOPE_VERSION, description="信封格式版本")
    agent: str | None = Field(default=None, description="生产消息的 Agent 名称")
    correlation_id: str | None = Field(default=None, description="关联ID，用于分布式追踪")
    retries: int | None = Field(default=None, description="重试次数")
    status: str | None = Field(default=None, description=f"执行状态: {STATUS_OK}/{STATUS_ERROR}")
    data: dict[str, Any] = Field(default_factory=dict, description="业务数据负载")

    @property
    def message_id(self) -> str:
        """消息ID别名，与 id 字段相同。"""
        return self.id


def encode_capability_message(
    agent: str, result: dict[str, Any], *, correlation_id: str | None, retries: int
) -> dict[str, Any]:
    """将 Agent 的业务结果编码为 CapabilityEventEnvelope 格式。

    Args:
        agent: 生产消息的 Agent 名称
        result: 业务结果字典，必须包含 'type' 字段
        correlation_id: 用于分布式追踪的关联 ID
        retries: 成功前的重试次数

    Returns:
        编码后的消息字典（JSON 序列化友好）

    注意:
        - 调用方需要预先移除 Kafka 路由相关的保留字段（如 _topic, _key）
        - type 字段会被提升到 Envelope 层级，不再包含在 data 中
        - 返回的 dict 已经 JSON 序列化友好（datetime 等会被转换）

    使用示例：
        ```python
        result = {
            "type": "capability.executed",
            "output": {"key": "value"}
        }
        envelope = encode_capability_message(
            agent="orchestrator",
            result=result,
            correlation_id="req-123",
            retries=0
        )
        ```
    """
    event_type = str(result.get(RESERVED_FIELD_TYPE, DEFAULT_EVENT_TYPE))
    # 复制 result 避免修改输入参数，同时将 type 提升到 Envelope 层级
    data = {k: v for k, v in result.items() if k != RESERVED_FIELD_TYPE}

    envelope = CapabilityEventEnvelope(
        id=str(uuid4()),
        ts=datetime.now(UTC),
        type=event_type,
        version=ENVELOPE_VERSION,
        agent=agent,
        correlation_id=correlation_id,
        retries=retries,
        status=STATUS_OK,
        data=data,
    )
    # 输出 JSON 友好的 dict，确保 datetime 等可被 json.dumps 序列化
    return envelope.model_dump(mode="json")


def decode_capability_message(
    value: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """将 CapabilityEventEnvelope 格式的消息解码为 (业务数据, 元数据) 元组。

    Args:
        value: 消息字典，应符合 CapabilityEventEnvelope 格式

    Returns:
        (payload, meta): 业务数据字典和元数据字典
            - payload 为消息的 data 字段内容
            - meta 包含所有元数据字段（id, type, correlation_id 等）

    Raises:
        ValidationError: 当消息不符合 CapabilityEventEnvelope 格式时

    使用示例：
        ```python
        message = {
            "id": "msg-123",
            "ts": "2025-01-01T00:00:00Z",
            "type": "capability.executed",
            "data": {"key": "value"}
        }
        payload, meta = decode_capability_message(message)
        ```
    """
    # 验证并解析 CapabilityEventEnvelope 格式
    envelope = CapabilityEventEnvelope.model_validate(value)
    payload = envelope.data
    meta = {
        "id": envelope.id,
        "message_id": envelope.message_id,
        "type": envelope.type,
        "version": envelope.version,
        "correlation_id": envelope.correlation_id,
        "agent": envelope.agent,
        "retries": envelope.retries,
        "status": envelope.status,
    }
    return payload, meta
