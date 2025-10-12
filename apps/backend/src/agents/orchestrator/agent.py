"""领域编排器代理

消费领域总线和能力事件，并执行以下操作：
- 将命令触发的领域事件（Command.Received）投影为领域事实（*Requested）
- 向相应的能力主题发出能力任务
- 将能力结果投影为领域事实（例如：*Proposed）

注意事项：
- 领域事实通过DomainEvent + EventOutbox（数据库直写）持久化，
  不直接生产到Kafka。Outbox relay将发布它们。
- 能力任务使用BaseAgent生产者发送到Kafka（代理总线）。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.agents.orchestrator.interfaces import (
    CapabilityEventProcessor,
    DefaultOrchestratorComponentFactory,
    DomainEventProcessor,
    OrchestratorComponentFactory,
    OutboxManager,
    TaskManager,
)


class OrchestratorAgent(BaseAgent):
    """编排器代理，负责协调领域事件和能力事件的处理流程。

    架构角色：
    - 作为领域层和能力层之间的协调者
    - 实现事件驱动架构中的编排模式（Orchestration Pattern）
    - 确保领域事件和能力任务之间的因果关系追踪
    """

    def __init__(
        self,
        name: str,
        consume_topics: list[str],
        produce_topics: list[str] | None = None,
        component_factory: OrchestratorComponentFactory | None = None,
    ) -> None:
        """初始化编排器代理。

        Args:
            name: 代理名称
            consume_topics: 消费的主题列表
            produce_topics: 生产的主题列表（可选）
            component_factory: 组件工厂（可选，默认使用DefaultOrchestratorComponentFactory）
        """
        super().__init__(name=name, consume_topics=consume_topics, produce_topics=produce_topics)

        # 使用工厂模式和依赖注入，遵循依赖反转原则(DIP)
        # 这样做的好处：
        # 1. 便于单元测试时注入mock对象
        # 2. 解耦组件创建逻辑，提高可维护性
        # 3. 支持不同环境下使用不同的实现策略
        factory = component_factory or DefaultOrchestratorComponentFactory()
        self.domain_processor: DomainEventProcessor = factory.create_domain_processor(self.log)
        self.capability_processor: CapabilityEventProcessor = factory.create_capability_processor(self.log)
        self.task_manager: TaskManager = factory.create_task_manager(self.log)
        self.outbox_manager: OutboxManager = factory.create_outbox_manager(self.log, self.name)

    async def process_message(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """通过路由到适当的处理器来处理消息。

        消息识别策略：
        - 通过消费的 topic 识别消息类型（显式路由）
        - 领域事件：来自 genesis.session.events 等领域事件 topic
        - 能力事件：来自能力代理的 topic，包含 type 字段

        这种设计使路由决策明确且可预测，便于理解和维护。

        Args:
            message: 要处理的消息字典
            context: 可选的上下文信息字典，包含 topic 等元数据

        Returns:
            处理结果字典或None
        """
        self.log.info(
            "orchestrator_message_received",
            message_keys=list(message.keys()),
            has_context=context is not None,
            context_keys=list(context.keys()) if context else [],
        )

        # 从上下文中获取 topic，用于路由决策
        topic = (context or {}).get("topic", "")

        # 根据 topic 判断是否为领域事件
        # 领域事件来自特定的领域事件 topic（如 genesis.session.events）
        if topic == "genesis.session.events":
            # 提取领域事件信息用于日志和可观测性
            system_data = message.get("system", {})
            event_type = system_data.get("event_type")
            aggregate_id = system_data.get("aggregate_id")

            self.log.info(
                "orchestrator_processing_domain_event",
                topic=topic,
                event_type=event_type,
                aggregate_id=aggregate_id,
                has_payload=bool(message.get("data")),
                schema_version=message.get("schema_version", "v1"),
            )
            return await self._handle_domain_event(message, context or {})

        # 能力事件识别 - 来自能力代理的消息
        # 能力事件可能来自不同的能力代理，通过 type 字段标识具体能力
        msg_type = (context or {}).get("meta", {}).get("type") or message.get("type")
        if msg_type:
            self.log.info(
                "orchestrator_processing_capability_event",
                msg_type=msg_type,
                topic=topic,
                has_data=bool(message.get("data")),
            )
            return await self._handle_capability_event(msg_type, message, context or {})

        # 无法识别的消息类型 - 记录但不抛出异常，保持系统健壮性
        self.log.debug(
            "orchestrator_ignored_message",
            reason="unknown_topic_or_missing_type",
            topic=topic,
        )
        return None

    async def _handle_domain_event(
        self, evt: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """使用领域事件处理器处理领域事件。

        处理流程：
        1. 将Command.Received投影为领域事实（如StoryDevelopment.Requested）
        2. 持久化领域事件到数据库（Outbox模式确保最终一致性）
        3. 创建异步任务记录以便追踪
        4. 如果需要，发送能力任务到对应的能力代理

        设计决策：
        - 使用Outbox模式而非直接发布到Kafka，避免双写问题
        - Outbox relay会异步将事件发布到Kafka，保证至少一次交付
        - 任务创建可能失败但不影响事件持久化，通过日志记录便于排查

        Args:
            evt: 领域事件字典
            context: 可选的上下文信息字典

        Returns:
            处理结果字典或None
        """
        from src.common.events.mapping import normalize_task_type

        # 步骤1：通过领域处理器处理事件，完成事件投影和映射
        processing_result = await self.domain_processor.handle_domain_event(evt, context)

        if not processing_result:
            return None

        # 提取处理结果中的关键信息
        correlation_id = processing_result["correlation_id"]
        scope_type = processing_result["scope_type"]
        aggregate_id = processing_result["aggregate_id"]
        mapping = processing_result["mapping"]
        enriched_payload = processing_result["enriched_payload"]
        causation_id = processing_result["causation_id"]
        metadata = processing_result.get("metadata")

        # 步骤2：持久化领域事件 - 使用Outbox模式确保事件最终一致性
        # 为什么使用Outbox而非直接发布：
        # 1. 避免领域事件持久化和Kafka发布之间的分布式事务问题
        # 2. 通过数据库事务保证事件持久化的原子性
        # 3. Outbox relay负责将事件异步发布到Kafka，提供重试机制
        try:
            await self.outbox_manager.persist_domain_event(
                scope_type=scope_type,
                session_id=aggregate_id,
                event_action=mapping.requested_action,
                payload=enriched_payload,
                correlation_id=correlation_id,
                causation_id=causation_id,
                metadata=metadata,
            )
            self.log.info(
                "orchestrator_domain_event_persisted",
                scope_type=scope_type,
                event_action=mapping.requested_action,
                aggregate_id=aggregate_id,
            )
        except Exception as e:
            # 领域事件持久化失败是严重错误，必须抛出异常终止处理
            # 这确保了消息会被重新投递，避免事件丢失
            self.log.error(
                "orchestrator_domain_event_persist_failed",
                scope_type=scope_type,
                event_action=mapping.requested_action,
                aggregate_id=aggregate_id,
                error=str(e),
                exc_info=True,
            )
            raise

        # 步骤3和4：创建异步任务并将能力任务入队
        # 注意：仅当mapping包含capability_message时才执行
        # 某些领域命令（如状态查询）不需要触发能力任务
        if mapping.capability_message:
            try:
                # 创建异步任务记录，用于追踪任务状态和可观测性
                await self.task_manager.create_async_task(
                    correlation_id=correlation_id,
                    session_id=aggregate_id,
                    task_type=normalize_task_type(mapping.capability_message.get("type", "")),
                    input_data=mapping.capability_message.get("input") or {},
                )
                # 将能力任务入队，最终会通过BaseAgent的生产者发送到Kafka
                await self.outbox_manager.enqueue_capability_task(
                    capability_message=mapping.capability_message,
                    correlation_id=correlation_id,
                )
                self.log.info(
                    "orchestrator_capability_task_enqueued",
                    topic=mapping.capability_message.get("_topic"),
                    correlation_id=correlation_id,
                )
            except Exception as e:
                # 任务创建失败不应阻断流程，因为领域事件已经持久化
                # 通过日志记录便于后续人工介入或补偿处理
                self.log.warning("async_task_create_failed", correlation_id=correlation_id, error=str(e), exc_info=True)
        else:
            # 记录仅状态变更的命令，便于理解系统行为
            self.log.info(
                "orchestrator_state_only_command_processed",
                requested_action=mapping.requested_action,
                correlation_id=correlation_id,
                message="命令仅触发状态变更，无需能力任务",
            )

        return None

    async def _handle_capability_event(
        self, msg_type: str, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """使用能力事件处理器处理能力事件。

        能力事件处理流程：
        1. 识别能力事件类型（如意图分类结果、故事开发结果等）
        2. 将能力结果投影为领域事实（如StoryDevelopment.Proposed）
        3. 完成对应的异步任务
        4. 如果需要，触发后续的能力任务（链式调用）

        这种设计支持能力代理之间的协作，实现复杂的业务流程编排。

        Args:
            msg_type: 消息类型
            message: 消息内容字典
            context: 上下文信息字典

        Returns:
            处理结果字典或None
        """
        # 通过能力处理器处理事件，生成需要执行的操作
        processing_result = await self.capability_processor.handle_capability_event(msg_type, message, context)

        if not processing_result:
            return None

        # 执行处理器指定的操作（持久化领域事件、完成任务、触发后续任务等）
        action = processing_result.action
        return await self._execute_event_action(action)

    async def _execute_event_action(self, action: Any) -> dict[str, Any] | None:
        """使用管理器执行事件处理器指定的操作。

        操作执行顺序设计：
        1. 先持久化领域事件（状态变更）
        2. 再完成异步任务（标记任务完成）
        3. 最后触发后续能力任务（如果有）

        这个顺序确保了：
        - 即使后续步骤失败，状态变更也已持久化
        - 任务完成标记在状态变更之后，保证一致性
        - 后续任务触发失败不影响当前事件的处理

        Args:
            action: 要执行的事件操作对象

        Returns:
            执行结果字典或None
        """
        self.log.info(
            "orchestrator_executing_event_action",
            has_domain_event=bool(action.domain_event),
            has_task_completion=bool(action.task_completion),
            has_capability_message=bool(action.capability_message),
        )

        # 操作1：持久化领域事件（如果指定）
        # 这是最关键的操作，失败则抛出异常终止处理
        if action.domain_event:
            try:
                await self.outbox_manager.persist_domain_event(**action.domain_event)
                self.log.info(
                    "orchestrator_domain_event_persisted_success", event_action=action.domain_event.get("event_action")
                )
            except Exception as e:
                # 领域事件持久化失败是不可恢复的错误，必须抛出
                self.log.error("orchestrator_domain_event_persist_failed", error=str(e), exc_info=True)
                raise

        # 操作2：完成异步任务（如果指定）
        # 任务完成失败记录日志但不抛出异常，避免影响后续流程
        if action.task_completion:
            try:
                await self.task_manager.complete_async_task(**action.task_completion)
                self.log.info(
                    "orchestrator_async_task_completed_success",
                    correlation_id=action.task_completion.get("correlation_id"),
                )
            except Exception as e:
                # 任务完成失败不应阻断流程，因为领域事件已经持久化
                # 可以通过定时任务补偿或人工介入处理
                self.log.error("orchestrator_async_task_complete_failed", error=str(e), exc_info=True)

        # 操作3：将后续能力任务入队（如果指定）
        # 支持能力任务的链式调用，实现复杂业务流程的编排
        if action.capability_message:
            try:
                # 为后续能力任务创建异步任务记录，保持可观测性和一致性
                from src.common.events.mapping import normalize_task_type

                # 从领域事件或能力消息中提取相关ID信息
                correlation_id = (action.domain_event or {}).get("correlation_id")
                session_id = action.capability_message.get("session_id") or (action.domain_event or {}).get(
                    "session_id", ""
                )
                await self.task_manager.create_async_task(
                    correlation_id=correlation_id,
                    session_id=session_id,
                    task_type=normalize_task_type(action.capability_message.get("type", "")),
                    input_data=action.capability_message.get("input") or {},
                )

                # 将后续能力任务入队
                await self.outbox_manager.enqueue_capability_task(
                    capability_message=action.capability_message,
                    correlation_id=correlation_id,
                )
                self.log.info("orchestrator_followup_task_enqueued", topic=action.capability_message.get("_topic"))
            except Exception as e:
                # 后续任务入队失败不应阻断当前处理流程
                # 可以通过监控告警或补偿机制处理
                self.log.error("orchestrator_followup_task_enqueue_failed", error=str(e), exc_info=True)

        return None
