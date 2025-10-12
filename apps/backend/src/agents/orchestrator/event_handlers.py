"""能力事件处理器(Event Handlers for Capability Events)

本模块提供基于命令模式的事件处理架构,将不同类型的能力事件处理逻辑封装为独立的命令对象。
这种设计使得事件处理逻辑从主编排器中分离,提升了代码的可读性、可测试性和可维护性。

核心设计模式:
- 命令模式(Command Pattern): 将事件处理请求封装为对象,实现请求的参数化、队列化和记录
- 工厂模式(Factory Pattern): 根据消息类型动态创建合适的命令处理器
- 外观模式(Facade Pattern): 提供向后兼容的简化接口,屏蔽内部实现复杂度

架构分层:
1. EventCommand: 抽象命令接口,定义事件处理的标准协议
2. ConcreteCommand: 具体命令实现(如 GenerationCompletedCommand),封装特定事件的处理逻辑
3. EventCommandFactory: 命令工厂,负责命令的创建和调度
4. WorkflowOrchestrator: 核心编排器,协调命令执行和工作流决策
5. CapabilityEventHandlers: 向后兼容的外观层,保持旧代码的调用方式不变
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from src.agents.orchestrator.message_factory import MessageFactory
from src.agents.orchestrator.types import GenerationData
from src.agents.orchestrator.workflow_rules import ConfigBasedWorkflowRules, IWorkflowRules
from src.agents.orchestrator.workflows import EventAction, EventActionBuilder, EventHandlerConfig


class EventCommand(ABC):
    """事件命令抽象基类

    实现命令模式(Command Pattern)的核心接口,将事件处理逻辑封装为可执行的命令对象。
    每个具体命令类负责处理特定类型的事件,实现关注点分离和代码的可扩展性。

    设计理念:
    - 单一职责: 每个具体命令类只处理一种类型的事件
    - 开闭原则: 新增事件类型时只需添加新的命令类,无需修改现有代码
    - 依赖注入: 通过构造函数注入工作流规则,便于测试和配置切换

    双重初始化策略(Dual Initialization):
    支持两种初始化方式以实现平滑迁移:
    1. 新方式: 传入 workflow_rules 接口对象(推荐)
    2. 旧方式: 传入 config 配置对象(向后兼容)

    这种设计允许团队逐步从配置驱动迁移到接口驱动,降低重构风险。
    """

    def __init__(self, workflow_rules: IWorkflowRules | None = None, config: EventHandlerConfig | None = None):
        """初始化事件命令

        支持两种初始化路径,优先使用 workflow_rules 接口:
        1. 如果提供了 workflow_rules,直接使用(新架构)
        2. 否则从 config 创建 ConfigBasedWorkflowRules(旧架构兼容)

        向后兼容性考量:
        - 保留 self.config 以支持遗留代码中可能存在的直接配置访问
        - 使用默认配置(EventHandlerConfig.for_genesis_workflow)确保无参数初始化时的可用性
        - 这种渐进式设计使得代码库可以分阶段重构,避免一次性大规模修改

        Args:
            workflow_rules: 工作流规则接口对象(推荐方式)
            config: 事件处理器配置对象(向后兼容)
        """
        # 优先使用新的规则接口,实现接口驱动的架构
        if workflow_rules:
            self.workflow_rules = workflow_rules
        else:
            # 向后兼容路径: 从配置对象创建规则实现
            # 如果没有提供配置,使用 Genesis 工作流的默认配置
            config = config or EventHandlerConfig.for_genesis_workflow()
            self.workflow_rules = ConfigBasedWorkflowRules(config)
            # 保留配置对象供遗留代码使用,避免破坏现有功能
            self.config = config

    @abstractmethod
    def can_handle(self, msg_type: str) -> bool:
        """判断此命令是否能处理给定的消息类型

        责任链模式(Chain of Responsibility)的核心方法:
        命令工厂会遍历所有已注册的命令,通过此方法找到第一个能够处理该消息类型的命令。

        设计要点:
        - 每个具体命令类实现自己的判断逻辑,通常基于消息类型前缀或完整匹配
        - 返回 True 表示此命令可以处理该消息,工厂将停止遍历并使用此命令
        - 实现应该高效,因为每个消息都会触发此方法的调用

        Args:
            msg_type: 消息类型字符串,如 "ChapterGenerated", "SceneGenerated"

        Returns:
            True 表示此命令可以处理该消息类型,False 则不能处理
        """
        pass

    @abstractmethod
    def execute(
        self,
        msg_type: str,
        session_id: str,
        data: Any,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str = "",
        causation_id: str | None = None,
    ) -> EventAction | None:
        """执行命令并返回事件操作对象

        命令模式的核心执行方法,封装了完整的事件处理逻辑:
        1. 验证输入参数的有效性
        2. 根据消息类型和数据执行业务逻辑
        3. 构建并返回 EventAction 对象,指导后续的工作流操作

        事件溯源(Event Sourcing)支持:
        - correlation_id: 关联标识,追踪同一业务流程中的多个事件
        - causation_id: 因果标识,记录触发当前事件的上游事件
        这些追踪字段支持分布式系统中的请求链路追踪和问题诊断。

        Args:
            msg_type: 消息类型,标识事件的种类
            session_id: 会话标识,关联同一用户会话中的所有操作
            data: 事件携带的数据负载,类型取决于具体的事件
            correlation_id: 关联标识,用于追踪业务流程(可选)
            scope_type: 作用域类型,如 "Chapter", "Scene",定义事件的上下文范围
            scope_prefix: 作用域前缀,用于构建完整的作用域标识
            causation_id: 因果标识,记录触发此事件的上游事件(可选)

        Returns:
            EventAction 对象,包含下一步要执行的操作,如发布领域事件、完成任务等
            返回 None 表示无法处理该事件或无需后续操作
        """
        pass


class GenerationCompletedCommand(EventCommand):
    """Command for handling generation completion events."""

    def can_handle(self, msg_type: str) -> bool:
        """Check if this is a generation completion event."""
        from src.common.events.mapping import is_generation_completed_event

        return is_generation_completed_event(msg_type)

    def execute(
        self,
        msg_type: str,
        session_id: str,
        data: Any,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str = "",
        causation_id: str | None = None,
    ) -> EventAction | None:
        """Handle generation completion events."""
        if not (self.can_handle(msg_type) and session_id):
            return None

        target_type = self.workflow_rules.get_target_for_event(msg_type)
        if not target_type:
            return None

        # Get task prefix using existing mapping utility
        from src.common.events.mapping import normalize_task_type

        task_prefix = normalize_task_type(msg_type)

        # Build event action using builder pattern
        builder = EventActionBuilder()

        # Add domain event
        builder.with_domain_event(
            scope_type=scope_type,
            session_id=session_id,
            event_action=f"{target_type.capitalize()}.Proposed",
            payload={"session_id": session_id, "content": data.model_dump()},
            correlation_id=correlation_id,
            causation_id=causation_id,
        )

        # Add task completion
        builder.with_task_completion(
            correlation_id=correlation_id,
            expect_task_prefix=task_prefix,
            result_data=data.model_dump(),
        )

        # Add capability message
        capability_message = MessageFactory.create_quality_review_message(
            session_id=session_id, target_type=target_type, content=data.model_dump(), scope_prefix=scope_prefix
        )
        builder.with_capability_message(capability_message)

        return builder.build()


class EventCommandFactory:
    """Factory for creating event command handlers."""

    def __init__(self, workflow_rules: IWorkflowRules | None = None, config: EventHandlerConfig | None = None):
        # Support both new rules interface and legacy config for migration
        if workflow_rules:
            self.workflow_rules = workflow_rules
        else:
            # Backward compatibility: create rules from config
            config = config or EventHandlerConfig.for_genesis_workflow()
            self.workflow_rules = ConfigBasedWorkflowRules(config)

        self._commands = [
            GenerationCompletedCommand(workflow_rules=self.workflow_rules),
        ]

    def get_command(self, msg_type: str) -> EventCommand | None:
        """Get the appropriate command handler for a message type."""
        for command in self._commands:
            if command.can_handle(msg_type):
                return command
        return None

    def handle_event(
        self,
        msg_type: str,
        session_id: str,
        data: Any,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str = "",
        causation_id: str | None = None,
    ) -> EventAction | None:
        """Handle an event using the appropriate command."""
        command = self.get_command(msg_type)
        if command:
            return command.execute(
                msg_type=msg_type,
                session_id=session_id,
                data=data,
                correlation_id=correlation_id,
                scope_type=scope_type,
                scope_prefix=scope_prefix,
                causation_id=causation_id,
            )
        return None


class WorkflowOrchestrator:
    """Core workflow orchestrator responsible for routing events to commands."""

    def __init__(
        self,
        workflow_rules: IWorkflowRules | None = None,
        config: EventHandlerConfig | None = None,
        factory: EventCommandFactory | None = None,
    ) -> None:
        # Support both new rules interface and legacy config for migration
        if workflow_rules:
            self.workflow_rules = workflow_rules
        elif config:
            self.workflow_rules = ConfigBasedWorkflowRules(config)
        else:
            # Default backward compatibility
            config = EventHandlerConfig.for_genesis_workflow()
            self.workflow_rules = ConfigBasedWorkflowRules(config)

        self.factory = factory or EventCommandFactory(workflow_rules=self.workflow_rules)

    def orchestrate_generation(
        self,
        msg_type: str,
        session_id: str,
        data: GenerationData,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        return self.orchestrate(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )

    def orchestrate(
        self,
        *,
        msg_type: str,
        session_id: str,
        data: Any,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str = "",
        causation_id: str | None = None,
    ) -> EventAction | None:
        return self.factory.handle_event(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )


class CapabilityEventHandlers:
    """Backward-compatible facade exposing workflow orchestration entry points."""

    _default_orchestrator: WorkflowOrchestrator | None = None

    def __init__(
        self,
        workflow_rules: IWorkflowRules | None = None,
        config: EventHandlerConfig | None = None,
        orchestrator: WorkflowOrchestrator | None = None,
    ) -> None:
        if orchestrator:
            self.orchestrator = orchestrator
        elif workflow_rules:
            self.orchestrator = WorkflowOrchestrator(workflow_rules=workflow_rules)
        else:
            # Backward compatibility
            self.orchestrator = WorkflowOrchestrator(config=config)

    # ------------------------------------------------------------------
    # Instance-based API
    # ------------------------------------------------------------------
    def handle_generation_event(
        self,
        msg_type: str,
        session_id: str,
        data: GenerationData,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        return self.orchestrator.orchestrate_generation(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )

    def handle_event(
        self,
        msg_type: str,
        session_id: str,
        data: Any,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str = "",
        causation_id: str | None = None,
    ) -> EventAction | None:
        return self.orchestrator.orchestrate(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )

    # ------------------------------------------------------------------
    # Class-level helpers to preserve historical static API
    # ------------------------------------------------------------------
    @classmethod
    def _default(cls) -> WorkflowOrchestrator:
        if cls._default_orchestrator is None:
            cls._default_orchestrator = WorkflowOrchestrator()
        return cls._default_orchestrator

    @classmethod
    def handle_generation_completed(
        cls,
        msg_type: str,
        session_id: str,
        data: GenerationData,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        return cls._default().orchestrate_generation(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )


# ==============================================================================
# Dynamic Handler Dispatch Registry
# ==============================================================================

# Type alias for handler functions
HandlerFunction = Callable[..., EventAction | None]

# Core registry: maps data types to their corresponding handler functions
HANDLER_REGISTRY: dict[type, HandlerFunction] = {
    GenerationData: CapabilityEventHandlers.handle_generation_completed,
}
