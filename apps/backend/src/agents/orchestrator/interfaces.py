"""编排器组件抽象接口

定义编排器各组件的抽象接口，遵循依赖反转原则(DIP)，
允许OrchestratorAgent依赖抽象而不是具体实现。

设计理念：
1. 使用Protocol而非ABC定义接口，支持结构化子类型(structural subtyping)，
   使得任何符合接口签名的类都可以自动成为实现者，无需显式继承
2. 通过工厂模式创建组件实例，实现依赖注入，便于单元测试时替换为mock对象
3. 保持接口简洁，每个Protocol专注于单一职责，遵循接口隔离原则(ISP)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol


class DomainEventProcessor(Protocol):
    """领域事件处理器协议

    处理来自用户的领域级别事件（如创建小说、更新章节等），
    将其转换为系统内部的能力消息，驱动相应的业务流程。

    职责：
    - 解析和验证领域事件的有效性
    - 根据事件类型路由到对应的处理逻辑
    - 将领域事件转换为能力消息供下游Agent消费
    - 管理事件处理的事务边界
    """

    async def handle_domain_event(
        self, evt: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """处理领域事件

        领域事件通常来自API层的用户操作，需要转换为内部能力消息。
        此方法是编排器的入口点，负责启动业务流程。

        Args:
            evt: 领域事件字典，包含event_type、payload等字段，
                 例如: {"event_type": "novel.create", "payload": {...}}
            context: 可选的上下文信息字典，用于传递请求级别的元数据
                    （如user_id、request_id等），便于日志追踪和审计

        Returns:
            处理结果字典，包含处理状态和输出数据；
            返回None表示事件被忽略或无需同步响应

        Raises:
            事件验证失败或处理过程中的业务异常
        """
        ...


class CapabilityEventProcessor(Protocol):
    """能力事件处理器协议

    处理来自其他Agent的能力完成事件，协调多Agent协作流程。
    当下游Agent完成任务后，会发送能力事件回传结果，编排器据此决定下一步动作。

    职责：
    - 接收和解析能力完成事件
    - 根据消息类型路由到对应的处理器
    - 协调多个Agent之间的数据流转
    - 更新业务流程状态，触发后续任务
    """

    async def handle_capability_event(self, msg_type: str, message: dict[str, Any], context: dict[str, Any]) -> Any:
        """处理能力事件

        能力事件是Agent间协作的核心机制，用于异步任务的结果回传。
        例如：InquiryAgent完成意图分类后，通过能力事件通知Orchestrator进入下一阶段。

        Args:
            msg_type: 消息类型，标识能力的具体类别，
                     例如: "IntentClassified"、"WorldBuilt"等
            message: 消息内容字典，包含能力执行的结果数据，
                    通常包含result、metadata等字段
            context: 上下文信息字典，包含correlation_id、session_id等，
                    用于关联原始请求和追踪完整的业务流程

        Returns:
            处理结果对象，具体类型取决于业务需求；
            返回None表示事件处理完成但无需同步响应

        Raises:
            消息格式错误或处理逻辑异常
        """
        ...


class TaskManager(Protocol):
    """任务管理器协议

    管理异步任务的生命周期，追踪任务状态，协调长时间运行的业务流程。
    在事件驱动架构中，任务是业务流程的基本执行单元。

    职责：
    - 创建和注册异步任务，分配唯一标识
    - 追踪任务执行状态（pending、running、completed、failed）
    - 完成任务时更新状态并触发后续流程
    - 提供任务查询和监控能力

    设计考虑：
    使用correlation_id关联同一业务流程中的多个任务，便于分布式追踪。
    """

    async def create_async_task(
        self, *, correlation_id: str | None, session_id: str, task_type: str, input_data: dict[str, Any]
    ) -> None:
        """创建异步任务

        在数据库中记录任务信息，用于后续追踪和状态更新。
        任务创建是业务流程启动的标志，后续Agent通过任务ID获取执行上下文。

        Args:
            correlation_id: 关联ID，用于追踪同一业务流程中的多个任务，
                           在分布式系统中实现端到端的调用链追踪
            session_id: 会话ID，标识用户会话，用于隔离不同用户的任务
            task_type: 任务类型，描述任务的业务语义，
                      例如: "inquiry.classify_intent"、"worldsmith.build_world"
            input_data: 输入数据字典，包含任务执行所需的参数和上下文信息

        Note:
            此方法不返回任务ID，因为任务ID通常由correlation_id派生，
            下游通过correlation_id即可查询任务状态
        """
        ...

    async def complete_async_task(
        self, *, correlation_id: str | None, expect_task_prefix: str, result_data: dict[str, Any]
    ) -> None:
        """完成异步任务

        标记任务为已完成状态，保存执行结果，触发后续业务逻辑。
        此方法通常在Agent完成工作并发送能力事件后调用。

        Args:
            correlation_id: 关联ID，用于定位待完成的任务
            expect_task_prefix: 期望的任务前缀，用于验证任务类型匹配，
                               防止误完成错误的任务，提供额外的安全检查，
                               例如: "inquiry.classify"会匹配"inquiry.classify_intent"
            result_data: 结果数据字典，包含任务执行的输出结果和元数据

        Raises:
            如果未找到匹配的任务，或任务类型不匹配expect_task_prefix
        """
        ...


class OutboxManager(Protocol):
    """Outbox管理器协议

    实现Transactional Outbox模式，确保事件发布的可靠性和一致性。
    在数据库事务中同时保存业务数据和事件，事务提交后异步发送事件，
    避免分布式事务，保证最终一致性。

    职责：
    - 持久化领域事件到Outbox表，与业务操作在同一事务中
    - 将能力任务消息入队到消息中间件（如Redis队列）
    - 确保事件不丢失，即使消息中间件暂时不可用
    - 支持事件重试和幂等性保障

    模式优势：
    - 避免双写问题（同时写数据库和消息队列可能部分失败）
    - 提供事件溯源能力，所有事件都有持久化记录
    - 支持事件回放和审计
    """

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

        将领域事件保存到Outbox表，稍后由后台任务异步发送到消息队列。
        此方法应在业务事务中调用，确保事件和业务数据的一致性。

        Args:
            scope_type: 作用域类型，定义事件的业务范围，
                       例如: "novel"、"chapter"、"character"
            session_id: 会话ID，标识事件所属的用户会话
            event_action: 事件动作，描述具体的业务操作，
                         例如: "created"、"updated"、"deleted"
            payload: 有效负载数据，包含事件的业务数据，应为可JSON序列化的字典
            correlation_id: 关联ID，追踪同一业务流程中的多个事件
            causation_id: 因果ID，标识触发当前事件的上游事件，
                         用于构建事件因果链，便于问题排查
            metadata: 元数据字典，包含额外的非业务信息，
                     如timestamp、user_agent、ip_address等

        Note:
            此方法仅持久化事件，不立即发送。后台任务会轮询Outbox表，
            将未发送的事件推送到消息队列，实现异步解耦。
        """
        ...

    async def enqueue_capability_task(self, *, capability_message: dict[str, Any], correlation_id: str | None) -> None:
        """将能力任务入队

        直接将能力消息推送到消息队列（如Redis），供下游Agent消费。
        与persist_domain_event不同，此方法用于Agent间的即时通信，
        不经过Outbox表，适合对延迟敏感的场景。

        Args:
            capability_message: 能力消息字典，包含任务类型、输入参数等，
                               应符合Agent间约定的消息格式规范
            correlation_id: 关联ID，用于关联请求和响应，
                           便于追踪完整的任务执行链路

        Note:
            此方法假设消息队列可用，如果入队失败会抛出异常。
            对于关键任务，建议先通过persist_domain_event持久化，
            再由后台任务异步推送，提高可靠性。
        """
        ...


class OrchestratorComponentFactory(ABC):
    """编排器组件工厂抽象基类

    使用抽象工厂模式创建编排器的各个组件实例。
    通过依赖注入，使OrchestratorAgent与具体实现解耦，便于单元测试和扩展。

    设计意图：
    - 集中管理组件创建逻辑，避免OrchestratorAgent直接依赖具体类
    - 便于测试时注入Mock对象，提高测试独立性
    - 支持运行时切换实现，提供灵活的配置能力
    """

    @abstractmethod
    def create_domain_processor(self, logger: Any) -> DomainEventProcessor:
        """创建领域事件处理器

        Args:
            logger: 日志记录器，用于记录处理器的运行日志

        Returns:
            实现了DomainEventProcessor协议的处理器实例
        """
        ...

    @abstractmethod
    def create_capability_processor(self, logger: Any) -> CapabilityEventProcessor:
        """创建能力事件处理器

        Args:
            logger: 日志记录器，用于记录处理器的运行日志

        Returns:
            实现了CapabilityEventProcessor协议的处理器实例
        """
        ...

    @abstractmethod
    def create_task_manager(self, logger: Any) -> TaskManager:
        """创建任务管理器

        Args:
            logger: 日志记录器，用于记录任务管理的运行日志

        Returns:
            实现了TaskManager协议的管理器实例
        """
        ...

    @abstractmethod
    def create_outbox_manager(self, logger: Any, agent_name: str) -> OutboxManager:
        """创建Outbox管理器

        Args:
            logger: 日志记录器，用于记录事件发布的运行日志
            agent_name: Agent名称，用于标识事件来源，便于追踪和调试

        Returns:
            实现了OutboxManager协议的管理器实例
        """
        ...


class DefaultOrchestratorComponentFactory(OrchestratorComponentFactory):
    """默认编排器组件工厂实现

    提供编排器组件的默认实现，适用于生产环境。
    测试环境可以创建自定义工厂，返回Mock对象以隔离测试。

    实现特点：
    使用延迟导入（方法内部import）而非模块顶部导入，原因：
    1. 避免循环依赖：interfaces模块被其他模块引用，如果在顶部导入具体实现，
       而具体实现又依赖interfaces，会形成循环依赖
    2. 减少启动时间：只在实际创建组件时才加载实现模块，提高应用启动速度
    3. 支持条件加载：可以根据配置动态选择不同的实现类
    """

    def create_domain_processor(self, logger: Any) -> DomainEventProcessor:
        """创建领域事件处理器

        Args:
            logger: 日志记录器

        Returns:
            DomainEventProcessor的默认实现实例
        """
        # 延迟导入避免循环依赖
        from src.agents.orchestrator.domain_event_processor import DomainEventProcessor as DomainEventProcessorImpl

        return DomainEventProcessorImpl(logger)

    def create_capability_processor(self, logger: Any) -> CapabilityEventProcessor:
        """创建能力事件处理器

        Args:
            logger: 日志记录器

        Returns:
            CapabilityEventProcessor的默认实现实例
        """
        # 延迟导入避免循环依赖
        from src.agents.orchestrator.capability_event_processor import (
            CapabilityEventProcessor as CapabilityEventProcessorImpl,
        )

        return CapabilityEventProcessorImpl(logger)

    def create_task_manager(self, logger: Any) -> TaskManager:
        """创建任务管理器

        Args:
            logger: 日志记录器

        Returns:
            TaskManager的默认实现实例
        """
        # 延迟导入避免循环依赖
        from src.agents.orchestrator.task_manager import TaskManager as TaskManagerImpl

        return TaskManagerImpl(logger)

    def create_outbox_manager(self, logger: Any, agent_name: str) -> OutboxManager:
        """创建Outbox管理器

        Args:
            logger: 日志记录器
            agent_name: Agent名称

        Returns:
            OutboxManager的默认实现实例
        """
        # 延迟导入避免循环依赖
        from src.agents.orchestrator.outbox_manager import OutboxManager as OutboxManagerImpl

        return OutboxManagerImpl(logger, agent_name)
