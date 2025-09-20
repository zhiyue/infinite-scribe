"""Outbox管理模块

处理编排器的领域事件持久化和能力任务入队功能。
为领域事件和outbox条目提供幂等性操作。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, select

from src.agents.message import encode_message
from src.common.events.config import build_event_type, get_aggregate_type, get_domain_topic
from src.db.sql.session import create_sql_session
from src.models.event import DomainEvent
from src.models.workflow import EventOutbox
from src.schemas.enums import OutboxStatus


class DomainEventIdempotencyChecker:
    """领域事件幂等性检查器，处理领域事件的幂等性验证。"""

    @staticmethod
    async def check_existing_domain_event(correlation_id: str, evt_type: str, db_session) -> DomainEvent | None:
        """通过correlation_id和事件类型检查领域事件是否已存在。

        Args:
            correlation_id: 关联ID字符串
            evt_type: 事件类型字符串
            db_session: 数据库会话对象

        Returns:
            如果存在则返回DomainEvent对象，否则返回None
        """
        try:
            return await db_session.scalar(
                select(DomainEvent).where(
                    and_(
                        DomainEvent.correlation_id == UUID(str(correlation_id)),
                        DomainEvent.event_type == evt_type,
                    )
                )
            )
        except Exception:
            # 如果correlation_id是无效的UUID或其他错误，视为没有现有事件
            return None


class DomainEventCreator:
    """领域事件创建器，处理领域事件的创建逻辑。"""

    def __init__(self, logger):
        """初始化领域事件创建器。

        Args:
            logger: 日志记录器实例
        """
        self.log = logger
        self.idempotency_checker = DomainEventIdempotencyChecker()

    async def create_or_get_domain_event(
        self,
        scope_type: str,
        session_id: str,
        event_action: str,
        payload: dict[str, Any],
        correlation_id: str | None,
        causation_id: str | None,
        db_session,
    ) -> DomainEvent:
        """创建新的领域事件，或如果通过correlation_id + 事件类型找到现有事件则返回现有事件。

        Args:
            scope_type: 作用域类型
            session_id: 会话ID
            event_action: 事件动作
            payload: 有效负载数据
            correlation_id: 关联ID
            causation_id: 因果ID
            db_session: 数据库会话对象

        Returns:
            创建或获取的DomainEvent对象
        """
        evt_type = build_event_type(scope_type, event_action)
        aggregate_type = get_aggregate_type(scope_type)

        # 检查现有领域事件（幂等性）
        existing = None
        if correlation_id:
            self.log.debug(
                "orchestrator_checking_existing_domain_event",
                correlation_id=correlation_id,
                evt_type=evt_type,
            )

            existing = await self.idempotency_checker.check_existing_domain_event(correlation_id, evt_type, db_session)

            if existing:
                self.log.info(
                    "orchestrator_domain_event_already_exists",
                    correlation_id=correlation_id,
                    evt_type=evt_type,
                    existing_event_id=str(existing.event_id),
                    existing_aggregate_id=existing.aggregate_id,
                )
                return existing
            else:
                self.log.debug(
                    "orchestrator_no_existing_domain_event_found",
                    correlation_id=correlation_id,
                    evt_type=evt_type,
                )

        # 创建新的领域事件
        self.log.info(
            "orchestrator_creating_new_domain_event",
            evt_type=evt_type,
            aggregate_type=aggregate_type,
            aggregate_id=session_id,
            correlation_id=correlation_id,
        )

        domain_event = DomainEvent(
            event_type=evt_type,
            aggregate_type=aggregate_type,
            aggregate_id=str(session_id),
            payload=payload,
            correlation_id=UUID(str(correlation_id)) if correlation_id else None,
            causation_id=UUID(str(causation_id)) if causation_id else None,
            event_metadata={"source": "orchestrator"},
        )
        db_session.add(domain_event)
        await db_session.flush()

        self.log.info(
            "orchestrator_domain_event_created",
            event_id=str(domain_event.event_id),
            evt_type=evt_type,
            aggregate_id=session_id,
        )

        return domain_event


class OutboxEntryCreator:
    """Outbox条目创建器，处理outbox条目的创建逻辑。"""

    def __init__(self, logger):
        """初始化outbox条目创建器。

        Args:
            logger: 日志记录器实例
        """
        self.log = logger

    async def create_or_get_outbox_entry(
        self,
        domain_event: DomainEvent,
        scope_type: str,
        session_id: str,
        correlation_id: str | None,
        db_session,
    ) -> EventOutbox:
        """创建outbox条目，或如果通过领域事件ID找到现有条目则返回现有条目。

        Args:
            domain_event: 领域事件对象
            scope_type: 作用域类型
            session_id: 会话ID
            correlation_id: 关联ID
            db_session: 数据库会话对象

        Returns:
            创建或获取的EventOutbox对象
        """
        topic = get_domain_topic(scope_type)

        # 检查现有outbox条目（通过领域事件ID进行幂等性检查）
        self.log.debug(
            "orchestrator_checking_outbox_entry",
            domain_event_id=str(domain_event.event_id),
        )

        existing_outbox = await self._check_existing_outbox(domain_event.event_id, db_session)
        if existing_outbox:
            self.log.debug(
                "orchestrator_outbox_entry_already_exists",
                event_id=str(domain_event.event_id),
                existing_status=existing_outbox.status.value
                if hasattr(existing_outbox.status, "value")
                else str(existing_outbox.status),
            )
            return existing_outbox

        # 创建新的outbox条目
        self.log.info(
            "orchestrator_creating_outbox_entry",
            event_id=str(domain_event.event_id),
            topic=topic,
            key=session_id,
        )

        outbox_payload = self._build_outbox_payload(domain_event)

        outbox_entry = EventOutbox(
            id=domain_event.event_id,
            topic=topic,
            key=str(session_id),
            partition_key=str(session_id),
            payload=outbox_payload,
            headers={
                "event_type": domain_event.event_type,
                "version": 1,
                "correlation_id": str(correlation_id) if correlation_id else None,
            },
            status=OutboxStatus.PENDING,
        )
        db_session.add(outbox_entry)

        self.log.info(
            "orchestrator_outbox_entry_created",
            event_id=str(domain_event.event_id),
            topic=topic,
            status=outbox_entry.status.value if hasattr(outbox_entry.status, "value") else str(outbox_entry.status),
        )

        return outbox_entry

    async def _check_existing_outbox(self, event_id: UUID, db_session) -> EventOutbox | None:
        """检查给定event_id的outbox条目是否已存在。

        Args:
            event_id: 事件ID
            db_session: 数据库会话对象

        Returns:
            如果存在则返回EventOutbox对象，否则返回None
        """
        return await db_session.scalar(select(EventOutbox).where(EventOutbox.id == event_id))

    def _build_outbox_payload(self, domain_event: DomainEvent) -> dict:
        """从领域事件构建outbox有效负载。

        Args:
            domain_event: 领域事件对象

        Returns:
            构建的有效负载字典
        """
        # 扁平化有效负载结构以避免双重嵌套 - 确保下游消费者能正确解析数据
        outbox_payload = {
            "event_id": str(domain_event.event_id),
            "event_type": domain_event.event_type,
            "aggregate_type": domain_event.aggregate_type,
            "aggregate_id": domain_event.aggregate_id,
            "metadata": domain_event.event_metadata or {},
        }
        # 直接合并领域事件有效负载，而不是嵌套在"payload"键下
        outbox_payload.update(domain_event.payload or {})

        # 添加created_at作为下游时间戳的备用值
        try:
            if getattr(domain_event, "created_at", None):
                outbox_payload["created_at"] = domain_event.created_at.isoformat()  # type: ignore[attr-defined]
        except Exception:
            pass

        return outbox_payload


class CapabilityTaskEnqueuer:
    """能力任务入队器，处理能力任务的入队逻辑。"""

    def __init__(self, logger, agent_name: str):
        """初始化能力任务入队器。

        Args:
            logger: 日志记录器实例
            agent_name: 代理名称
        """
        self.log = logger
        self.agent_name = agent_name

    async def enqueue_capability_task(self, capability_message: dict[str, Any], correlation_id: str | None) -> None:
        """将能力任务入队到EventOutbox，供relay发布到Kafka。

        Args:
            capability_message: 能力消息字典
            correlation_id: 关联ID
        """
        # 提取路由信息
        topic = capability_message.get("_topic")
        key = capability_message.get("_key") or capability_message.get("session_id")

        if not topic:
            self.log.warning("capability_task_enqueue_skipped", reason="missing_topic", msg=capability_message)
            return

        # 构建信封有效负载（剥离路由键）
        result_payload = {k: v for k, v in capability_message.items() if k not in {"_topic", "_key"}}
        envelope = encode_message(self.agent_name, result_payload, correlation_id=correlation_id, retries=0)

        await self._create_outbox_entry(envelope, correlation_id, topic, key)

    async def _create_outbox_entry(
        self,
        envelope: dict,
        correlation_id: str | None,
        topic: str,
        key: Any,
    ) -> None:
        """为能力任务创建outbox条目。

        Args:
            envelope: 信封数据
            correlation_id: 关联ID
            topic: 主题名称
            key: 分区键
        """
        async with create_sql_session() as db:
            outbox_entry = EventOutbox(
                topic=topic,
                key=str(key) if key is not None else None,
                partition_key=str(key) if key is not None else None,
                payload=envelope,
                headers={
                    "type": envelope.get("type"),
                    "version": envelope.get("version"),
                    "correlation_id": correlation_id,
                    "agent": self.agent_name,
                },
                status=OutboxStatus.PENDING,
            )
            db.add(outbox_entry)
            # 刷新以获取日志ID
            await db.flush()

            self.log.debug(
                "capability_task_outbox_created",
                outbox_id=str(outbox_entry.id),
                topic=topic,
                key=key,
            )


class OutboxManager:
    """统一的outbox管理接口，提供领域事件持久化和能力任务入队的统一操作。"""

    def __init__(self, logger, agent_name: str):
        """初始化outbox管理器。

        Args:
            logger: 日志记录器实例
            agent_name: 代理名称
        """
        self.log = logger
        self.domain_event_creator = DomainEventCreator(logger)
        self.outbox_entry_creator = OutboxEntryCreator(logger)
        self.capability_enqueuer = CapabilityTaskEnqueuer(logger, agent_name)

    async def persist_domain_event(
        self,
        *,
        scope_type: str,
        session_id: str,
        event_action: str,
        payload: dict[str, Any],
        correlation_id: str | None,
        causation_id: str | None = None,
    ) -> None:
        """持久化领域事件和outbox（通过correlation_id + 事件类型保证幂等性）。

        Args:
            scope_type: 作用域类型
            session_id: 会话ID
            event_action: 事件动作
            payload: 有效负载数据
            correlation_id: 关联ID
            causation_id: 因果ID
        """
        evt_type = build_event_type(scope_type, event_action)
        aggregate_type = get_aggregate_type(scope_type)
        topic = get_domain_topic(scope_type)

        self.log.info(
            "orchestrator_persisting_domain_event",
            scope_type=scope_type,
            session_id=session_id,
            event_action=event_action,
            correlation_id=correlation_id,
            evt_type=evt_type,
            aggregate_type=aggregate_type,
            topic=topic,
            payload_keys=list(payload.keys()) if payload else [],
        )

        async with create_sql_session() as db:
            # 创建或获取领域事件（幂等性）
            domain_event = await self.domain_event_creator.create_or_get_domain_event(
                scope_type, session_id, event_action, payload, correlation_id, causation_id, db
            )

            # 创建或获取outbox条目（幂等性）
            await self.outbox_entry_creator.create_or_get_outbox_entry(
                domain_event, scope_type, session_id, correlation_id, db
            )

        self.log.info(
            "orchestrator_domain_event_persist_completed",
            evt_type=evt_type,
            event_id=str(domain_event.event_id),
            session_id=session_id,
            correlation_id=correlation_id,
        )

    async def enqueue_capability_task(self, *, capability_message: dict[str, Any], correlation_id: str | None) -> None:
        """将能力任务入队到outbox，供relay发布到Kafka。

        Args:
            capability_message: 能力消息字典
            correlation_id: 关联ID
        """
        await self.capability_enqueuer.enqueue_capability_task(capability_message, correlation_id)
