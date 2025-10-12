"""编排器工作流动作原语

该模块定义了编排器在处理事件后可以执行的动作类型，采用构建器模式
提供流畅的API来组合复杂的事件响应。支持三种主要动作类型：
- 领域事件：触发系统内其他组件的响应
- 任务完成：标记异步任务的完成状态
- 能力消息：发送给具体能力代理的指令消息
"""

from __future__ import annotations

from typing import Any, NamedTuple


class EventAction(NamedTuple):
    """编排器事件处理后的响应动作

    该类封装了编排器处理事件后可能产生的三种动作类型。使用 NamedTuple
    确保不可变性，避免在异步处理流程中的状态混乱。

    Attributes:
        domain_event: 领域事件数据，用于触发系统内其他模块的响应，
                     包含事件类型、会话标识和有效载荷等关键信息
        task_completion: 任务完成数据，用于标记编排器分配的异步任务已完成，
                        包含关联ID和结果数据以便调用方追踪
        capability_message: 能力消息数据，发送给特定能力代理的指令，
                           用于执行具体的AI能力任务（如查询、生成等）

    Notes:
        - 三个字段都是可选的，支持灵活组合
        - 通常每个动作只会设置一个字段，但架构上允许同时设置多个
        - 使用 EventActionBuilder 构建可提高代码可读性
    """

    domain_event: dict[str, Any] | None = None
    task_completion: dict[str, Any] | None = None
    capability_message: dict[str, Any] | None = None


class EventActionBuilder:
    """事件动作构建器

    使用构建器模式提供流畅的API来组合 EventAction 对象。通过链式调用
    方法可以清晰地表达动作的意图，同时保证最终对象的不可变性。

    Examples:
        >>> action = (EventActionBuilder()
        ...     .with_domain_event(
        ...         scope_type="session",
        ...         session_id="abc123",
        ...         event_action="user.query.received",
        ...         payload={"query": "tell me about..."}
        ...     )
        ...     .build())
    """

    def __init__(self) -> None:
        """初始化构建器，所有动作字段默认为空"""
        self._domain_event: dict[str, Any] | None = None
        self._task_completion: dict[str, Any] | None = None
        self._capability_message: dict[str, Any] | None = None

    def with_domain_event(
        self,
        scope_type: str,
        session_id: str,
        event_action: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> EventActionBuilder:
        """添加领域事件动作

        构建一个领域事件，用于在系统内部触发其他模块的响应。领域事件
        遵循事件驱动架构模式，通过事件总线传播状态变更。

        Args:
            scope_type: 事件作用域类型，如 "session"、"novel"、"chapter"，
                       用于确定事件的生命周期边界
            session_id: 会话标识符，用于关联同一用户交互流程中的所有事件
            event_action: 事件动作名称，采用命名空间格式（如 "user.query.received"），
                         描述发生了什么业务行为
            payload: 事件有效载荷，包含事件相关的业务数据
            correlation_id: 关联ID，用于追踪整个业务流程，跨越多个服务和事件
            causation_id: 因果ID，指向触发当前事件的上游事件ID，用于构建事件链

        Returns:
            EventActionBuilder: 返回自身以支持链式调用

        Notes:
            - correlation_id 用于追踪整个业务流程（如一次用户请求）
            - causation_id 用于记录直接因果关系（哪个事件触发了当前事件）
            - 这两个ID对于分布式系统的可观测性至关重要
        """
        self._domain_event = {
            "scope_type": scope_type,
            "session_id": session_id,
            "event_action": event_action,
            "payload": payload,
            "correlation_id": correlation_id,
            "causation_id": causation_id,
        }
        return self

    def with_task_completion(
        self,
        correlation_id: str | None,
        expect_task_prefix: str,
        result_data: dict[str, Any],
    ) -> EventActionBuilder:
        """添加任务完成动作

        标记一个异步任务已完成，并提供结果数据。编排器使用此机制来通知
        等待任务完成的调用方，支持异步工作流的协调。

        Args:
            correlation_id: 关联ID，用于匹配等待该任务完成的请求方，
                          通常在任务创建时由请求方提供
            expect_task_prefix: 期望的任务前缀，用于标识任务类型和优先级，
                               帮助任务队列进行路由和调度
            result_data: 任务结果数据，包含任务执行的输出，
                        格式取决于具体的任务类型

        Returns:
            EventActionBuilder: 返回自身以支持链式调用

        Notes:
            - 任务前缀用于支持不同优先级和类型的任务队列
            - correlation_id 确保结果能返回给正确的等待方
            - result_data 应包含足够的信息供调用方处理后续逻辑
        """
        self._task_completion = {
            "correlation_id": correlation_id,
            "expect_task_prefix": expect_task_prefix,
            "result_data": result_data,
        }
        return self

    def with_capability_message(self, message: dict[str, Any]) -> EventActionBuilder:
        """添加能力消息动作

        构建发送给特定能力代理的消息，用于触发具体的AI能力执行
        （如查询知识库、生成内容、分析情感等）。

        Args:
            message: 能力消息字典，包含目标能力代理的标识、
                    动作类型、输入参数等信息，格式由能力代理定义

        Returns:
            EventActionBuilder: 返回自身以支持链式调用

        Notes:
            - 消息格式应符合目标能力代理的接口规范
            - 通常包含 capability_type、action、params 等标准字段
            - 能力代理负责验证消息格式并执行相应操作
        """
        self._capability_message = message
        return self

    def build(self) -> EventAction:
        """构建最终的 EventAction 对象

        将构建器中设置的所有动作组合成不可变的 EventAction 实例。

        Returns:
            EventAction: 包含所有已设置动作的不可变动作对象

        Notes:
            - 构建后的对象是不可变的，确保在异步处理中的线程安全
            - 如果没有设置任何动作，所有字段将为 None
            - 通常应该至少设置一个动作字段，否则该动作没有实际效果
        """
        return EventAction(
            domain_event=self._domain_event,
            task_completion=self._task_completion,
            capability_message=self._capability_message,
        )
