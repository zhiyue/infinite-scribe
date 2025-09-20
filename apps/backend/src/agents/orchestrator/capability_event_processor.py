"""能力事件处理模块

处理编排器的能力事件处理功能。
提取事件数据，尝试不同的处理器，并准备要执行的操作。
"""

from __future__ import annotations

from typing import Any

from src.agents.orchestrator.event_handlers import CapabilityEventHandlers, EventAction
from src.agents.orchestrator.types import (
    ConsistencyCheckData,
    GenerationData,
    MessageContext,
    ProcessingResult,
    QualityReviewData,
    ScopeInfo,
    create_capability_event_message_from_dict,
    create_message_context_from_dict,
    create_processing_result,
)


class EventDataExtractor:
    """事件数据提取器，用于从能力事件中提取和规范化数据。"""

    @staticmethod
    def extract_event_data(message: dict[str, Any]) -> GenerationData | QualityReviewData | ConsistencyCheckData:
        """从消息中提取数据，优先使用'data'字段，如果没有则回退到消息本身。

        Args:
            message: 原始消息字典

        Returns:
            提取出的事件数据对象
        """
        # 使用 Pydantic 进行类型安全的数据提取和转换
        event_msg = create_capability_event_message_from_dict(message)
        return event_msg.to_typed_data()

    @staticmethod
    def extract_session_and_scope(
        data: GenerationData | QualityReviewData | ConsistencyCheckData, context: MessageContext
    ) -> tuple[str, ScopeInfo]:
        """从数据和上下文中提取会话ID和作用域信息。

        Args:
            data: 事件数据字典
            context: 上下文信息字典

        Returns:
            (会话ID, 作用域信息字典) 元组
        """
        # 从 Pydantic 模型中提取会话 ID
        session_id = str(data.session_id or data.aggregate_id or "")
        topic = context.topic or ""

        # 从主题前缀推断作用域 (例如: genesis.outline.events -> GENESIS)
        scope_prefix = topic.split(".", 1)[0].upper() if "." in topic else "GENESIS"
        scope_type = scope_prefix

        scope_info = ScopeInfo(
            topic=topic,
            scope_prefix=scope_prefix,
            scope_type=scope_type,
        )

        return session_id, scope_info

    @staticmethod
    def extract_correlation_id(context: MessageContext, data: GenerationData | QualityReviewData | ConsistencyCheckData) -> str | None:
        """提取关联ID，优先从context['meta']获取，否则从data中获取。

        Args:
            context: 上下文信息字典
            data: 事件数据字典

        Returns:
            关联ID字符串或None
        """
        # 从 Pydantic 模型中安全提取 correlation_id
        if context.meta and context.meta.correlation_id:
            return context.meta.correlation_id
        return data.correlation_id

    @staticmethod
    def extract_causation_id(context: MessageContext, data: GenerationData | QualityReviewData | ConsistencyCheckData) -> str | None:
        """提取因果关系ID（能力事件的event_id用作下游领域事件的causation_id）。

        Args:
            context: 上下文信息字典
            data: 事件数据字典

        Returns:
            因果关系ID字符串或None
        """
        # 从 Pydantic 模型中安全提取 event_id
        if context.meta and context.meta.event_id:
            return context.meta.event_id
        return data.event_id


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
        data: GenerationData | QualityReviewData | ConsistencyCheckData,
        correlation_id: str | None,
        scope_info: ScopeInfo,
        causation_id: str | None,
    ) -> EventAction | None:
        """按顺序尝试不同的事件处理器，直到找到匹配的为止。

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
        scope_type = scope_info.scope_type
        scope_prefix = scope_info.scope_prefix

        # 根据数据类型选择合适的处理器 - 类型安全的方式
        if isinstance(data, GenerationData):
            self.log.debug("orchestrator_trying_generation_handler", msg_type=msg_type, session_id=session_id)
            action = CapabilityEventHandlers.handle_generation_completed(
                msg_type, session_id, data, correlation_id, scope_type, scope_prefix, causation_id
            )
            if action:
                self.log.info(
                    "orchestrator_generation_handler_matched",
                    msg_type=msg_type,
                    session_id=session_id,
                    has_domain_event=bool(action.domain_event),
                    has_task_completion=bool(action.task_completion),
                    has_capability_message=bool(action.capability_message),
                )
                return action

        elif isinstance(data, QualityReviewData):
            self.log.debug("orchestrator_trying_quality_handler", msg_type=msg_type, session_id=session_id)
            action = CapabilityEventHandlers.handle_quality_review_result(
                msg_type, session_id, data, correlation_id, scope_type, scope_prefix, causation_id
            )
            if action:
                self.log.info(
                    "orchestrator_quality_handler_matched",
                    msg_type=msg_type,
                    session_id=session_id,
                    has_domain_event=bool(action.domain_event),
                    has_task_completion=bool(action.task_completion),
                    has_capability_message=bool(action.capability_message),
                )
                return action

        elif isinstance(data, ConsistencyCheckData):
            self.log.debug("orchestrator_trying_consistency_handler", msg_type=msg_type, session_id=session_id)
            action = CapabilityEventHandlers.handle_consistency_check_result(
                msg_type, session_id, data, correlation_id, scope_type, causation_id
            )
            if action:
                self.log.info(
                    "orchestrator_consistency_handler_matched",
                    msg_type=msg_type,
                    session_id=session_id,
                    has_domain_event=bool(action.domain_event),
                    has_task_completion=bool(action.task_completion),
                    has_capability_message=bool(action.capability_message),
                )
                return action

        # 没有找到匹配的处理器
        self.log.debug(
            "orchestrator_no_handler_matched",
            msg_type=msg_type,
            session_id=session_id,
            data_type=type(data).__name__,
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
        context_model = create_message_context_from_dict(context)
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
            data_fields=list(data.model_fields_set) if hasattr(data, "model_fields_set") else [],
        )

        # 查找匹配的处理器
        action = self.handler_matcher.find_matching_handler(
            msg_type, session_id, data, correlation_id, scope_info, causation_id
        )

        if not action:
            return None

        # 使用 Pydantic 返回类型安全的处理结果
        return create_processing_result(
            action=action,
            msg_type=msg_type,
            session_id=session_id,
            correlation_id=correlation_id,
        )
