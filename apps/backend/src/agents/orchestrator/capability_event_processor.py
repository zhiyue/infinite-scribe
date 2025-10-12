"""能力事件处理模块

目标：用直接的基于 msg_type 的路由替代多层分发，降低复杂度。

核心职责：
- 解析能力事件消息与上下文，提取会话/作用域/追踪信息
- 基于 `msg_type` 直接构建 EventAction（领域事件、任务完成、能力消息）
- 返回 ProcessingResult 供 OrchestratorAgent 执行
"""

from __future__ import annotations

from typing import Any

from src.agents.orchestrator.types import (
    CapabilityEventMessage,
    EventAction,
    GenerationData,
    MessageContext,
    ProcessingResult,
    ScopeInfo,
)
from src.common.events.config import infer_scope_from_topic
from src.common.events.mapping import (
    extract_strategy_key_from_event_type,
    is_generation_completed_event,
    normalize_task_type,
)

# ============================================================================
# 数据提取函数
# ============================================================================


def extract_event_data(message: dict[str, Any]) -> GenerationData:
    """从消息中提取业务数据，处理多种消息格式

    支持两种格式：
    1. 标准格式：{"data": {...}, ...}
    2. 扁平格式：{直接包含业务字段}
    """
    event_msg: CapabilityEventMessage = CapabilityEventMessage(**message)
    typed_data = event_msg.to_typed_data()

    if hasattr(typed_data, "model_fields_set") and typed_data.model_fields_set:
        return typed_data

    # 简单回退：当标准信封不足时直接取字典
    potential_payload = message.get("data") if isinstance(message.get("data"), dict) else message
    payload = {} if not isinstance(potential_payload, dict) else potential_payload

    return GenerationData(**payload)


def extract_session_and_scope(data: GenerationData, context: MessageContext) -> tuple[str, ScopeInfo]:
    """从数据和上下文中提取会话ID和作用域信息

    会话ID提取优先级：
    1. context.meta.aggregate_id (系统级)
    2. data.session_id (业务级，向后兼容)

    作用域从topic推断：topic="genesis.outline.events" -> scope="Genesis"
    """
    session_id = ""
    if context.meta:
        session_id = str(context.meta.aggregate_id or "")

    if not session_id:
        session_id = str(getattr(data, "session_id", "") or "")

    topic = context.topic or ""
    scope_prefix, scope_type = infer_scope_from_topic(topic)

    scope_info = ScopeInfo(
        topic=topic,
        scope_prefix=scope_prefix,
        scope_type=scope_type,
    )

    return session_id, scope_info


def extract_metadata_field(context: MessageContext, field_name: str) -> str | None:
    """从context.meta中提取指定的元数据字段

    统一的元数据提取逻辑，替代原来重复的代码。
    用于提取 correlation_id、event_id 等系统级元数据。
    """
    if context.meta:
        return getattr(context.meta, field_name, None)
    return None


# ============================================================================
# 主处理器类
# ============================================================================


class CapabilityEventProcessor:
    """能力事件处理编排器

    协调整个能力事件的处理流程：
    - 数据提取和规范化
    - 处理器动态路由
    - 结果封装
    """

    def __init__(self, logger: Any) -> None:
        self.log = logger

    async def handle_capability_event(
        self, msg_type: str, message: dict[str, Any], context: dict[str, Any]
    ) -> ProcessingResult | None:
        """处理能力事件的完整编排流程

        流程：
        1. 提取数据：业务数据、系统元数据、会话和作用域
        2. 匹配处理器：根据数据类型查找并调用处理器
        3. 封装结果：返回包含EventAction的ProcessingResult

        Returns:
            ProcessingResult: 包含处理结果和元数据
            None: 未找到匹配的处理器
        """
        # 阶段1：数据提取
        data = extract_event_data(message)
        context_model = MessageContext(**context)
        session_id, scope_info = extract_session_and_scope(data, context_model)

        # 提取系统元数据
        correlation_id = extract_metadata_field(context_model, "correlation_id")
        causation_id = extract_metadata_field(context_model, "event_id")

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

        # 阶段2：直接路由并构建事件动作
        action = self._route_action(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_info=scope_info,
            causation_id=causation_id,
        )

        if not action:
            return None

        # 阶段3：结果封装
        return ProcessingResult(
            action=action,
            msg_type=msg_type,
            session_id=session_id,
            correlation_id=correlation_id,
        )

    def _route_action(
        self,
        *,
        msg_type: str,
        session_id: str,
        data: GenerationData,
        correlation_id: str | None,
        scope_info: ScopeInfo,
        causation_id: str | None,
    ) -> EventAction | None:
        """基于 msg_type 的直接路由，构建 EventAction。"""
        if not session_id:
            return None

        # 生成完成 → 完成任务
        if is_generation_completed_event(msg_type):
            return self._build_generation_completed_action(
                msg_type=msg_type,
                session_id=session_id,
                data=data,
                correlation_id=correlation_id,
                scope_info=scope_info,
                causation_id=causation_id,
            )

        return None

    def _build_generation_completed_action(
        self,
        *,
        msg_type: str,
        session_id: str,
        data: GenerationData,
        correlation_id: str | None,
        scope_info: ScopeInfo,
        causation_id: str | None,
    ) -> EventAction | None:
        """构建生成完成事件的 EventAction

        将生成完成事件转换为：
        - 领域事件（domain_event）：用于发布到事件总线
        - 任务完成数据（task_completion）：用于标记任务完成

        Args:
            msg_type: 消息类型（如 "genesis.outline.completed"）
            session_id: 会话ID
            data: 生成数据
            correlation_id: 关联ID，用于追踪事件链
            scope_info: 作用域信息
            causation_id: 因果ID，记录触发此事件的原始事件

        Returns:
            EventAction: 包含领域事件和任务完成数据
            None: 无法提取目标类型时
        """
        target_or_action = self._target_from_msg_type(msg_type)
        if not target_or_action:
            return None

        task_prefix = normalize_task_type(msg_type)

        # 构建领域事件数据
        # _target_from_msg_type 现在可能直接返回完整的事件动作（如 "Character.Proposed" 或 "Inquiry.Finished"）
        # 若仅返回目标（如 "character"），则默认拼接 ".Proposed"
        event_action = target_or_action if "." in target_or_action else f"{target_or_action.capitalize()}.Proposed"

        domain_event = {
            "scope_type": scope_info.scope_type,
            "session_id": session_id,
            "event_action": event_action,
            "payload": {"session_id": session_id, "content": data.model_dump()},
            "correlation_id": correlation_id,
            "causation_id": causation_id,
        }

        # 构建任务完成数据
        task_completion = {
            "correlation_id": correlation_id,
            "expect_task_prefix": task_prefix,
            "result_data": data.model_dump(),
        }

        return EventAction(
            domain_event=domain_event,
            task_completion=task_completion,
        )

    @staticmethod
    def _target_from_msg_type(msg_type: str) -> str | None:
        """从 msg_type 推断完整事件动作后缀，以构建领域事件。

        约定：
        - 生成完成类事件（*.Generated）通常落地为领域事件的 "<Target>.Proposed"
        - Inquiry 生成完成（Inquiry.Response.Generated）视为一次完整问答流程，落地为 "Inquiry.Finished"

        返回：
        - 完整事件动作（如 "Character.Proposed"、"Theme.Proposed"、"Inquiry.Finished"），
          或当无法确定动作时返回目标（如 "character"），由调用方补全默认动作。
        """
        # 精确映射：特殊策略
        exact_action_map = {
            # Inquiry：回答生成完成 → 整体问答流程完成
            "Inquiry.Response.Generated": "Inquiry.Finished",
        }
        if msg_type in exact_action_map:
            return exact_action_map[msg_type]

        # 通用策略：识别目标并默认投影为 Proposed（AI草案产出）
        target_key = extract_strategy_key_from_event_type(msg_type)
        if target_key:
            return f"{target_key.capitalize()}.Proposed"

        # 兜底：按能力事件前缀/后缀推断
        parts = msg_type.split(".") if msg_type else []
        if not parts:
            return None

        # 常见的“已生成”结尾 → Proposed
        if parts[-1] == "Generated":
            # 对于如 Character.Design.Generated / Outliner.Theme.Generated
            # 统一回退到第一段作为目标
            sub = parts[0]
            return f"{sub.capitalize()}.Proposed"

        # 默认返回第一段目标（调用方将按需补全动作）
        return parts[0].lower()
