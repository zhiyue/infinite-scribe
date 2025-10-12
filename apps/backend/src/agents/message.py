"""Agent 消息封装模型和辅助函数。

提供统一的 Envelope 模式和编解码工具，确保 Agent 间通信具有强类型和版本管理能力。
通过标准化的消息格式，支持分布式追踪、重试机制和错误处理。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from .constants import (
    DEFAULT_EVENT_TYPE,
    ENVELOPE_VERSION,
    RESERVED_FIELD_TYPE,
    STATUS_ERROR,
    STATUS_OK,
)


class Envelope(BaseModel):
    """Agent 间通信的标准消息封装。

    设计理念：
    - 将元数据（id, ts, type 等）与业务数据（data）分离，便于路由和监控
    - 支持分布式追踪（correlation_id）和重试机制（retries）
    - 统一的版本管理（version）确保消息格式的演进兼容性
    """

    id: str = Field(description="Unique message identifier (UUID)")
    ts: datetime = Field(description="Event timestamp in UTC")
    type: str = Field(description="Business event type")
    version: str = Field(default=ENVELOPE_VERSION, description="Envelope version")
    agent: str | None = Field(default=None, description="Producing agent name")
    correlation_id: str | None = Field(default=None, description="Correlation id for tracing")
    retries: int | None = Field(default=None, description="Number of retries before success")
    status: str | None = Field(default=None, description=f"Business status: {STATUS_OK}/{STATUS_ERROR}")
    data: dict[str, Any] = Field(default_factory=dict, description="Payload data")

    @property
    def message_id(self) -> str:
        return self.id


def encode_message(agent: str, result: dict[str, Any], *, correlation_id: str | None, retries: int) -> dict[str, Any]:
    """将 Agent 的业务结果编码为标准 Envelope 格式。

    参数:
        agent: 生产消息的 Agent 名称
        result: 业务结果字典，必须包含 'type' 字段
        correlation_id: 用于分布式追踪的关联 ID
        retries: 成功前的重试次数

    注意:
        - 调用方需要预先移除 Kafka 路由相关的保留字段（如 _topic, _key）
        - type 字段会被提升到 Envelope 层级，不再包含在 data 中
        - 返回的 dict 已经 JSON 序列化友好（datetime 等会被转换）
    """
    from uuid import uuid4

    event_type = str(result.get(RESERVED_FIELD_TYPE, DEFAULT_EVENT_TYPE))
    # 复制 result 避免修改输入参数，同时将 type 提升到 Envelope 层级
    data = {k: v for k, v in result.items() if k != RESERVED_FIELD_TYPE}

    envelope = Envelope(
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


def decode_message(value: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """将传入消息解码为 (业务数据, 元数据) 元组。

    设计理念：
        - 只接受标准 Envelope 格式，确保消息规范性
        - 返回统一的 (payload, meta) 结构，简化消费方代码
        - 使用 Pydantic 验证，格式错误时自动抛出 ValidationError

    返回:
        (payload, meta): 业务数据字典和元数据字典
            - payload 为 Envelope 的 data 字段内容
            - meta 包含所有 Envelope 元数据字段

    抛出:
        ValidationError: 当消息不符合 Envelope 格式时
    """
    # 验证并解析 Envelope 格式（格式错误会抛出 ValidationError）
    envelope = Envelope.model_validate(value)
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
