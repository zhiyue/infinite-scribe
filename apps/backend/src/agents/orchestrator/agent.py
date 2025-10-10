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
    """编排器代理，负责协调领域事件和能力事件的处理流程。"""

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

        # 使用依赖注入，遵循依赖反转原则(DIP)
        factory = component_factory or DefaultOrchestratorComponentFactory()
        self.domain_processor: DomainEventProcessor = factory.create_domain_processor(self.log)
        self.capability_processor: CapabilityEventProcessor = factory.create_capability_processor(self.log)
        self.task_manager: TaskManager = factory.create_task_manager(self.log)
        self.outbox_manager: OutboxManager = factory.create_outbox_manager(self.log, self.name)

    async def process_message(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """通过路由到适当的处理器来处理消息。

        Args:
            message: 要处理的消息字典（新嵌套结构）
            context: 可选的上下文信息字典

        Returns:
            处理结果字典或None
        """
        self.log.info(
            "orchestrator_message_received",
            message_keys=list(message.keys()),
            has_context=context is not None,
            context_keys=list(context.keys()) if context else [],
        )

        # 领域事件形状识别 - 新嵌套结构
        system_data = message.get("system", {})
        event_type = system_data.get("event_type")
        aggregate_id = system_data.get("aggregate_id")

        if event_type and aggregate_id:
            self.log.info(
                "orchestrator_processing_domain_event",
                event_type=event_type,
                aggregate_id=aggregate_id,
                has_payload=bool(message.get("data")),
                schema_version=message.get("schema_version", "v1"),
            )
            return await self._handle_domain_event(message, context or {})

        # 能力事件信封 - 从上下文获取类型
        msg_type = (context or {}).get("meta", {}).get("type") or message.get("type")
        if msg_type:
            self.log.info(
                "orchestrator_processing_capability_event",
                msg_type=msg_type,
                topic=context.get("topic") if context else None,
                has_data=bool(message.get("data")),
            )
            return await self._handle_capability_event(msg_type, message, context or {})

        self.log.debug("orchestrator_ignored_message", reason="unknown_shape")
        return None

    async def _handle_domain_event(
        self, evt: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """使用领域事件处理器处理领域事件。

        Args:
            evt: 领域事件字典
            context: 可选的上下文信息字典

        Returns:
            处理结果字典或None
        """
        from src.common.events.mapping import normalize_task_type

        # 通过领域处理器处理事件
        processing_result = await self.domain_processor.handle_domain_event(evt, context)

        if not processing_result:
            return None

        # 提取处理结果
        correlation_id = processing_result["correlation_id"]
        scope_type = processing_result["scope_type"]
        aggregate_id = processing_result["aggregate_id"]
        mapping = processing_result["mapping"]
        enriched_payload = processing_result["enriched_payload"]
        causation_id = processing_result["causation_id"]
        metadata = processing_result.get("metadata")

        # 1) 持久化领域事件 - 通过Outbox模式确保事件最终一致性
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
            self.log.error(
                "orchestrator_domain_event_persist_failed",
                scope_type=scope_type,
                event_action=mapping.requested_action,
                aggregate_id=aggregate_id,
                error=str(e),
                exc_info=True,
            )
            raise

        # 2) 创建异步任务并将能力任务入队 - 仅当需要能力任务时执行
        if mapping.capability_message:
            try:
                await self.task_manager.create_async_task(
                    correlation_id=correlation_id,
                    session_id=aggregate_id,
                    task_type=normalize_task_type(mapping.capability_message.get("type", "")),
                    input_data=mapping.capability_message.get("input") or {},
                )
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
                self.log.warning("async_task_create_failed", correlation_id=correlation_id, error=str(e), exc_info=True)
        else:
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

        Args:
            msg_type: 消息类型
            message: 消息内容字典
            context: 上下文信息字典

        Returns:
            处理结果字典或None
        """
        # 通过能力处理器处理事件
        processing_result = await self.capability_processor.handle_capability_event(msg_type, message, context)

        if not processing_result:
            return None

        # 执行操作
        action = processing_result.action
        return await self._execute_event_action(action)

    async def _execute_event_action(self, action: Any) -> dict[str, Any] | None:
        """使用管理器执行事件处理器指定的操作。

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

        # 如果指定，则持久化领域事件
        if action.domain_event:
            try:
                await self.outbox_manager.persist_domain_event(**action.domain_event)
                self.log.info(
                    "orchestrator_domain_event_persisted_success", event_action=action.domain_event.get("event_action")
                )
            except Exception as e:
                self.log.error("orchestrator_domain_event_persist_failed", error=str(e), exc_info=True)
                raise

        # 如果指定，则完成异步任务
        if action.task_completion:
            try:
                await self.task_manager.complete_async_task(**action.task_completion)
                self.log.info(
                    "orchestrator_async_task_completed_success",
                    correlation_id=action.task_completion.get("correlation_id"),
                )
            except Exception as e:
                self.log.error("orchestrator_async_task_complete_failed", error=str(e), exc_info=True)

        # 如果指定，则将后续能力任务入队
        if action.capability_message:
            try:
                # 创建异步任务以保持可观测性和一致性
                from src.common.events.mapping import normalize_task_type

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

                await self.outbox_manager.enqueue_capability_task(
                    capability_message=action.capability_message,
                    correlation_id=correlation_id,
                )
                self.log.info("orchestrator_followup_task_enqueued", topic=action.capability_message.get("_topic"))
            except Exception as e:
                self.log.error("orchestrator_followup_task_enqueue_failed", error=str(e), exc_info=True)

        return None
