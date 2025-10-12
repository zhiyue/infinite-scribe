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
    """生成完成事件命令处理器

    专门处理内容生成完成类型的事件(如章节生成完成、场景生成完成等)。
    该命令遵循命令模式,将复杂的事件处理流程封装为独立的可执行对象。

    核心职责:
    1. 识别所有类型的生成完成事件(通过事件映射工具)
    2. 构建领域事件,标记生成内容为"已提议"状态
    3. 完成异步任务,通知任务系统生成已完成
    4. 创建质量审核消息,触发后续的内容审核流程

    工作流程:
    GenerationCompleted → DomainEvent(Proposed) → TaskCompletion → QualityReview

    这种设计将"生成完成"这一技术事件转换为业务领域可理解的多个操作,
    实现了技术层与业务层的解耦,使得工作流更加清晰和可控。
    """

    def can_handle(self, msg_type: str) -> bool:
        """判断此命令是否能处理给定的消息类型

        使用统一的事件映射工具判断消息类型是否属于生成完成事件。
        这种集中式的类型判断避免了在多处重复判断逻辑,提高了可维护性。

        支持的事件类型示例:
        - ChapterGenerated: 章节生成完成
        - SceneGenerated: 场景生成完成
        - CharacterGenerated: 角色生成完成

        Args:
            msg_type: 消息类型字符串

        Returns:
            True 表示此命令可以处理该消息类型
        """
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
        """执行生成完成事件的处理流程

        这是生成完成事件的核心处理逻辑,遵循构建器模式(Builder Pattern)
        逐步构建包含多个操作的复合事件动作。处理流程分为三个关键步骤:

        1. 发布领域事件: 通知领域层有新内容"已提议"等待审核
        2. 完成异步任务: 标记任务系统中的生成任务为完成状态
        3. 触发质量审核: 创建审核消息,启动内容质量检查流程

        快速失败策略(Fail Fast):
        - 如果消息类型无法处理或会话ID缺失,立即返回 None
        - 如果工作流规则未定义目标类型,立即返回 None
        这种设计避免了不必要的资源消耗和错误传播

        Args:
            msg_type: 消息类型,标识具体的生成事件
            session_id: 会话标识,关联用户会话
            data: 生成的内容数据
            correlation_id: 关联标识,用于追踪业务流程
            scope_type: 作用域类型,定义事件的业务上下文
            scope_prefix: 作用域前缀,用于构建完整标识
            causation_id: 因果标识,记录触发此事件的上游事件

        Returns:
            EventAction 对象包含三个操作:领域事件、任务完成、质量审核消息
            返回 None 表示事件无法处理或无需后续操作
        """
        # 验证必要参数,实现快速失败
        if not (self.can_handle(msg_type) and session_id):
            return None

        # 从工作流规则获取目标类型,用于确定后续处理流程
        target_type = self.workflow_rules.get_target_for_event(msg_type)
        if not target_type:
            return None

        # 规范化任务类型前缀,确保任务完成通知能正确匹配待完成的任务
        # 例如: "ChapterGenerated" -> "chapter_generation"
        from src.common.events.mapping import normalize_task_type

        task_prefix = normalize_task_type(msg_type)

        # 使用构建器模式逐步构建复合事件动作
        builder = EventActionBuilder()

        # 步骤1: 添加领域事件,标记内容为"已提议"状态
        # 这个事件通知领域层有新内容等待审核,触发状态机转换
        builder.with_domain_event(
            scope_type=scope_type,
            session_id=session_id,
            event_action=f"{target_type.capitalize()}.Proposed",
            payload={"session_id": session_id, "content": data.model_dump()},
            correlation_id=correlation_id,
            causation_id=causation_id,
        )

        # 步骤2: 添加任务完成通知,关闭任务系统中的生成任务
        # 通过 expect_task_prefix 确保只完成匹配的任务,避免误操作
        builder.with_task_completion(
            correlation_id=correlation_id,
            expect_task_prefix=task_prefix,
            result_data=data.model_dump(),
        )

        # 步骤3: 创建质量审核消息,触发内容审核工作流
        # MessageFactory 负责根据目标类型创建合适的审核消息结构
        capability_message = MessageFactory.create_quality_review_message(
            session_id=session_id, target_type=target_type, content=data.model_dump(), scope_prefix=scope_prefix
        )
        builder.with_capability_message(capability_message)

        # 构建并返回包含所有操作的事件动作对象
        return builder.build()


class EventCommandFactory:
    """事件命令工厂

    实现工厂模式(Factory Pattern)和责任链模式(Chain of Responsibility)的组合:
    - 工厂职责: 创建和管理所有可用的事件命令处理器
    - 责任链职责: 遍历命令列表,找到第一个能处理该事件的命令

    核心优势:
    1. 解耦事件类型与处理逻辑: 新增事件处理器只需添加到命令列表,无需修改调用代码
    2. 集中管理命令实例: 所有命令在工厂初始化时创建,避免重复创建开销
    3. 灵活的命令匹配: 通过 can_handle 方法实现灵活的事件路由策略

    扩展新事件处理:
    只需在 __init__ 的 self._commands 列表中添加新的命令实例即可,
    工厂会自动将新命令纳入责任链,无需修改其他代码。
    """

    def __init__(self, workflow_rules: IWorkflowRules | None = None, config: EventHandlerConfig | None = None):
        """初始化事件命令工厂

        支持两种初始化方式以实现平滑迁移:
        1. 新方式: 传入 workflow_rules 接口对象(推荐)
        2. 旧方式: 传入 config 配置对象(向后兼容)

        在初始化时创建所有命令实例,这些实例在工厂的生命周期内复用,
        避免了每次处理事件时重复创建命令的开销。

        Args:
            workflow_rules: 工作流规则接口对象(推荐方式)
            config: 事件处理器配置对象(向后兼容)
        """
        # 优先使用新的规则接口,实现接口驱动的架构
        if workflow_rules:
            self.workflow_rules = workflow_rules
        else:
            # 向后兼容路径: 从配置对象创建规则实现
            config = config or EventHandlerConfig.for_genesis_workflow()
            self.workflow_rules = ConfigBasedWorkflowRules(config)

        # 命令注册表: 按处理优先级顺序注册所有可用的事件命令
        # 责任链会从前到后遍历,第一个匹配的命令将处理事件
        self._commands = [
            GenerationCompletedCommand(workflow_rules=self.workflow_rules),
            # 新增命令处理器在此添加
        ]

    def get_command(self, msg_type: str) -> EventCommand | None:
        """根据消息类型获取合适的命令处理器

        实现责任链模式的核心方法:
        遍历所有已注册的命令,通过 can_handle 方法找到第一个能处理该消息的命令。
        这种设计使得事件路由逻辑完全由命令自己决定,工厂只负责协调。

        查找策略:
        - 顺序遍历命令列表(按注册顺序)
        - 调用每个命令的 can_handle 方法判断是否匹配
        - 返回第一个匹配的命令,停止后续遍历
        - 如果没有命令匹配,返回 None

        Args:
            msg_type: 消息类型字符串

        Returns:
            匹配的命令处理器实例,如果无匹配则返回 None
        """
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
        """处理事件的统一入口

        这是工厂提供的高级API,封装了"查找命令"和"执行命令"两个步骤。
        调用者无需关心具体由哪个命令处理事件,只需提供事件信息即可。

        处理流程:
        1. 根据消息类型查找匹配的命令处理器
        2. 如果找到命令,调用其 execute 方法执行处理逻辑
        3. 如果没有找到命令,返回 None 表示无法处理

        这种设计将命令选择逻辑隐藏在工厂内部,
        使得事件处理的调用代码更加简洁和统一。

        Args:
            msg_type: 消息类型,标识事件的种类
            session_id: 会话标识
            data: 事件数据负载
            correlation_id: 关联标识,用于追踪业务流程
            scope_type: 作用域类型
            scope_prefix: 作用域前缀
            causation_id: 因果标识

        Returns:
            EventAction 对象包含后续操作,返回 None 表示无法处理
        """
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
    """工作流编排器

    作为系统的核心协调器,负责将事件路由到合适的命令处理器。
    这个类实现了编排器模式(Orchestrator Pattern),将复杂的工作流协调逻辑
    集中在一个地方,使得系统的事件处理流程清晰可控。

    核心职责:
    1. 管理工作流规则和命令工厂的依赖注入
    2. 提供统一的事件编排入口
    3. 支持多种数据类型的事件处理(通过泛型方法)
    4. 实现向后兼容的初始化策略

    架构定位:
    编排器位于应用层和领域层之间,作为两者的桥梁:
    - 接收来自应用层的事件请求
    - 通过工作流规则和命令工厂协调处理逻辑
    - 返回领域操作给应用层执行

    依赖注入策略:
    支持三种依赖注入方式,提供了极大的灵活性:
    1. 注入 workflow_rules: 使用自定义工作流规则
    2. 注入 config: 从配置创建默认工作流规则
    3. 注入 factory: 直接使用预配置的命令工厂
    """

    def __init__(
        self,
        workflow_rules: IWorkflowRules | None = None,
        config: EventHandlerConfig | None = None,
        factory: EventCommandFactory | None = None,
    ) -> None:
        """初始化工作流编排器

        支持灵活的依赖注入,适应不同的使用场景:
        - 测试场景: 注入模拟的 workflow_rules 或 factory
        - 生产场景: 注入配置对象或使用默认配置
        - 向后兼容: 支持旧代码的配置方式

        初始化优先级:
        1. 如果提供了 workflow_rules,使用该规则接口
        2. 如果提供了 config,从配置创建规则实现
        3. 否则使用 Genesis 工作流的默认配置

        Args:
            workflow_rules: 工作流规则接口对象(推荐方式)
            config: 事件处理器配置对象(向后兼容)
            factory: 预配置的命令工厂(高级用法,用于依赖注入)
        """
        # 根据优先级建立工作流规则
        if workflow_rules:
            self.workflow_rules = workflow_rules
        elif config:
            self.workflow_rules = ConfigBasedWorkflowRules(config)
        else:
            # 默认使用 Genesis 工作流配置,确保无参数初始化时的可用性
            config = EventHandlerConfig.for_genesis_workflow()
            self.workflow_rules = ConfigBasedWorkflowRules(config)

        # 如果提供了工厂实例则使用,否则创建新的工厂实例
        # 这种设计支持依赖注入,便于测试和自定义工厂行为
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
        """编排生成类型事件的处理

        这是针对 GenerationData 类型的专用编排方法,提供了类型安全的接口。
        实际上是 orchestrate 方法的类型明确版本,便于调用者理解和使用。

        为什么需要这个方法:
        虽然 orchestrate 方法可以处理任意类型的数据,但提供特定类型的方法
        可以让调用代码更清晰,IDE也能提供更好的类型提示和自动完成。

        Args:
            msg_type: 消息类型,标识生成事件的种类
            session_id: 会话标识
            data: GenerationData 类型的生成数据
            correlation_id: 关联标识
            scope_type: 作用域类型
            scope_prefix: 作用域前缀
            causation_id: 因果标识

        Returns:
            EventAction 对象包含后续操作
        """
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
        """通用的事件编排入口

        这是编排器的核心方法,委托给命令工厂处理具体的事件。
        使用关键字参数(keyword-only arguments)确保调用的明确性。

        委托模式(Delegation Pattern):
        编排器本身不直接处理事件,而是将处理逻辑委托给命令工厂。
        这种设计实现了关注点分离:
        - 编排器关注工作流的协调和规则管理
        - 命令工厂关注命令的选择和执行

        Args:
            msg_type: 消息类型
            session_id: 会话标识
            data: 事件数据(可以是任意类型)
            correlation_id: 关联标识
            scope_type: 作用域类型
            scope_prefix: 作用域前缀
            causation_id: 因果标识

        Returns:
            EventAction 对象包含后续操作,返回 None 表示无法处理
        """
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
    """能力事件处理器外观类

    实现外观模式(Facade Pattern),为工作流编排提供简化的、向后兼容的接口。
    这个类是整个事件处理架构对外暴露的统一入口,隐藏了内部的复杂性。

    核心设计目标:
    1. 向后兼容: 保留旧代码的调用方式,避免大规模重构
    2. 简化接口: 提供清晰直观的方法名,降低使用门槛
    3. 双重API: 同时支持实例方法和类方法,适应不同的使用场景
    4. 灵活初始化: 支持多种依赖注入方式

    使用场景:
    - 实例方法: 需要自定义配置或测试场景
    - 类方法: 快速使用默认配置的场景,避免重复创建实例

    架构演进策略:
    保留这个外观层使得我们可以在内部重构命令模式、工厂模式等复杂架构,
    而不影响外部调用者。这是一种典型的"对扩展开放,对修改封闭"的设计。
    """

    # 类级别的默认编排器实例,实现轻量级单例模式
    # 用于支持类方法调用时的编排器复用
    _default_orchestrator: WorkflowOrchestrator | None = None

    def __init__(
        self,
        workflow_rules: IWorkflowRules | None = None,
        config: EventHandlerConfig | None = None,
        orchestrator: WorkflowOrchestrator | None = None,
    ) -> None:
        """初始化能力事件处理器

        提供三种依赖注入方式,按优先级选择:
        1. 直接注入编排器实例(最灵活,测试常用)
        2. 注入工作流规则接口(推荐方式)
        3. 注入配置对象或使用默认配置(向后兼容)

        这种多层次的初始化策略支持渐进式重构:
        - 新代码可以使用 workflow_rules 接口
        - 旧代码继续使用 config 配置
        - 测试代码可以注入模拟的 orchestrator

        Args:
            workflow_rules: 工作流规则接口对象
            config: 事件处理器配置对象
            orchestrator: 预配置的编排器实例(用于依赖注入)
        """
        if orchestrator:
            # 优先使用注入的编排器,支持完全自定义
            self.orchestrator = orchestrator
        elif workflow_rules:
            # 使用规则接口创建编排器(推荐方式)
            self.orchestrator = WorkflowOrchestrator(workflow_rules=workflow_rules)
        else:
            # 向后兼容: 使用配置创建编排器
            self.orchestrator = WorkflowOrchestrator(config=config)

    # ------------------------------------------------------------------
    # 实例方法 API (Instance-based API)
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
        """处理生成类型的能力事件

        实例方法版本,使用初始化时配置的编排器处理生成事件。
        适用于需要自定义配置或在依赖注入框架中使用的场景。

        方法命名策略:
        使用 "handle_generation_event" 而非 "orchestrate_generation"
        是为了保持与旧代码的一致性,降低迁移成本。

        Args:
            msg_type: 消息类型
            session_id: 会话标识
            data: GenerationData 类型的生成数据
            correlation_id: 关联标识
            scope_type: 作用域类型
            scope_prefix: 作用域前缀
            causation_id: 因果标识

        Returns:
            EventAction 对象包含后续操作
        """
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
        """处理通用类型的能力事件

        实例方法版本,可以处理任意类型的事件数据。
        这是最通用的事件处理入口,支持未来扩展新的事件类型。

        与 handle_generation_event 的关系:
        - handle_generation_event: 类型明确,适用于已知的生成事件
        - handle_event: 类型通用,适用于所有事件类型

        Args:
            msg_type: 消息类型
            session_id: 会话标识
            data: 事件数据(可以是任意类型)
            correlation_id: 关联标识
            scope_type: 作用域类型
            scope_prefix: 作用域前缀
            causation_id: 因果标识

        Returns:
            EventAction 对象包含后续操作,返回 None 表示无法处理
        """
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
    # 类方法 API - 保留历史的静态调用方式 (Class-level API)
    # ------------------------------------------------------------------
    @classmethod
    def _default(cls) -> WorkflowOrchestrator:
        """获取默认的工作流编排器实例

        实现轻量级单例模式(Singleton Pattern),在类级别维护一个共享的编排器实例。
        这个设计支持类方法的快速调用,避免每次都创建新的编排器实例。

        为什么使用延迟初始化:
        - 避免模块导入时就创建实例,减少启动开销
        - 首次调用时才创建,实现按需加载(Lazy Loading)
        - 使用默认配置,无需额外参数

        注意事项:
        这不是严格的单例模式,因为用户仍可以通过实例化 CapabilityEventHandlers
        创建其他编排器实例。这种"伪单例"设计提供了便利性和灵活性的平衡。

        Returns:
            默认的工作流编排器实例
        """
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
        """处理生成完成事件的类方法版本

        提供静态调用方式,使用默认编排器处理生成完成事件。
        这是为了保持与旧代码的兼容性,旧代码可能使用静态方法调用。

        使用场景:
        - 快速原型开发,无需配置
        - 简单的脚本或工具
        - 迁移期间保持旧代码不变

        推荐做法:
        新代码建议使用实例方法而非类方法,因为实例方法支持依赖注入,
        更便于测试和配置管理。

        Args:
            msg_type: 消息类型
            session_id: 会话标识
            data: GenerationData 类型的生成数据
            correlation_id: 关联标识
            scope_type: 作用域类型
            scope_prefix: 作用域前缀
            causation_id: 因果标识

        Returns:
            EventAction 对象包含后续操作
        """
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
# 动态处理器分发注册表 (Dynamic Handler Dispatch Registry)
# ==============================================================================
"""
注册表设计说明:

这个注册表实现了基于数据类型的动态分发机制,是一种轻量级的消息路由策略。
通过将数据类型映射到处理函数,系统可以根据事件携带的数据类型自动选择合适的处理器。

设计优势:
1. 类型驱动: 根据数据的实际类型而非消息类型字符串进行路由
2. 易于扩展: 添加新的数据类型处理只需在注册表中添加一行
3. 类型安全: 利用 Python 的类型系统,减少字符串匹配的错误
4. 集中管理: 所有的类型-处理器映射关系在一处维护

使用场景:
当调用者只知道数据对象的类型,而不确定应该调用哪个处理方法时,
可以通过查询这个注册表找到对应的处理函数。

扩展方式:
HANDLER_REGISTRY[NewDataType] = CapabilityEventHandlers.handle_new_event

这种注册表模式常用于事件驱动架构和插件系统,提供了高度的灵活性。
"""

# 处理器函数的类型别名,统一处理函数的签名
# 所有注册的处理函数都应该接受可变参数并返回 EventAction 或 None
HandlerFunction = Callable[..., EventAction | None]

# 核心注册表: 将数据类型映射到对应的处理函数
# 键: 数据类型(如 GenerationData, ReviewData 等)
# 值: 处理该类型数据的类方法或函数
HANDLER_REGISTRY: dict[type, HandlerFunction] = {
    # GenerationData 类型的事件使用 handle_generation_completed 处理
    GenerationData: CapabilityEventHandlers.handle_generation_completed,
    # 未来可以添加更多类型映射:
    # ReviewData: CapabilityEventHandlers.handle_review_completed,
    # ApprovalData: CapabilityEventHandlers.handle_approval_completed,
}
