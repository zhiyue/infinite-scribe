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

# 启用延迟注解评估，允许类型提示中使用尚未定义的类型（如前向引用）
from __future__ import annotations

from typing import Any

# Pydantic v2 核心组件：数据验证和序列化的基础类
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
    """编排器处理结果的统一响应格式

    此类型专门用于 Orchestrator 封装事件处理结果和追踪元数据。
    编排器作为事件驱动架构的核心协调者，在处理能力事件后，
    使用此类型返回标准化的响应结构，确保下游服务能够统一处理。

    设计考量：
    - 使用 Pydantic BaseModel 确保类型安全、数据验证和 JSON 序列化支持
    - 包含分布式追踪字段（session_id, correlation_id）支持请求链路追踪和问题定位
    - 允许额外字段（extra="allow"）提供扩展灵活性，适应未来需求变化
    - action 使用 Any 类型避免循环导入，保持模块间的清晰依赖关系

    典型工作流：
    1. Orchestrator 接收能力事件消息（CapabilityEventMessage）
    2. 根据事件类型（intent_classified、outline_generated 等）执行相应处理逻辑
    3. 将处理结果、操作类型和追踪信息封装为 ProcessingResult
    4. 返回给调用方，下游服务根据 action 和 msg_type 决定后续流程
    5. 通过 session_id 和 correlation_id 实现全链路追踪和监控

    使用示例：
        result = ProcessingResult(
            action=outline_generated_action,
            msg_type="capability_event",
            session_id="sess_123456",
            correlation_id="corr_789012"
        )

    Attributes:
        action: 事件操作对象，包含具体的业务动作和数据负载
                使用 Any 类型避免与 EventAction 类产生循环导入依赖
                运行时实际类型应为 EventAction 或其子类实例
        msg_type: 消息类型标识符，用于消息路由和处理器选择
                  常见值：capability_event（能力事件）、task_completion（任务完成）
        session_id: 会话标识符，用于关联同一用户会话中的所有相关请求
                    支持会话级状态管理、上下文保持和问题追溯
        correlation_id: 跨服务关联标识符，用于分布式系统中的请求链路追踪
                       可选字段，主要用于日志聚合、性能分析和故障排查
    """

    # 事件操作对象 - 使用 Any 避免循环导入，实际为 EventAction 类型
    action: Any
    # 消息类型标识 - 用于消息路由和处理器选择
    msg_type: str
    # 会话标识 - 关联同一会话的所有操作
    session_id: str
    # 关联标识 - 用于分布式追踪（可选）
    correlation_id: str | None = None

    # 模型配置：启用灵活性以适应事件驱动架构的动态特性
    # extra="allow": 允许动态添加字段，支持不同事件类型携带特定的扩展数据
    # arbitrary_types_allowed=True: 允许非标准 Pydantic 类型，如 EventAction 等自定义类
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


# =============================================================================
# 公共接口导出列表
# =============================================================================
#
# 显式声明模块的公共 API，控制 `from module import *` 的导入行为。
# 遵循 Python 最佳实践，明确定义哪些类型对外可见。
#
# 导出分类说明：
# 1. Orchestrator 特有类型：编排器专属的类型定义，不会在其他模块中使用
#    - ProcessingResult: 编排器处理结果的标准响应格式
#
# 2. 通用事件类型：事件驱动架构的核心类型（重新导出以保持向后兼容）
#    - 事件枚举：EventActionType, TargetType, ScopeType
#    - 元数据结构：EventMetadata, DomainEventMetadata, ScopeInfo
#    - 事件负载：EventPayloadData, DomainEventPayload
#    - 事件容器：DomainEvent, EventOutboxHeaders
#
# 3. 通用消息类型：跨模块消息传递的标准格式（重新导出以保持向后兼容）
#    - 消息枚举：MessageType
#    - 消息上下文：MessageContext
#    - 消息数据：ContentData, GenerationData, TaskInput, TaskResultData
#    - 消息容器：CapabilityTaskMessage, CapabilityEventMessage
#    - 任务负载：TaskCompletionPayload, CapabilityEventData
#
# 维护指南：
# - 新增 Orchestrator 特有类型：添加到分类 1，并在上方文档中说明用途
# - 新增通用类型导入：从 common.types 导入后，添加到相应分类（2 或 3）
# - 移除类型：同步删除导入语句、__all__ 条目和文档说明
# - 重构建议：逐步迁移现有代码直接从 common.types 导入，最终可移除重新导出

__all__ = [
    # =========================================================================
    # Orchestrator 特有类型
    # =========================================================================
    "ProcessingResult",  # 编排器处理结果的统一响应格式
    # =========================================================================
    # 通用事件类型（重新导出以保持向后兼容）
    # =========================================================================
    # 事件枚举类型
    "EventActionType",  # 事件动作类型枚举
    "TargetType",  # 事件目标类型枚举
    "ScopeType",  # 事件作用域类型枚举
    # 事件元数据
    "EventMetadata",  # 通用事件元数据
    "DomainEventMetadata",  # 领域事件元数据
    "ScopeInfo",  # 作用域信息
    # 事件负载和容器
    "EventPayloadData",  # 事件负载数据
    "DomainEventPayload",  # 领域事件负载
    "EventOutboxHeaders",  # 事件发件箱头部信息
    "DomainEvent",  # 领域事件（完整结构）
    # =========================================================================
    # 通用消息类型（重新导出以保持向后兼容）
    # =========================================================================
    # 消息枚举和上下文
    "MessageType",  # 消息类型枚举
    "MessageContext",  # 消息上下文（会话、用户信息等）
    # 消息数据结构
    "ContentData",  # 内容数据
    "GenerationData",  # 生成数据
    "TaskInput",  # 任务输入
    "TaskResultData",  # 任务结果数据
    # 消息容器
    "CapabilityTaskMessage",  # 能力任务消息
    "CapabilityEventMessage",  # 能力事件消息
    # 任务相关负载
    "TaskCompletionPayload",  # 任务完成负载
    "CapabilityEventData",  # 能力事件数据
]
