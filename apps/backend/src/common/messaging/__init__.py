"""消息传递模块。

提供 Agent 间异步通信的标准化消息格式和编解码工具。

核心组件：
- CapabilityEventEnvelope: 能力事件的标准信封格式
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
    ```

模块结构：
- envelope.py: CapabilityEventEnvelope 定义和专用编解码
- protocol.py: 统一的消息协议和解码接口
"""

from .envelope import (
    CapabilityEventEnvelope,
    decode_capability_message,
    encode_capability_message,
)
from .protocol import decode_message

__all__ = [
    # 能力事件信封
    "CapabilityEventEnvelope",
    # 编码函数
    "encode_capability_message",
    # 解码函数
    "decode_capability_message",
    "decode_message",  # 统一解码接口
]
