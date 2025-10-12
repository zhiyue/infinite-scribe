"""消息传递模块。

提供 Agent 间异步通信的标准化消息格式和编解码工具。

核心组件：
- CapabilityEventEnvelope: Agent 能力调用消息的标准信封格式
- DomainEventEnvelope: 领域事件的标准信封格式（Event Sourcing & CQRS）
- encode_capability_message: 编码能力事件消息
- decode_message: 统一的消息解码接口（支持多种格式）

使用示例：
    ```python
    # 编码能力消息
    from src.common.messaging import encode_capability_message

    message = encode_capability_message(
        agent="orchestrator",
        result={"type": "task.completed", "output": data},
        correlation_id="req-123",
        retries=0
    )

    # 解码消息（自动识别格式）
    from src.common.messaging import decode_message

    payload, meta = decode_message(message)

    # 构建领域事件信封
    from src.common.messaging import DomainEventBuilder

    envelope = DomainEventBuilder.from_domain_event(event).build()
    ```

模块结构：
- capability_envelope.py: CapabilityEventEnvelope 定义和专用编解码
- domain_envelope.py: DomainEventEnvelope 定义和 Builder
- protocol.py: 统一的消息协议和解码接口
"""

from .capability_envelope import (
    CapabilityEventEnvelope,
    decode_capability_message,
    encode_capability_message,
)
from .domain_envelope import DomainEventBuilder, DomainEventEnvelope, SystemMetadata
from .protocol import decode_message

__all__ = [
    # 能力事件信封
    "CapabilityEventEnvelope",
    "encode_capability_message",
    "decode_capability_message",
    # 领域事件信封
    "DomainEventEnvelope",
    "DomainEventBuilder",
    "SystemMetadata",
    # 统一解码接口
    "decode_message",
]
