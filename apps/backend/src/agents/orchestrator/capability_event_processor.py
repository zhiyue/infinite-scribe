"""能力事件处理模块

本模块实现了能力事件(Capability Event)的核心处理流程，负责：
1. 从原始消息中提取和规范化事件数据
2. 解析消息上下文中的系统元数据(correlation_id、causation_id等)
3. 通过注册表动态匹配并调用相应的事件处理器
4. 生成包含下游操作(领域事件、任务完成、能力消息)的处理结果

设计理念：
- 采用职责分离原则：提取器、匹配器、处理器各司其职
- 遵循事件溯源模式：保留完整的因果链追踪(correlation_id、causation_id)
- 支持动态处理器注册：通过类型映射实现松耦合的处理器扩展
"""

from __future__ import annotations

from typing import Any

from src.agents.orchestrator.event_handlers import HANDLER_REGISTRY
from src.agents.orchestrator.types import (
    CapabilityEventMessage,
    GenerationData,
    MessageContext,
    ProcessingResult,
    ScopeInfo,
)
from src.agents.orchestrator.workflows import EventAction
from src.common.events.config import DEFAULT_VALUES


class EventDataExtractor:
    """事件数据提取器，用于从能力事件中提取和规范化数据

    职责：
    1. 将原始消息字典转换为类型安全的Pydantic模型
    2. 提取业务数据(GenerationData)和系统元数据(correlation_id等)
    3. 处理消息格式的兼容性问题(标准格式vs遗留格式)
    4. 从消息和上下文中推断会话ID和作用域信息
    """

    @staticmethod
    def extract_event_data(message: dict[str, Any]) -> GenerationData:
        """从消息中提取业务数据，处理多种消息格式

        处理逻辑：
        1. 首先尝试按标准CapabilityEventMessage格式解析
        2. 如果解析成功且有有效字段，直接返回typed_data
        3. 否则回退到兼容模式：从message["data"]或message本身提取数据

        这种回退机制是为了兼容不同版本的消息生产者，确保系统演进过程中
        旧版本消息仍能被正确处理。

        Args:
            message: 原始消息字典，可能包含标准data字段或直接包含业务字段

        Returns:
            提取出的GenerationData事件数据对象，包含纯业务字段
        """
        # 使用 Pydantic 进行类型安全的数据提取和转换
        event_msg: CapabilityEventMessage = CapabilityEventMessage(**message)
        typed_data = event_msg.to_typed_data()

        # 检查是否有任何有效字段（包括空值字段）
        # model_fields_set是Pydantic v2特性，记录了哪些字段被显式设置
        if hasattr(typed_data, "model_fields_set") and typed_data.model_fields_set:
            return typed_data

        # 兼容性回退：处理非标准格式的消息
        # 某些生产者可能直接在message根层级发送数据，而不是嵌套在data字段中
        potential_payload = message.get("data") if isinstance(message.get("data"), dict) else message

        # 防御性编程：确保payload是有效字典，避免Pydantic解析异常
        payload = {} if not isinstance(potential_payload, dict) else potential_payload

        return GenerationData(**payload)

    @staticmethod
    def extract_session_and_scope(data: GenerationData, context: MessageContext) -> tuple[str, ScopeInfo]:
        """从数据和上下文中提取会话ID和作用域信息

        会话ID提取策略(按优先级排序)：
        1. context.meta.aggregate_id - 系统层级的聚合根ID，最可靠
        2. data.session_id - 业务层级的会话ID，用于向后兼容

        作用域推断策略：
        - 从topic的第一段提取作用域前缀(如"genesis.outline.events" -> "Genesis")
        - 作用域决定了事件的处理范围和处理器选择
        - 这种基于约定的推断减少了显式配置，但要求topic命名规范一致

        Args:
            data: 事件数据，可能包含业务层面的session_id
            context: 消息上下文，包含系统元数据和topic信息

        Returns:
            (会话ID, 作用域信息) 元组，用于后续的处理器路由和事件关联
        """
        # 优先从系统元数据中提取会话ID
        # 新的分层设计将系统字段统一存放在context.meta中，与业务数据分离
        session_id = ""
        if context.meta:
            # aggregate_id在DDD中代表聚合根的唯一标识，通常映射到会话ID
            session_id = str(context.meta.aggregate_id or "")

        # 兼容性回退：从业务数据中查找session_id
        # 某些遗留消息可能将session_id放在业务数据层，需要支持这种情况
        if not session_id:
            session_id = str(getattr(data, "session_id", "") or "")

        topic = context.topic or ""

        # 基于topic约定推断作用域类型
        # 作用域决定了消息路由和处理器选择，是消息分类的关键维度
        # 例如："genesis.outline.events" -> scope_prefix="Genesis", scope_type="GENESIS"
        scope_prefix = topic.split(".", 1)[0].capitalize() if "." in topic else DEFAULT_VALUES["scope_prefix"]
        scope_type = scope_prefix.upper()

        scope_info = ScopeInfo(
            topic=topic,
            scope_prefix=scope_prefix,
            scope_type=scope_type,
        )

        return session_id, scope_info

    @staticmethod
    def extract_correlation_id(context: MessageContext, data: GenerationData) -> str | None:
        """提取关联ID，用于追踪跨服务的请求链路

        Correlation ID的作用：
        - 将同一用户请求产生的所有事件关联起来
        - 支持分布式追踪和问题定位
        - 在整个请求链路中保持不变，直到请求完成

        为什么只从context.meta提取：
        - 遵循新的消息分层设计：系统元数据与业务数据分离
        - correlation_id是系统级概念，不应出现在业务数据层
        - 这种严格分离提高了代码的可维护性和类型安全性

        Args:
            context: 消息上下文，包含系统元数据
            data: 事件业务数据(不应包含系统字段)

        Returns:
            关联ID字符串，用于追踪请求链；如果不存在返回None
        """
        # 仅从系统元数据中提取correlation_id
        # 这是有意为之：强制消息生产者将系统字段放在正确位置
        if context.meta and context.meta.correlation_id:
            return context.meta.correlation_id

        # 不再从业务数据中提取系统字段
        # 如果这里返回None，说明消息格式不符合规范，需要修复生产者
        return None

    @staticmethod
    def extract_causation_id(context: MessageContext, data: GenerationData) -> str | None:
        """提取因果ID，用于构建事件的因果关系链

        Causation ID的作用：
        - 记录当前事件是由哪个事件触发的(直接因果关系)
        - 与correlation_id配合，支持完整的事件溯源
        - 能力事件的event_id会成为其触发的领域事件的causation_id

        因果链示例：
        1. 用户请求(correlation_id=REQ-001) -> 能力事件A(event_id=EVT-A, correlation_id=REQ-001)
        2. 能力事件A触发 -> 领域事件B(causation_id=EVT-A, correlation_id=REQ-001)
        3. 领域事件B触发 -> 领域事件C(causation_id=EVT-B, correlation_id=REQ-001)

        Args:
            context: 消息上下文，包含当前事件的event_id
            data: 事件业务数据(不使用)

        Returns:
            因果ID字符串(即当前事件的event_id)；如果不存在返回None
        """
        # 当前能力事件的event_id将作为下游事件的causation_id
        # 这样可以追踪"谁触发了谁"的因果关系
        if context.meta and context.meta.event_id:
            return context.meta.event_id

        # 不再从业务数据中提取系统字段
        # 缺失event_id说明消息格式有问题，需要在生产者侧修复
        return None


class EventHandlerMatcher:
    """事件处理器匹配器，负责动态路由和执行事件处理器

    设计模式：策略模式 + 注册表模式
    - 使用类型作为键，从HANDLER_REGISTRY中查找对应的处理器函数
    - 支持运行时动态添加新的处理器，无需修改此类代码
    - 避免了大量的if-else条件判断，提高了可扩展性

    工作流程：
    1. 根据数据类型(type(data))查找注册表
    2. 调用匹配的处理器函数，传入所有必要参数
    3. 返回处理器生成的EventAction对象
    """

    def __init__(self, logger: Any) -> None:
        """初始化事件处理器匹配器

        Args:
            logger: 结构化日志记录器，用于追踪处理器匹配和执行过程
        """
        self.log = logger

    def find_matching_handler(
        self,
        msg_type: str,
        session_id: str,
        data: GenerationData,
        correlation_id: str | None,
        scope_info: ScopeInfo,
        causation_id: str | None,
    ) -> EventAction | None:
        """通过类型注册表动态分派事件处理器

        为什么使用类型作为键：
        - Python的type()返回对象的确切类型，天然支持多态
        - 类型匹配比字符串匹配更类型安全，IDE可以提供更好的支持
        - 便于使用装饰器自动注册处理器：@register_handler(DataType)

        处理器职责：
        - 将能力事件转换为下游操作(领域事件、任务完成、能力消息)
        - 封装特定事件类型的业务逻辑
        - 返回EventAction对象，包含要执行的所有操作

        Args:
            msg_type: 消息类型标识符
            session_id: 会话ID，用于关联用户上下文
            data: 类型化的事件业务数据
            correlation_id: 请求链路追踪ID
            scope_info: 作用域信息，决定事件的处理范围
            causation_id: 因果关系ID，追踪事件触发链

        Returns:
            EventAction对象(包含要执行的下游操作)，如果未找到处理器则返回None
        """
        # 使用数据的运行时类型作为查找键
        # 这样可以支持GenerationData的各种子类型
        data_type = type(data)

        # 从全局注册表中查找对应的处理器函数
        # 注册表在event_handlers模块中维护，支持动态注册
        handler = HANDLER_REGISTRY.get(data_type)

        if handler:
            self.log.info(
                "orchestrator_handler_found",
                data_type=data_type.__name__,
                handler_name=getattr(handler, "__name__", "unknown"),
                session_id=session_id,
            )

            # 调用处理器函数，传入完整的上下文信息
            # 处理器是纯函数，接收参数，返回EventAction或None
            action = handler(
                msg_type=msg_type,
                session_id=session_id,
                data=data,
                correlation_id=correlation_id,
                scope_type=scope_info.scope_type,
                scope_prefix=scope_info.scope_prefix,
                causation_id=causation_id,
            )

            if action:
                # 记录处理器返回的操作类型，便于监控和调试
                self.log.info(
                    "orchestrator_handler_matched",
                    msg_type=msg_type,
                    session_id=session_id,
                    data_type=data_type.__name__,
                    has_domain_event=bool(action.domain_event),
                    has_task_completion=bool(action.task_completion),
                    has_capability_message=bool(action.capability_message),
                )
                return action

        # 未找到匹配的处理器是正常情况：
        # 1. 可能是新增的事件类型，处理器尚未实现
        # 2. 可能是测试/调试阶段的事件
        # 记录警告日志，但不抛出异常，允许系统继续运行
        self.log.warning(
            "orchestrator_no_handler_matched",
            msg_type=msg_type,
            session_id=session_id,
            data_type=data_type.__name__,
        )
        return None


class CapabilityEventProcessor:
    """主要的能力事件处理编排器，负责协调整个能力事件的处理流程。"""

    def __init__(self, logger: Any) -> None:
        """初始化能力事件处理器。

        Args:
            logger: 日志记录器实例
        """
        self.log = logger
        self.data_extractor = EventDataExtractor()
        self.handler_matcher = EventHandlerMatcher(logger)

    async def handle_capability_event(
        self, msg_type: str, message: dict[str, Any], context: dict[str, Any]
    ) -> ProcessingResult | None:
        """处理能力事件，进行完整的编排流程。

        Args:
            msg_type: 消息类型
            message: 消息内容字典
            context: 上下文信息字典

        Returns:
            包含操作信息的结果字典，如果无法处理则返回None
        """
        # 使用 Pydantic 进行类型安全的数据处理
        data = self.data_extractor.extract_event_data(message)
        context_model = MessageContext(**context)
        session_id, scope_info = self.data_extractor.extract_session_and_scope(data, context_model)
        correlation_id = self.data_extractor.extract_correlation_id(context_model, data)
        causation_id = self.data_extractor.extract_causation_id(context_model, data)

        self.log.info(
            "orchestrator_capability_event_details",
            msg_type=msg_type,
            session_id=session_id,
            topic=scope_info.topic,
            scope_prefix=scope_info.scope_prefix,
            scope_type=scope_info.scope_type,
            correlation_id=correlation_id,
            data_fields=list(data.model_fields_set),
        )

        # 查找匹配的处理器
        action = self.handler_matcher.find_matching_handler(
            msg_type, session_id, data, correlation_id, scope_info, causation_id
        )

        if not action:
            return None

        # 使用 Pydantic 返回类型安全的处理结果
        return ProcessingResult(
            action=action,
            msg_type=msg_type,
            session_id=session_id,
            correlation_id=correlation_id,
        )
