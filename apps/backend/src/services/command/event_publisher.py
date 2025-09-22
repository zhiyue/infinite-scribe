"""
EventPublisher - 领域事件发布器

负责将命令状态更新等领域事件发布到 EventBridge，实现解耦的事件驱动架构。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

from src.common.utils.datetime_utils import utc_now
from src.db.sql.session import create_sql_session
from src.models.workflow import EventOutbox
from src.schemas.enums import OutboxStatus

logger = logging.getLogger(__name__)


class DomainEventPublisher(ABC):
    """领域事件发布器抽象接口"""

    @abstractmethod
    async def publish_event(self, event: dict[str, Any]) -> bool:
        """发布领域事件

        Args:
            event: 领域事件数据

        Returns:
            发布是否成功
        """
        pass


class EventBridgePublisher(DomainEventPublisher):
    """EventBridge 事件发布器实现"""

    def __init__(self, event_outbox_service=None):
        """初始化发布器

        Args:
            event_outbox_service: 事件输出箱服务，用于可靠事件发布
        """
        self.event_outbox = event_outbox_service

    async def publish_event(self, event: dict[str, Any]) -> bool:
        """发布事件到 EventBridge

        Args:
            event: 领域事件数据

        Returns:
            发布是否成功
        """
        try:
            # enriched 事件数据
            enriched_event = self._enrich_event(event)

            # 验证事件格式
            if not self._validate_event(enriched_event):
                logger.error("Invalid event format", extra={"event": enriched_event})
                return False

            # 如果有 outbox 服务，使用可靠发布
            if self.event_outbox:
                return await self._publish_via_outbox(enriched_event)
            else:
                # 直接发布（开发环境或简化场景）
                return await self._publish_direct(enriched_event)

        except Exception as e:
            logger.error(f"Failed to publish event: {e}", extra={"event": event}, exc_info=True)
            return False

    def _enrich_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """丰富事件数据，添加元信息

        Args:
            event: 原始事件数据

        Returns:
            丰富后的事件数据
        """
        now = utc_now()

        enriched = {
            **event,
            "event_id": event.get("event_id", str(uuid4())),
            "timestamp": event.get("timestamp", now.isoformat()),
            "version": event.get("version", 1),
            "source": event.get("source", "command-status-updater"),
            "metadata": {
                **event.get("metadata", {}),
                "published_at": now.isoformat(),
                "publisher": "EventBridgePublisher",
            },
        }

        return enriched

    def _validate_event(self, event: dict[str, Any]) -> bool:
        """验证事件格式

        Args:
            event: 事件数据

        Returns:
            格式是否有效
        """
        required_fields = ["event_type", "event_id", "timestamp"]

        for field in required_fields:
            if field not in event:
                logger.warning(f"Missing required field '{field}' in event")
                return False

        # 验证事件类型格式
        event_type = event.get("event_type", "")
        if not event_type or not isinstance(event_type, str):
            logger.warning("Invalid event_type format")
            return False

        return True

    async def _publish_via_outbox(self, event: dict[str, Any]) -> bool:
        """通过 Outbox 模式可靠发布事件

        Args:
            event: 事件数据

        Returns:
            发布是否成功
        """
        try:
            # 使用 outbox 服务确保可靠发布（若提供外部服务）
            if self.event_outbox is not None:
                success = await self.event_outbox.store_event(event)
                if success:
                    logger.debug(f"Event stored in outbox by service: {event.get('event_id')}")
                    return True
                else:
                    logger.error(f"Failed to store event in outbox service: {event.get('event_id')}")
                    return False

            # 直接写入 EventOutbox（与 ConversationOutboxManager 保持一致的扁平化结构）
            # Choose first configured domain topic for EventBridge
            try:
                from src.core.config import settings
                topic = (settings.eventbridge.domain_topics[0] if settings.eventbridge.domain_topics else "genesis.session.events")
            except Exception:
                topic = "genesis.session.events"
            aggregate_id = str(event.get("aggregate_id"))
            payload = {
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "aggregate_type": event.get("aggregate_type", "Session"),
                "aggregate_id": aggregate_id,
                "metadata": event.get("metadata") or {},
            }
            # 合并业务 payload
            if event.get("payload"):
                try:
                    payload.update(event["payload"])  # type: ignore[arg-type]
                except Exception:
                    payload["payload"] = event.get("payload")

            headers = {
                "event_type": event.get("event_type"),
                "version": event.get("version", 1),
                "correlation_id": (event.get("metadata", {}) or {}).get("correlation_id"),
            }

            async with create_sql_session() as db:
                out = EventOutbox(
                    topic=topic,
                    key=aggregate_id,
                    partition_key=aggregate_id,
                    payload=payload,
                    headers=headers,
                    status=OutboxStatus.PENDING,
                )
                db.add(out)
                await db.flush()
                logger.debug(
                    "EventOutbox row created",
                    extra={"row_id": str(out.id), "topic": topic, "event_type": payload.get("event_type")},
                )
                return True

        except Exception as e:
            logger.error(f"Failed to store event in outbox: {e}", exc_info=True)
            return False

    async def _publish_direct(self, event: dict[str, Any]) -> bool:
        """直接发布事件（用于开发或简化场景）

        Args:
            event: 事件数据

        Returns:
            发布是否成功
        """
        try:
            # TODO: 实际实现中，这里应该调用真正的 EventBridge 或 Kafka
            # 现在只是记录日志作为占位符
            logger.info(
                f"Publishing event: {event.get('event_type')}",
                extra={
                    "event_id": event.get("event_id"),
                    "event_type": event.get("event_type"),
                    "aggregate_id": event.get("aggregate_id"),
                    "source": event.get("source"),
                },
            )

            # 模拟发布成功
            return True

        except Exception as e:
            logger.error(f"Failed to publish event directly: {e}", exc_info=True)
            return False


class NoOpEventPublisher(DomainEventPublisher):
    """无操作事件发布器，用于测试或禁用事件发布的场景"""

    async def publish_event(self, event: dict[str, Any]) -> bool:
        """不执行任何操作的事件发布

        Args:
            event: 事件数据

        Returns:
            总是返回 True
        """
        logger.debug(f"NoOp event publish: {event.get('event_type', 'unknown')}")
        return True
