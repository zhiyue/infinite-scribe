"""Outbox管理模块

处理编排器的领域事件持久化和能力任务入队功能。
为领域事件和outbox条目提供幂等性操作。

核心功能：
1. 领域事件持久化：将业务事件保存到domain_events表
2. Outbox条目创建：创建待发布的消息到event_outbox表（Outbox Pattern）
3. 能力任务入队：将能力任务消息入队供relay进程发布

设计模式：
- Outbox Pattern：通过本地事务保证领域事件和消息发布的最终一致性
- 幂等性保证：通过correlation_id + event_type确保重复请求不会创建多个事件
- 事务边界：领域事件和outbox条目在同一事务中创建，保证原子性

幂等性策略：
- 领域事件：通过(correlation_id, event_type)唯一索引保证幂等
- Outbox条目：通过event_id主键保证幂等（event_id即domain_event.event_id）
- 查询优先：创建前先查询，如果已存在则返回现有记录

错误处理原则：
- UUID转换失败：使用None而非抛出异常，保证系统可用性
- 数据库查询失败：假定不存在并继续，优先保证系统可用性
- 重复创建保护：通过幂等性检查避免重复数据
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
    """领域事件幂等性检查器，处理领域事件的幂等性验证。

    设计目的：
    确保相同的业务请求（通过correlation_id标识）不会重复创建领域事件。
    这对于保证系统的幂等性至关重要，特别是在以下场景：
    - 客户端重试请求
    - 消息队列重复投递
    - 分布式事务重试
    - 网络超时后的重新提交

    检查策略：
    - 使用(correlation_id, event_type)组合作为唯一性判断依据
    - 采用"查询优先"模式，在创建前先检查是否已存在
    - 容错处理：查询失败时假定不存在，优先保证系统可用性

    Note: 这是一个无状态的工具类，使用@staticmethod避免不必要的实例化。
    """

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
            # 安全地转换correlation_id为UUID，防止非法格式导致查询失败
            safe_correlation_id = safe_uuid_conversion(correlation_id)
            if safe_correlation_id is None:
                # 如果correlation_id无法转换为UUID，视为没有现有事件
                # 这避免了因格式错误导致查询异常，同时允许系统继续处理
                return None

            # 使用correlation_id和事件类型的组合来确保幂等性
            # 这确保相同的业务操作不会重复创建领域事件
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
            # 采用"假定不存在"策略而非抛出异常：
            # 1. 避免因网络抖动或临时数据库问题导致整个流程中断
            # 2. 最坏情况是创建重复事件，这可以通过下游的幂等性检查处理
            # 3. 优先保证系统可用性而非绝对的数据一致性
            return None


class DomainEventCreator:
    """领域事件创建器，处理领域事件的创建逻辑。

    职责：
    1. 创建新的领域事件实例（DomainEvent）
    2. 提供幂等性检查（通过correlation_id + event_type）
    3. 构建事件元数据（从payload和metadata参数中提取）
    4. 处理UUID转换和错误恢复（采用降级策略）

    设计原则：
    - 幂等性优先：相同的correlation_id + event_type只创建一次
    - 容错设计：UUID转换失败时使用None，不中断流程
    - 元数据提升：将关键业务字段从payload提升到metadata层
    - 单一职责：只负责领域事件的创建，不涉及outbox
    """

    def __init__(self, logger):
        """初始化领域事件创建器。

        Args:
            logger: 日志记录器实例
        """
        self.log = logger
        # 注入幂等性检查器，实现职责分离
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
        # 构建标准化的事件类型和聚合类型
        # 例如：scope_type="inquiry", event_action="started" -> evt_type="inquiry.started"
        evt_type = build_event_type(scope_type, event_action)
        aggregate_type = get_aggregate_type(scope_type)

        # 检查现有领域事件（幂等性保证）
        # 通过correlation_id确保相同的业务请求不会创建多个领域事件
        existing = None
        if correlation_id:
            self.log.debug(
                "orchestrator_checking_existing_domain_event",
                correlation_id=correlation_id,
                evt_type=evt_type,
            )

            existing = await self.idempotency_checker.check_existing_domain_event(correlation_id, evt_type, db_session)

            if existing:
                # 找到现有事件，直接返回以避免重复创建
                # 这是幂等性的关键：相同的correlation_id + event_type只产生一个事件
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
        # 使用安全转换避免因格式错误导致数据库插入失败
        safe_correlation_id = safe_uuid_conversion(correlation_id)
        safe_causation_id = safe_uuid_conversion(causation_id)

        # 记录UUID转换失败的情况，便于追踪数据质量问题
        # 采用降级策略：使用None而非抛出异常，保证系统继续运行
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
        # 元数据与业务payload分离的设计目的：
        # 1. 快速查询和过滤（无需解析payload）
        # 2. 统一的监控和追踪维度
        # 3. 保持payload的纯粹性（只包含业务数据）
        event_metadata = EventMetadata(source="orchestrator").model_dump(exclude_none=True)

        # 从显式metadata参数中提取关键字段
        # 允许调用方直接传递trace_id、span_id等追踪信息
        if metadata:
            event_metadata.update(metadata)

        # 从payload中提取关键业务字段到metadata
        # 目的：将常用的查询和过滤字段提升到metadata层，方便：
        # 1. 下游系统快速过滤事件（无需解析payload）
        # 2. 监控和告警系统按用户/小说维度统计
        # 3. 保持payload的纯粹性（只包含业务数据）
        if isinstance(payload, dict):
            # 提取用户ID，用于按用户维度的事件追踪和权限验证
            user_id = payload.get("user_id")
            if user_id:
                event_metadata["user_id"] = user_id

            # 提取小说ID，用于按小说维度的事件追踪和数据隔离
            novel_id = payload.get("novel_id")
            if novel_id:
                event_metadata["novel_id"] = novel_id

            # 提取时间戳，用于事件时序分析和调试
            timestamp = payload.get("timestamp")
            if timestamp:
                event_metadata["timestamp"] = timestamp

        # 创建领域事件实例
        # 使用session_id作为aggregate_id，建立事件与会话的强关联
        # 这使得可以按会话追踪所有相关事件
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
        # 立即flush以获取生成的event_id
        # 这对于后续创建outbox条目是必要的（outbox.id = event.event_id）
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
    """Outbox条目创建器，处理outbox条目的创建逻辑。

    职责：
    1. 从领域事件构建outbox条目（使用OutboxPayloadBuilder）
    2. 提供幂等性检查（通过event_id）
    3. 构建Kafka消息的headers（用于路由和过滤）

    设计原则：
    - 单一职责：只负责outbox条目的创建，不涉及领域事件
    - 依赖领域事件：outbox是领域事件的"投影"，用于消息发布
    - 幂等性保证：通过event_id确保一个领域事件只有一个outbox条目
    """

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
        # 由于outbox的ID直接使用domain_event.event_id，因此：
        # 1. 每个领域事件最多对应一个outbox条目
        # 2. 避免重复发布相同的事件到消息队列
        self.log.debug(
            "orchestrator_checking_outbox_entry",
            domain_event_id=str(domain_event.event_id),
        )

        existing_outbox = await self._check_existing_outbox(domain_event.event_id, db_session)
        if existing_outbox:
            # 找到现有条目，直接返回
            # 即使状态是FAILED，也不重新创建，而是让重试机制处理
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

        # 使用Builder模式构建分层的outbox payload
        # 将系统元数据和业务数据隔离，便于下游处理和版本演进
        outbox_payload = self._build_outbox_payload(domain_event)

        # 从event_metadata中提取user_id和novel_id用于headers
        # 目的：将关键业务标识放在headers中，支持：
        # 1. Kafka消费者快速过滤消息（无需解析payload）
        # 2. 消息路由和分区策略（例如按用户或小说ID分区）
        # 3. 监控和追踪系统按业务维度统计（用户活跃度、小说处理量等）
        user_id = None
        novel_id = None
        if domain_event.event_metadata:
            user_id = domain_event.event_metadata.get("user_id")
            novel_id = domain_event.event_metadata.get("novel_id")

        # 创建outbox条目
        # 关键设计决策：
        # 1. id使用domain_event.event_id，确保一对一映射和幂等性
        # 2. key和partition_key都使用session_id，保证同一会话的消息顺序性
        # 3. 初始状态为PENDING，等待relay进程发布到Kafka
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

    设计要点：
    1. 职责单一：只负责能力任务消息的格式化和入队
    2. 委托模式：实际的入队操作委托给BaseOutboxManager
    3. 消息封装：将capability_message转换为标准的消息信封格式

    与领域事件的区别：
    - 领域事件：记录已发生的业务事实，需要持久化到domain_events表
    - 能力任务：请求下游Agent执行操作，只需入队到event_outbox表

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
        # 避免重复实现outbox写入逻辑，保持代码DRY原则
        self.base_outbox = BaseOutboxManager(agent_name)

    async def enqueue_capability_task(self, capability_message: dict[str, Any], correlation_id: str | None) -> None:
        """将能力任务入队到EventOutbox，供relay发布到Kafka。

        Args:
            capability_message: 能力消息字典
            correlation_id: 关联ID
        """
        # 提取路由信息
        # _topic和_key是内部路由字段，不会发送到Kafka
        topic = capability_message.get("_topic")
        key = capability_message.get("_key") or capability_message.get("session_id")

        if not topic:
            # 缺少topic说明消息配置有误，记录警告但不中断流程
            # 这允许其他能力任务继续处理，避免单点故障
            self.log.warning("capability_task_enqueue_skipped", reason="missing_topic", msg=capability_message)
            return

        # 构建信封有效负载（剥离路由键）
        # 移除以_开头的内部字段，保持发送到Kafka的payload纯净
        result_payload = {k: v for k, v in capability_message.items() if k not in {"_topic", "_key"}}
        # 使用标准的消息编码格式，包含type、version、data等字段
        envelope = encode_message(self.agent_name, result_payload, correlation_id=correlation_id, retries=0)

        # 构建headers，用于消息追踪和路由
        # headers与payload分离，便于中间件和消费者快速过滤
        headers = EventOutboxHeaders(
            type=envelope.get("type"),
            version=envelope.get("version", 1),
            correlation_id=correlation_id,
            agent=self.agent_name,
        ).model_dump()

        # 使用BaseOutboxManager进行入队
        # 这提供了统一的消息持久化机制：
        # 1. 保证消息至少发送一次（at-least-once delivery）
        # 2. 支持重试和错误恢复
        # 3. 与relay进程解耦，提高系统可靠性
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

    架构设计：
    - 使用Facade模式统一多个内部组件的接口
    - 组合DomainEventCreator、OutboxEntryCreator、CapabilityTaskEnqueuer等专门组件
    - 组合BaseOutboxManager提供通用的消息入队能力

    职责分离：
    - 领域事件持久化：orchestrator特定的业务逻辑（DomainEventCreator + OutboxEntryCreator）
    - 能力任务入队：通用的消息入队逻辑（CapabilityTaskEnqueuer -> BaseOutboxManager）
    - 事务管理：在persist_domain_event中协调多个组件的操作

    使用场景：
    1. persist_domain_event：当业务操作完成时，持久化领域事件到数据库
    2. enqueue_capability_task：当需要调用能力Agent时，入队任务消息
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
        # 使用依赖注入模式传递logger，保证日志上下文一致性
        self.domain_event_creator = DomainEventCreator(logger)
        self.outbox_entry_creator = OutboxEntryCreator(logger)
        self.capability_enqueuer = CapabilityTaskEnqueuer(logger, agent_name)
        # 通用的消息入队能力（可用于非领域事件的消息）
        # BaseOutboxManager提供与领域事件无关的通用消息入队功能
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
        # 构建事件的标准化标识信息
        evt_type = build_event_type(scope_type, event_action)
        aggregate_type = get_aggregate_type(scope_type)
        topic = get_domain_topic(scope_type)

        # 从payload中提取元数据（如果没有显式提供）
        # 这是一个便利性功能，允许调用方只传递payload
        # 而不必重复构建metadata参数
        if not metadata:
            metadata = {}
            if isinstance(payload, dict):
                # 提取关键业务字段到metadata
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

        # 使用事务确保领域事件和outbox条目的原子性写入
        # 这是Outbox Pattern的核心：要么都成功，要么都失败
        # 避免领域事件已保存但outbox条目丢失的情况
        async with create_sql_session() as db:
            # 第一步：创建或获取领域事件（幂等性）
            # 如果相同的correlation_id + event_type已存在，返回现有事件
            domain_event = await self.domain_event_creator.create_or_get_domain_event(
                scope_type, session_id, event_action, payload, correlation_id, causation_id, db, metadata
            )

            # 第二步：创建或获取outbox条目（幂等性）
            # 如果相同的event_id已存在outbox，返回现有条目
            # 这确保即使重试也不会产生重复的消息发布
            await self.outbox_entry_creator.create_or_get_outbox_entry(
                domain_event, scope_type, session_id, correlation_id, db
            )
            # 事务自动提交（通过async context manager）

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
