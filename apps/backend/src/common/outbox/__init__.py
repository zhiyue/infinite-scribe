"""Shared helpers for managing outbox operations.

提供基于 Outbox Pattern 的可靠消息传输机制。

核心组件：
- BaseOutboxManager: 通用的消息入队管理器

Note: 领域事件相关的类（DomainEventEnvelope, DomainEventBuilder, SystemMetadata）
已移至 src.common.messaging.domain_envelope，请直接从那里导入。
"""

from .manager import BaseOutboxManager

__all__ = [
    "BaseOutboxManager",
]
