"""Shared helpers for managing outbox operations.

提供基于 Outbox Pattern 的可靠消息传输机制。
领域事件相关的类已统一移至 src.common.messaging.domain_envelope。

向后兼容性导出：
- DomainEventEnvelope, DomainEventBuilder, SystemMetadata 从 common.messaging 导出
- 新代码应该直接从 common.messaging.domain_envelope 导入
"""

# 向后兼容性导出 - 从新位置导入
from src.common.messaging.domain_envelope import (
    DomainEventBuilder,
    DomainEventEnvelope,
    SystemMetadata,
)

from .manager import BaseOutboxManager

__all__ = [
    "BaseOutboxManager",
    # 向后兼容 - 建议从 common.messaging.domain_envelope 导入
    "DomainEventBuilder",
    "DomainEventEnvelope",
    "SystemMetadata",
]
