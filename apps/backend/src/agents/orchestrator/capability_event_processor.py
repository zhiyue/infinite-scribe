"""能力事件处理模块

处理编排器的能力事件处理功能。
提取事件数据，尝试不同的处理器，并准备要执行的操作。
"""

from __future__ import annotations

from typing import Any

from src.agents.orchestrator.event_handlers import CapabilityEventHandlers, EventAction


class EventDataExtractor:
    """事件数据提取器，用于从能力事件中提取和规范化数据。"""

    @staticmethod
    def extract_event_data(message: dict[str, Any]) -> dict[str, Any]:
        """从消息中提取数据，优先使用'data'字段，如果没有则回退到消息本身。

        Args:
            message: 原始消息字典

        Returns:
            提取出的事件数据字典
        """
        return message.get("data") or message

    @staticmethod
    def extract_session_and_scope(data: dict[str, Any], context: dict[str, Any]) -> tuple[str, dict[str, str]]:
        """从数据和上下文中提取会话ID和作用域信息。

        Args:
            data: 事件数据字典
            context: 上下文信息字典

        Returns:
            (会话ID, 作用域信息字典) 元组
        """
        # 从数据中提取会话ID，可能的字段包括session_id或aggregate_id
        session_id = str(data.get("session_id") or data.get("aggregate_id") or "")
        topic = context.get("topic") or ""

        # 从主题前缀推断作用域 (例如: genesis.outline.events -> GENESIS)
        scope_prefix = topic.split(".", 1)[0].upper() if "." in topic else "GENESIS"
        scope_type = scope_prefix

        scope_info = {
            "topic": topic,
            "scope_prefix": scope_prefix,
            "scope_type": scope_type,
        }

        return session_id, scope_info

    @staticmethod
    def extract_correlation_id(context: dict[str, Any], data: dict[str, Any]) -> str | None:
        """提取关联ID，优先从context['meta']获取，否则从data中获取。

        Args:
            context: 上下文信息字典
            data: 事件数据字典

        Returns:
            关联ID字符串或None
        """
        return context.get("meta", {}).get("correlation_id") or data.get("correlation_id")

    @staticmethod
    def extract_causation_id(context: dict[str, Any], data: dict[str, Any]) -> str | None:
        """提取因果关系ID（能力事件的event_id用作下游领域事件的causation_id）。

        Args:
            context: 上下文信息字典
            data: 事件数据字典

        Returns:
            因果关系ID字符串或None
        """
        return context.get("meta", {}).get("event_id") or data.get("event_id")


class EventHandlerMatcher:
    """事件处理器匹配器，将事件匹配到适当的处理器并执行它们。"""

    def __init__(self, logger):
        """初始化事件处理器匹配器。

        Args:
            logger: 日志记录器实例
        """
        self.log = logger

    def find_matching_handler(
        self,
        msg_type: str,
        session_id: str,
        data: dict[str, Any],
        correlation_id: str | None,
        scope_info: dict[str, str],
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
        scope_type = scope_info["scope_type"]
        scope_prefix = scope_info["scope_prefix"]

        # 定义要按顺序尝试的处理器列表 - 按照业务优先级排序
        handlers = [
            # 1. 处理生成完成事件 - 最高优先级，直接影响用户体验
            lambda: CapabilityEventHandlers.handle_generation_completed(
                msg_type, session_id, data, correlation_id, scope_type, scope_prefix, causation_id
            ),
            # 2. 处理质量审查结果事件 - 内容质量保证
            lambda: CapabilityEventHandlers.handle_quality_review_result(
                msg_type, session_id, data, correlation_id, scope_type, scope_prefix, causation_id
            ),
            # 3. 处理一致性检查结果事件 - 数据一致性验证
            lambda: CapabilityEventHandlers.handle_consistency_check_result(
                msg_type, session_id, data, correlation_id, scope_type, causation_id
            ),
        ]

        # 逐个尝试处理器
        for i, handler in enumerate(handlers):
            self.log.debug(
                "orchestrator_trying_handler",
                handler_index=i,
                msg_type=msg_type,
                session_id=session_id,
            )

            action = handler()
            if action:
                self.log.info(
                    "orchestrator_handler_matched",
                    handler_index=i,
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
            handlers_tried=len(handlers),
        )
        return None


class CapabilityEventProcessor:
    """主要的能力事件处理编排器，负责协调整个能力事件的处理流程。"""

    def __init__(self, logger):
        """初始化能力事件处理器。

        Args:
            logger: 日志记录器实例
        """
        self.log = logger
        self.data_extractor = EventDataExtractor()
        self.handler_matcher = EventHandlerMatcher(logger)

    async def handle_capability_event(
        self, msg_type: str, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """处理能力事件，进行完整的编排流程。

        Args:
            msg_type: 消息类型
            message: 消息内容字典
            context: 上下文信息字典

        Returns:
            包含操作信息的结果字典，如果无法处理则返回None
        """
        # 提取事件数据和上下文信息
        data = self.data_extractor.extract_event_data(message)
        session_id, scope_info = self.data_extractor.extract_session_and_scope(data, context)
        correlation_id = self.data_extractor.extract_correlation_id(context, data)
        causation_id = self.data_extractor.extract_causation_id(context, data)

        self.log.info(
            "orchestrator_capability_event_details",
            msg_type=msg_type,
            session_id=session_id,
            topic=scope_info["topic"],
            scope_prefix=scope_info["scope_prefix"],
            scope_type=scope_info["scope_type"],
            correlation_id=correlation_id,
            data_keys=list(data.keys()) if data else [],
        )

        # 查找匹配的处理器
        action = self.handler_matcher.find_matching_handler(
            msg_type, session_id, data, correlation_id, scope_info, causation_id
        )

        if not action:
            return None

        # 返回操作信息供主编排器执行
        return {
            "action": action,
            "msg_type": msg_type,
            "session_id": session_id,
            "correlation_id": correlation_id,
        }
