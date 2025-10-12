# 通用类型定义 (Common Types)

本目录包含整个后端系统使用的通用类型定义，遵循依赖倒置原则，使得任何 agent 或服务都可以使用这些类型，而无需依赖特定的组件实现。

## 目录结构

```
common/types/
├── __init__.py        # 统一导出所有通用类型
├── events.py          # 事件相关的通用类型
├── messages.py        # 消息相关的通用类型
└── README.md          # 本文档
```

## 模块说明

### events.py - 事件相关类型

包含所有与事件处理相关的通用类型：

**字面量类型：**
- `EventActionType` - 事件动作类型
- `TargetType` - 目标类型
- `ScopeType` - 作用域类型

**元数据和上下文：**
- `EventMetadata` - 统一的事件元数据模型
- `DomainEventMetadata` - EventMetadata 的别名（向后兼容）
- `ScopeInfo` - 作用域信息

**事件结构：**
- `EventPayloadData` - 事件负载数据
- `DomainEventPayload` - 领域事件负载
- `EventOutboxHeaders` - 事件 Outbox 头部信息
- `DomainEvent` - 领域事件完整结构

### messages.py - 消息相关类型

包含所有与消息传递相关的通用类型：

**字面量类型：**
- `MessageType` - 消息类型

**消息上下文：**
- `MessageContext` - 消息上下文（包含主题和元数据）

**内容数据：**
- `ContentData` - 内容数据
- `GenerationData` - 生成数据

**任务消息：**
- `TaskInput` - 任务输入数据
- `CapabilityTaskMessage` - 能力任务消息
- `TaskResultData` - 任务结果数据
- `TaskCompletionPayload` - 任务完成负载

**能力事件消息：**
- `CapabilityEventData` - 能力事件数据
- `CapabilityEventMessage` - 能力事件消息

**工厂函数：**
- `create_message_context()`
- `create_generation_data()`
- `create_capability_task_message()`
- `create_capability_event_message()`

## 使用指南

### 推荐的导入方式

```python
# ✅ 推荐：直接从 common.types 导入通用类型
from src.common.types import (
    EventMetadata,
    MessageContext,
    CapabilityTaskMessage,
)

# ✅ 也可以：从子模块导入
from src.common.types.events import EventMetadata
from src.common.types.messages import MessageContext
```

### 向后兼容性

为了保持向后兼容，`src.agents.orchestrator.types` 模块重新导出了所有通用类型。
这意味着现有代码无需修改即可继续工作：

```python
# ✅ 仍然有效（向后兼容）
from src.agents.orchestrator.types import EventMetadata, MessageContext

# ✅ 新代码推荐使用
from src.common.types import EventMetadata, MessageContext
```

### 组件特有类型

组件特有的类型应该保留在各自的模块中，例如：

```python
# Orchestrator 特有类型
from src.agents.orchestrator.types import ProcessingResult
```

## 设计原则

### 1. 依赖倒置原则 (Dependency Inversion Principle)

通用类型不依赖于特定的组件实现，而是由各个组件依赖通用类型：

```
┌─────────────────────────────────────┐
│      src.common.types (通用)         │
│  - EventMetadata                    │
│  - MessageContext                   │
│  - ...                              │
└─────────────────────────────────────┘
           ▲         ▲         ▲
           │         │         │
     ┌─────┘    ┌────┘    └────┐
     │          │              │
┌────┴───┐ ┌───┴────┐  ┌──────┴─────┐
│Orchestr│ │InquiryA│  │WorldSmith  │
│ator    │ │gent    │  │Agent       │
└────────┘ └────────┘  └────────────┘
```

### 2. 单一职责原则 (Single Responsibility Principle)

- `events.py` - 只负责事件相关的类型
- `messages.py` - 只负责消息相关的类型
- 每个模块有明确的边界和职责

### 3. 开闭原则 (Open/Closed Principle)

- 通过 Pydantic 的 `extra="allow"` 支持扩展
- 向后兼容的别名确保系统对修改关闭，对扩展开放

### 4. 类型安全

使用 Pydantic 实现运行时类型验证：
- 自动类型转换
- 字段验证
- 优秀的错误信息
- 与 FastAPI 完美集成

## 迁移指南

### 从 orchestrator.types 迁移到 common.types

如果你想更新现有代码使用新的导入路径：

```python
# 之前
from src.agents.orchestrator.types import (
    EventMetadata,
    MessageContext,
    CapabilityTaskMessage,
)

# 之后
from src.common.types import (
    EventMetadata,
    MessageContext,
    CapabilityTaskMessage,
)
```

**注意：** 这不是必须的，因为保持了向后兼容性。但新代码建议使用新的导入路径。

## 历史

**2025-01-12：类型重构**
- 将通用类型从 `src.agents.orchestrator.types` 迁移到 `src.common.types`
- 拆分为 `events.py` 和 `messages.py` 两个模块
- 保持向后兼容性
- `orchestrator/types.py` 从 437 行减少到 115 行

## 相关文档

- [Backend Architecture](../../CLAUDE.md)
- [Orchestrator README](../../agents/orchestrator/README.md)
- [Event System Documentation](../events/README.md)
