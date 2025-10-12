"""能力事件处理模块

处理编排器的能力事件处理功能。
提取事件数据，尝试不同的处理器，并准备要执行的操作。
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
    """事件数据提取器，用于从能力事件中提取和规范化数据。"""

    @staticmethod
    def extract_event_data(message: dict[str, Any]) -> GenerationData:
        """从消息中提取数据，优先使用'data'字段，如果没有则回退到消息本身。

        Args:
            message: 原始消息字典

        Returns:
            提取出的GenerationData事件数据对象
        """
        # 使用 Pydantic 进行类型安全的数据提取和转换
        event_msg: CapabilityEventMessage = CapabilityEventMessage(**message)
        typed_data = event_msg.to_typed_data()
        # 检查是否有任何有效字段（包括空值字段）
        if hasattr(typed_data, "model_fields_set") and typed_data.model_fields_set:
            return typed_data

        # Fallback: 如果消息没有标准 data 字段，直接根据内容创建GenerationData
        potential_payload = message.get("data") if isinstance(message.get("data"), dict) else message

        # 确保 payload 是一个有效的字典
        payload = {} if not isinstance(potential_payload, dict) else potential_payload

        return GenerationData(**payload)

    @staticmethod
    def extract_session_and_scope(data: GenerationData, context: MessageContext) -> tuple[str, ScopeInfo]:
        """从数据和上下文中提取会话ID和作用域信息。

        Args:
            data: 事件数据字典
            context: 上下文信息字典

        Returns:
            (会话ID, 作用域信息字典) 元组
        """
        # 从上下文中提取会话ID（系统信息）
        # 优先从 context.meta 获取系统字段，符合新的分层设计
        session_id = ""
        if context.meta:
            # aggregate_id 通常对应 session_id
            session_id = str(context.meta.aggregate_id or "")

        # 如果 context 中没有，尝试从消息本身获取（业务层回退）
        if not session_id:
            # 某些消息可能在业务数据中包含 session_id
            session_id = str(getattr(data, "session_id", "") or "")
        topic = context.topic or ""

        # 从主题前缀推断作用域 (例如: genesis.outline.events -> Genesis)
        scope_prefix = topic.split(".", 1)[0].capitalize() if "." in topic else DEFAULT_VALUES["scope_prefix"]
        scope_type = scope_prefix.upper()  # 例如: GENESIS

        scope_info = ScopeInfo(
            topic=topic,
            scope_prefix=scope_prefix,
            scope_type=scope_type,
        )

        return session_id, scope_info

    @staticmethod
    def extract_correlation_id(context: MessageContext, data: GenerationData) -> str | None:
        """提取关联ID，优先从context['meta']获取，否则从data中获取。

        Args:
            context: 上下文信息字典
            data: 事件数据字典

        Returns:
            关联ID字符串或None
        """
        # 从上下文中提取 correlation_id（系统信息）
        # 根据新的分层设计，系统字段应该在 context.meta 中
        if context.meta and context.meta.correlation_id:
            return context.meta.correlation_id

        # 如果 context 中没有，返回 None（不再从 data 获取系统字段）
        # 注意：data 现在只包含纯业务字段，不应包含系统字段
        return None

    @staticmethod
    def extract_causation_id(context: MessageContext, data: GenerationData) -> str | None:
        """提取因果关系ID（能力事件的event_id用作下游领域事件的causation_id）。

        Args:
            context: 上下文信息字典
            data: 事件数据字典

        Returns:
            因果关系ID字符串或None
        """
        # 从上下文中提取 event_id（系统信息）
        # 根据新的分层设计，系统字段应该在 context.meta 中
        if context.meta and context.meta.event_id:
            return context.meta.event_id

        # 如果 context 中没有，返回 None（不再从 data 获取系统字段）
        # 注意：data 现在只包含纯业务字段，不应包含系统字段
        return None


class EventHandlerMatcher:
    """事件处理器匹配器，将事件匹配到适当的处理器并执行它们。"""

    def __init__(self, logger: Any) -> None:
        """初始化事件处理器匹配器。

        Args:
            logger: 日志记录器实例
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
        """通过注册表动态分派事件处理器。

        Args:
            msg_type: 消息类型
            session_id: 会话ID
            data: 事件数据
            correlation_id: 关联ID
            scope_info: 作用域信息字典
            causation_id: 因果ID

        Returns:
            匹配的事件操作对象或None
        """
        # 获取数据对象的确切类型
        data_type = type(data)

        # 从注册表中查找对应的处理器函数
        handler = HANDLER_REGISTRY.get(data_type)

        if handler:
            self.log.info(
                "orchestrator_handler_found",
                data_type=data_type.__name__,
                handler_name=getattr(handler, "__name__", "unknown"),
                session_id=session_id,
            )

            # 动态调用找到的处理器
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

        # 没有找到匹配的处理器
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
