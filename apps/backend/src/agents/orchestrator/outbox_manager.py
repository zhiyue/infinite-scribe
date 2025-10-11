"""Outbox管理模块

处理编排器的领域事件持久化和能力任务入队功能。
为领域事件和outbox条目提供幂等性操作。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, select

from src.agents.message import encode_message
from src.agents.orchestrator.types import EventMetadata, EventOutboxHeaders
from src.common.events.config import build_event_type, get_aggregate_type, get_domain_topic
from src.common.outbox import BaseOutboxManager, OutboxPayloadBuilder
from src.common.utils.uuid_utils import safe_uuid_conversion
from src.core.logging import get_logger
from src.db.sql.session import create_sql_session
from src.models.event import DomainEvent
from src.models.workflow import EventOutbox
from src.schemas.enums import OutboxStatus

logger = get_logger(__name__)


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
            # 安全地转换correlation_id为UUID
            safe_correlation_id = safe_uuid_conversion(correlation_id)
            if safe_correlation_id is None:
                # 如果correlation_id无法转换为UUID，视为没有现有事件
                return None

            return await db_session.scalar(
                select(DomainEvent).where(
                    and_(
                        DomainEvent.correlation_id == safe_correlation_id,
                        DomainEvent.event_type == evt_type,
                    )
                )
            )
        except Exception as e:
            # 记录数据库错误以提升可观测性
            logger.warning(
                "orchestrator_domain_event_check_failed",
                correlation_id=correlation_id,
                evt_type=evt_type,
                error=str(e),
                error_type=type(e).__name__,
                message="数据库查询失败，假定不存在现有事件以保证系统可用性",
            )
            # 如果发生任何其他错误，视为没有现有事件以保证系统可用性
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
        metadata: dict[str, Any] | None = None,
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
            metadata: 额外的元数据（如user_id、novel_id等）

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

        # 安全地转换correlation_id和causation_id为UUID
        safe_correlation_id = safe_uuid_conversion(correlation_id)
        safe_causation_id = safe_uuid_conversion(causation_id)

        # 记录UUID转换失败的情况
        if correlation_id and safe_correlation_id is None:
            self.log.warning(
                "orchestrator_invalid_correlation_id_format",
                correlation_id=correlation_id,
                message="将使用None替代非法UUID格式的correlation_id",
            )
        if causation_id and safe_causation_id is None:
            self.log.warning(
                "orchestrator_invalid_causation_id_format",
                causation_id=causation_id,
                message="将使用None替代非法UUID格式的causation_id",
            )

        # 构建事件元数据，包含必要的上下文信息
        event_metadata = EventMetadata(source="orchestrator").model_dump(exclude_none=True)

        # 从payload中提取并添加关键字段到metadata
        if metadata:
            event_metadata.update(metadata)

        # 从payload中提取user_id、novel_id、timestamp等字段到metadata
        if isinstance(payload, dict):
            # 提取user_id
            user_id = payload.get("user_id")
            if user_id:
                event_metadata["user_id"] = user_id

            # 提取novel_id
            novel_id = payload.get("novel_id")
            if novel_id:
                event_metadata["novel_id"] = novel_id

            # 提取timestamp
            timestamp = payload.get("timestamp")
            if timestamp:
                event_metadata["timestamp"] = timestamp

        domain_event = DomainEvent(
            event_type=evt_type,
            aggregate_type=aggregate_type,
            aggregate_id=str(session_id),
            payload=payload,
            correlation_id=safe_correlation_id,
            causation_id=safe_causation_id,
            event_metadata=event_metadata,
        )
        db_session.add(domain_event)
        await db_session.flush()

        self.log.info(
            "orchestrator_domain_event_created",
            event_id=str(domain_event.event_id),
            evt_type=evt_type,
            aggregate_id=session_id,
            metadata_keys=list(event_metadata.keys()),
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

        # 从event_metadata中提取user_id和其他字段
        user_id = None
        novel_id = None
        if domain_event.event_metadata:
            user_id = domain_event.event_metadata.get("user_id")
            novel_id = domain_event.event_metadata.get("novel_id")

        outbox_entry = EventOutbox(
            id=domain_event.event_id,
            topic=topic,
            key=str(session_id),
            partition_key=str(session_id),
            payload=outbox_payload,
            headers=EventOutboxHeaders(
                event_type=domain_event.event_type,
                correlation_id=str(correlation_id) if correlation_id else None,
                causation_id=str(domain_event.causation_id)
                if hasattr(domain_event, "causation_id") and domain_event.causation_id
                else None,
                aggregate_id=domain_event.aggregate_id,
                aggregate_type=domain_event.aggregate_type,
                content_type="application/json",
                schema_version="v1",
                timestamp=domain_event.created_at.isoformat()
                if hasattr(domain_event, "created_at") and domain_event.created_at
                else None,
                user_id=user_id,
                novel_id=novel_id,
                session_id=str(session_id),
                source=domain_event.event_metadata.get("source", "orchestrator")
                if domain_event.event_metadata
                else "orchestrator",
                trace_id=domain_event.event_metadata.get("trace_id") if domain_event.event_metadata else None,
            ).model_dump(),
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
        """使用Builder模式构建outbox有效负载，确保字段隔离。

        采用LLD规范的命名空间隔离设计：
        - system: 系统元数据（event_id, event_type, aggregate_*, metadata等）
        - data: 业务数据（原domain_event.payload内容）
        - schema_version: 版本标识（支持演进）

        Args:
            domain_event: 领域事件对象

        Returns:
            分层结构的payload字典
        """
        try:
            payload_envelope = OutboxPayloadBuilder.from_domain_event(domain_event).build()

            self.log.debug(
                "outbox_payload_built_with_builder",
                event_id=str(domain_event.event_id),
                event_type=domain_event.event_type,
                schema_version=payload_envelope.schema_version,
                has_business_data=bool(payload_envelope.data),
            )

            return payload_envelope.model_dump(exclude_none=True)

        except Exception as e:
            self.log.error(
                "outbox_payload_build_failed",
                event_id=str(domain_event.event_id),
                event_type=domain_event.event_type,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


class CapabilityTaskEnqueuer:
    """能力任务入队器，处理能力任务的入队逻辑。

    Note: 现在使用BaseOutboxManager进行消息入队，提供更可靠的消息持久化。
    """

    def __init__(self, logger, agent_name: str):
        """初始化能力任务入队器。

        Args:
            logger: 日志记录器实例
            agent_name: 代理名称
        """
        self.log = logger
        self.agent_name = agent_name
        # 使用通用的BaseOutboxManager进行消息入队
        self.base_outbox = BaseOutboxManager(agent_name)

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

        # 构建headers
        headers = EventOutboxHeaders(
            type=envelope.get("type"),
            version=envelope.get("version", 1),
            correlation_id=correlation_id,
            agent=self.agent_name,
        ).model_dump()

        # 使用BaseOutboxManager进行入队
        outbox_id = await self.base_outbox.enqueue_message(
            topic=topic,
            payload=envelope,
            key=str(key) if key is not None else None,
            correlation_id=correlation_id,
            headers=headers,
        )

        self.log.debug(
            "capability_task_outbox_created",
            outbox_id=outbox_id,
            topic=topic,
            key=key,
        )


class OutboxManager:
    """统一的outbox管理接口，提供领域事件持久化和能力任务入队的统一操作。

    Note: 组合使用BaseOutboxManager提供通用的消息入队能力，
    同时保留orchestrator特定的领域事件持久化逻辑。
    """

    def __init__(self, logger, agent_name: str):
        """初始化outbox管理器。

        Args:
            logger: 日志记录器实例
            agent_name: 代理名称
        """
        self.log = logger
        self.agent_name = agent_name
        # Orchestrator特定的领域事件处理组件
        self.domain_event_creator = DomainEventCreator(logger)
        self.outbox_entry_creator = OutboxEntryCreator(logger)
        self.capability_enqueuer = CapabilityTaskEnqueuer(logger, agent_name)
        # 通用的消息入队能力（可用于非领域事件的消息）
        self.base_outbox = BaseOutboxManager(agent_name)

    async def persist_domain_event(
        self,
        *,
        scope_type: str,
        session_id: str,
        event_action: str,
        payload: dict[str, Any],
        correlation_id: str | None,
        causation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """持久化领域事件和outbox（通过correlation_id + 事件类型保证幂等性）。

        Args:
            scope_type: 作用域类型
            session_id: 会话ID
            event_action: 事件动作
            payload: 有效负载数据
            correlation_id: 关联ID
            causation_id: 因果ID
            metadata: 额外的元数据（如user_id、novel_id等）
        """
        evt_type = build_event_type(scope_type, event_action)
        aggregate_type = get_aggregate_type(scope_type)
        topic = get_domain_topic(scope_type)

        # 从payload中提取元数据（如果没有提供）
        if not metadata:
            metadata = {}
            if isinstance(payload, dict):
                if "user_id" in payload:
                    metadata["user_id"] = payload["user_id"]
                if "novel_id" in payload:
                    metadata["novel_id"] = payload["novel_id"]
                if "timestamp" in payload:
                    metadata["timestamp"] = payload["timestamp"]

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
            metadata_keys=list(metadata.keys()) if metadata else [],
        )

        async with create_sql_session() as db:
            # 创建或获取领域事件（幂等性）
            domain_event = await self.domain_event_creator.create_or_get_domain_event(
                scope_type, session_id, event_action, payload, correlation_id, causation_id, db, metadata
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
