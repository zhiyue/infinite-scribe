"""Orchestrator 特有的类型定义

本模块只包含 Orchestrator 特有的类型。
通用的事件和消息类型已迁移到 src.common.types 模块。

向后兼容性：
为了保持向后兼容，本模块重新导出所有通用类型，
这样现有代码可以继续使用 `from src.agents.orchestrator.types import ...`
而不需要立即修改导入路径。

设计决策：
- 通用类型集中管理：将可复用的类型定义移至 common.types，便于多个模块共享
- 保持向后兼容：通过重新导出避免破坏现有代码，支持渐进式迁移
- 清晰的模块边界：区分编排器特有逻辑和通用消息/事件结构

推荐做法：
新代码应该直接从 src.common.types 导入通用类型：
    from src.common.types import EventMetadata, MessageContext
    from src.agents.orchestrator.types import ProcessingResult
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

# =============================================================================
# 重新导出通用类型以保持向后兼容
# =============================================================================
#
# 架构演进说明：
# 原本所有类型都定义在此模块中，随着系统规模增长，发现许多类型（如事件、消息结构）
# 在多个模块间共享使用。为了避免代码重复和循环依赖，将这些通用类型提取到
# src.common.types 模块中集中管理。
#
# 重新导出策略：
# 为了不破坏现有代码的导入语句，这里重新导出所有通用类型。这样：
# 1. 现有代码无需修改导入路径，继续正常工作
# 2. 新代码可以选择直接从 common.types 导入，享受更清晰的模块结构
# 3. 支持团队渐进式迁移到新的导入方式，降低重构风险
#
# 从 common.types 导入所有通用类型
from src.common.types import (
    CapabilityEventData,
    CapabilityEventMessage,
    CapabilityTaskMessage,
    ContentData,
    DomainEvent,
    DomainEventMetadata,
    DomainEventPayload,
    EventActionType,
    EventMetadata,
    EventOutboxHeaders,
    EventPayloadData,
    GenerationData,
    MessageContext,
    MessageType,
    ScopeInfo,
    ScopeType,
    TargetType,
    TaskCompletionPayload,
    TaskInput,
    TaskResultData,
)

# =============================================================================
# Orchestrator 特有的类型定义
# =============================================================================


class ProcessingResult(BaseModel):
    """处理结果 - 编排器响应格式

    这是 Orchestrator 特有的类型，用于封装处理结果和元数据。
    编排器在处理能力事件后，使用此类型返回统一的响应结构。

    设计考量：
    - 使用 Pydantic BaseModel 确保数据验证和序列化支持
    - 包含追踪字段（session_id, correlation_id）便于分布式系统中的请求追踪
    - 支持额外字段（extra="allow"）提供扩展灵活性

    典型使用场景：
    1. 编排器接收能力事件（CapabilityEventMessage）
    2. 根据事件类型执行相应处理逻辑
    3. 将处理结果封装为 ProcessingResult 返回
    4. 下游服务根据 action 和 msg_type 决定后续操作

    Attributes:
        action: 事件操作对象，包含具体的业务动作和数据
                使用 Any 类型避免与 EventAction 产生循环导入依赖
                实际运行时应为 EventAction 实例
        msg_type: 消息类型标识，用于区分不同的处理结果类型
                  如 "capability_event", "task_completion" 等
        session_id: 会话标识符，用于关联同一会话中的多个请求
                    支持会话级别的状态管理和追踪
        correlation_id: 关联标识符，用于追踪跨服务的请求链路
                       可选字段，用于分布式追踪和日志关联
    """

    # 事件操作对象 - 使用 Any 避免循环导入，实际为 EventAction 类型
    action: Any
    # 消息类型 - 标识处理结果的类别
    msg_type: str
    # 会话标识 - 关联同一会话的所有操作
    session_id: str
    # 关联标识 - 用于分布式追踪（可选）
    correlation_id: str | None = None

    # 模型配置：允许额外字段和任意类型，提供最大灵活性
    # extra="allow": 支持动态添加字段，适应不同场景的扩展需求
    # arbitrary_types_allowed=True: 允许非标准 Pydantic 类型（如 EventAction）
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


# =============================================================================
# 导出列表
# =============================================================================
#
# 显式声明模块的公共接口，控制 `from module import *` 的行为。
#
# 分类说明：
# 1. Orchestrator 特有类型：仅在编排器中使用的专属类型定义
# 2. 通用事件类型：事件驱动架构中的核心事件结构（重新导出）
# 3. 通用消息类型：跨模块消息传递的标准格式（重新导出）
#
# 维护注意事项：
# - 新增 Orchestrator 特有类型时，添加到第一分类
# - 从 common.types 新增通用类型导入时，同步更新此列表
# - 保持分类清晰，便于理解模块边界

__all__ = [
    # Orchestrator 特有类型
    "ProcessingResult",
    # 重新导出的通用事件类型（向后兼容）
    "EventActionType",
    "TargetType",
    "ScopeType",
    "EventMetadata",
    "DomainEventMetadata",
    "ScopeInfo",
    "EventPayloadData",
    "DomainEventPayload",
    "EventOutboxHeaders",
    "DomainEvent",
    # 重新导出的通用消息类型（向后兼容）
    "MessageType",
    "MessageContext",
    "ContentData",
    "GenerationData",
    "TaskInput",
    "CapabilityTaskMessage",
    "TaskResultData",
    "TaskCompletionPayload",
    "CapabilityEventData",
    "CapabilityEventMessage",
]
