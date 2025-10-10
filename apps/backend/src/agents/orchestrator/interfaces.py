"""编排器组件抽象接口

定义编排器各组件的抽象接口，遵循依赖反转原则(DIP)，
允许OrchestratorAgent依赖抽象而不是具体实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol


class DomainEventProcessor(Protocol):
    """领域事件处理器协议"""

    async def handle_domain_event(
        self, evt: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """处理领域事件

        Args:
            evt: 领域事件字典
            context: 可选的上下文信息字典

        Returns:
            处理结果字典或None
        """
        ...


class CapabilityEventProcessor(Protocol):
    """能力事件处理器协议"""

    async def handle_capability_event(self, msg_type: str, message: dict[str, Any], context: dict[str, Any]) -> Any:
        """处理能力事件

        Args:
            msg_type: 消息类型
            message: 消息内容字典
            context: 上下文信息字典

        Returns:
            处理结果对象或None
        """
        ...


class TaskManager(Protocol):
    """任务管理器协议"""

    async def create_async_task(
        self, *, correlation_id: str | None, session_id: str, task_type: str, input_data: dict[str, Any]
    ) -> None:
        """创建异步任务

        Args:
            correlation_id: 关联ID
            session_id: 会话ID
            task_type: 任务类型
            input_data: 输入数据
        """
        ...

    async def complete_async_task(
        self, *, correlation_id: str | None, expect_task_prefix: str, result_data: dict[str, Any]
    ) -> None:
        """完成异步任务

        Args:
            correlation_id: 关联ID
            expect_task_prefix: 期望的任务前缀
            result_data: 结果数据
        """
        ...


class OutboxManager(Protocol):
    """Outbox管理器协议"""

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
        """持久化领域事件

        Args:
            scope_type: 作用域类型
            session_id: 会话ID
            event_action: 事件动作
            payload: 有效负载数据
            correlation_id: 关联ID
            causation_id: 因果ID
        """
        ...

    async def enqueue_capability_task(self, *, capability_message: dict[str, Any], correlation_id: str | None) -> None:
        """将能力任务入队

        Args:
            capability_message: 能力消息字典
            correlation_id: 关联ID
        """
        ...


class OrchestratorComponentFactory(ABC):
    """编排器组件工厂抽象基类"""

    @abstractmethod
    def create_domain_processor(self, logger: Any) -> DomainEventProcessor:
        """创建领域事件处理器"""
        ...

    @abstractmethod
    def create_capability_processor(self, logger: Any) -> CapabilityEventProcessor:
        """创建能力事件处理器"""
        ...

    @abstractmethod
    def create_task_manager(self, logger: Any) -> TaskManager:
        """创建任务管理器"""
        ...

    @abstractmethod
    def create_outbox_manager(self, logger: Any, agent_name: str) -> OutboxManager:
        """创建Outbox管理器"""
        ...


class DefaultOrchestratorComponentFactory(OrchestratorComponentFactory):
    """默认编排器组件工厂实现"""

    def create_domain_processor(self, logger: Any) -> DomainEventProcessor:
        """创建领域事件处理器"""
        from src.agents.orchestrator.domain_event_processor import DomainEventProcessor as DomainEventProcessorImpl

        return DomainEventProcessorImpl(logger)

    def create_capability_processor(self, logger: Any) -> CapabilityEventProcessor:
        """创建能力事件处理器"""
        from src.agents.orchestrator.capability_event_processor import (
            CapabilityEventProcessor as CapabilityEventProcessorImpl,
        )

        return CapabilityEventProcessorImpl(logger)

    def create_task_manager(self, logger: Any) -> TaskManager:
        """创建任务管理器"""
        from src.agents.orchestrator.task_manager import TaskManager as TaskManagerImpl

        return TaskManagerImpl(logger)

    def create_outbox_manager(self, logger: Any, agent_name: str) -> OutboxManager:
        """创建Outbox管理器"""
        from src.agents.orchestrator.outbox_manager import OutboxManager as OutboxManagerImpl

        return OutboxManagerImpl(logger, agent_name)
