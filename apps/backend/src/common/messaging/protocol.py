"""消息协议和编解码工具。

提供统一的消息编解码接口，支持多种消息格式：
- CapabilityEventEnvelope: Agent 能力调用消息
- DomainEventEnvelope: 领域事件消息

核心功能：
- decode_message: 统一解码接口，自动识别消息格式
"""

from __future__ import annotations

from typing import Any


def decode_message(value: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """统一的消息解码接口，自动识别并解码不同格式的消息。

    支持的消息格式：
    1. CapabilityEventEnvelope: {id, ts, type, data, ...} - Agent 能力调用消息
    2. DomainEventEnvelope: {system, data, schema_version} - 领域事件消息

    设计理念：
    - 自动检测消息格式，无需调用方手动判断
    - 返回统一的 (payload, meta) 结构，简化消费方代码
    - 使用 Pydantic 验证，确保类型安全和数据完整性

    Args:
        value: 消息字典，可以是任何支持的格式

    Returns:
        (payload, meta): 业务数据字典和元数据字典
            - payload 为消息的 data 字段内容
            - meta 包含所有元数据字段（id, type, correlation_id 等）

    Raises:
        ValidationError: 当消息不符合任何已知格式时

    使用示例：
        ```python
        # 自动识别 CapabilityEventEnvelope
        capability_msg = {
            "id": "msg-123",
            "ts": "2025-01-01T00:00:00Z",
            "type": "capability.executed",
            "data": {"result": "success"}
        }
        payload, meta = decode_message(capability_msg)

        # 自动识别 DomainEventEnvelope
        domain_event = {
            "system": {
                "event_id": "evt-456",
                "event_type": "Order.Created",
                ...
            },
            "data": {"order_id": "123"},
            "schema_version": "v1"
        }
        payload, meta = decode_message(domain_event)
        ```
    """
    # 检测消息格式：如果有 'system' 字段，则为 DomainEventEnvelope 格式
    if "system" in value and "schema_version" in value:
        # 领域事件格式
        from src.common.messaging.domain_envelope import DomainEventEnvelope

        envelope = DomainEventEnvelope.model_validate(value)
        # 使用类型安全的转换方法获取元数据
        meta = envelope.to_envelope_meta()
        payload = envelope.model_dump()
        return payload, meta

    # 默认为 CapabilityEventEnvelope 格式
    from .capability_envelope import CapabilityEventEnvelope

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
