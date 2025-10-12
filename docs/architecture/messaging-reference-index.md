# Agent Messaging Reference Index

> 汇总与能力事件、领域事件及消息封装相关的关键文档,方便快速定位具体规范与示例。

## 📋 内容地图

| 分类 | 描述 | 文档 |
|------|------|------|
| 能力事件流程 | 介绍 Envelope、Outbox、Kafka 与编排器之间的分层数据流,以及能力事件负载约定 | [`docs/architecture/agent-message-flow.md`](agent-message-flow.md) |
| 能力 & 领域事件结构 | 详细列出 Orchestrator 处理的事件 Schema、`system/data` 分层示例、常用字段约束 | [`docs/orchestrator-event-structures.md`](../orchestrator-event-structures.md) |
| 命令/事件总览 | Genesis 阶段命令与事件的索引关系(高层导航) | [`.tasks/novel-genesis-stage/lld/commands-events-index.md`](../../.tasks/novel-genesis-stage/lld/commands-events-index.md) |
| 领域事件详情 | 列出各事件类型的字段含义与触发条件 | [`.tasks/novel-genesis-stage/lld/events.md`](../../.tasks/novel-genesis-stage/lld/events.md) |
| 事件类型字典 | 定义所有标准化事件类型字符串,便于统一命名 | [`.tasks/novel-genesis-stage/lld/event-types.md`](../../.tasks/novel-genesis-stage/lld/event-types.md) |

---

## 🎯 快速导航

### 按角色查找

**前端开发者**:
- [前端 Command 结构](../orchestrator-event-structures.md#1-前端-command-结构) - 了解如何发送命令
- [事件响应格式](../../.tasks/novel-genesis-stage/lld/event-types.md#事件结构规范) - 了解事件返回格式

**Agent 开发者**:
- [Envelope 标准格式](agent-message-flow.md#1-envelope-标准格式) - 消息封装标准
- [Agent 发送消息](agent-message-flow.md#81-agent-发送消息推荐) - 发送消息最佳实践
- [能力事件命名](../../.tasks/novel-genesis-stage/lld/events.md#能力事件命名规范内部使用) - 事件命名规范

**Orchestrator 开发者**:
- [完整数据流转](../orchestrator-event-structures.md#完整数据流转概览) - 端到端数据流
- [事件转换流程](../orchestrator-event-structures.md#事件转换流程) - 转换逻辑
- [命令到事件映射](../../.tasks/novel-genesis-stage/lld/event-types.md#命令到事件映射) - 映射表

### 按主题查找

**消息格式**:
- [Envelope 格式](agent-message-flow.md#1-envelope-标准格式) | [GenerationData 结构](agent-message-flow.md#13-能力事件的业务负载约定generationdata) | [system/data 结构](agent-message-flow.md#14-领域事件结构systemdataschema_version)

**事件类型**:
- [点式命名规范](../../.tasks/novel-genesis-stage/lld/events.md#事件命名契约) | [Stage 0-5 事件](../../.tasks/novel-genesis-stage/lld/event-types.md#创世阶段事件类型) | [Python 枚举](../../.tasks/novel-genesis-stage/lld/event-types.md#python-枚举定义)

**数据存储**:
- [EventOutbox 表](agent-message-flow.md#31-postgresql-层eventoutbox-表) | [Kafka 存储](agent-message-flow.md#32-kafka-层broker-磁盘) | [Context 构建](agent-message-flow.md#4-context-的来源分析)

**数据转换**:
- [转换流程图](../orchestrator-event-structures.md#事件转换流程) | [核心组件](../orchestrator-event-structures.md#核心转换组件) | [完整示例](../orchestrator-event-structures.md#前端-command-到-orchestrator-完整转换流程)

**Topic 架构**:
- [领域总线和能力总线](../../.tasks/novel-genesis-stage/lld/events.md#事件与-topic-映射领域总线-能力总线) | [Topic 结构](../../.tasks/novel-genesis-stage/lld/event-types.md#topic-架构) | [Orchestrator 职责](../../.tasks/novel-genesis-stage/lld/events.md#路由职责中央协调者orchestrator)

---

## 🔍 常见场景

| 场景 | 推荐阅读 |
|------|----------|
| **开发新 Agent** | [Envelope 格式](agent-message-flow.md#1-envelope-标准格式) → [发送消息](agent-message-flow.md#81-agent-发送消息推荐) → [命名规范](../../.tasks/novel-genesis-stage/lld/events.md#能力事件命名规范内部使用) |
| **添加新事件** | [命名契约](../../.tasks/novel-genesis-stage/lld/events.md#事件命名契约) → [枚举定义](../../.tasks/novel-genesis-stage/lld/event-types.md#python-枚举定义) → [命令映射](../../.tasks/novel-genesis-stage/lld/event-types.md#命令到事件映射) |
| **调试消息流** | [数据流全景](agent-message-flow.md#2-数据流全景) → [排错技巧](agent-message-flow.md#85-调试与排错技巧) → [流转概览](../orchestrator-event-structures.md#完整数据流转概览) |
| **处理 Command** | [Command 结构](../orchestrator-event-structures.md#1-前端-command-结构) → [转换流程](../orchestrator-event-structures.md#前端-command-到-orchestrator-完整转换流程) → [领域事件](agent-message-flow.md#14-领域事件结构systemdataschema_version) |
| **配置 Topic** | [Topic 映射](../../.tasks/novel-genesis-stage/lld/events.md#事件与-topic-映射领域总线-能力总线) → [Topic 架构](../../.tasks/novel-genesis-stage/lld/event-types.md#topic-架构) → [路由职责](../../.tasks/novel-genesis-stage/lld/events.md#路由职责中央协调者orchestrator) |
| **实现处理器** | [核心组件](../orchestrator-event-structures.md#核心转换组件) → [类型系统](agent-message-flow.md#5-orchestrator-类型系统详解) → [转换流程](../orchestrator-event-structures.md#事件转换流程) |

---

## 📖 核心概念

| 术语 | 定义 | 参考 |
|------|------|------|
| **Envelope** | 统一的消息封装格式,包含 id、ts、type、data 等 | [§1](agent-message-flow.md#1-envelope-标准格式) |
| **EventOutbox** | Outbox 模式的数据库表,用于可靠消息发布 | [§3.1](agent-message-flow.md#31-postgresql-层eventoutbox-表) |
| **领域事件** | 表示业务事实,使用 `Genesis.Session.*` 命名空间 | [events.md](../../.tasks/novel-genesis-stage/lld/events.md#核心领域事件) |
| **能力事件** | Agent 内部事件,使用 `Outliner.*`、`Writer.*` 等命名空间 | [events.md](../../.tasks/novel-genesis-stage/lld/events.md#能力事件命名规范内部使用) |
| **点式命名** | 事件类型格式 `Domain.AggregateRoot.Action` | [events.md](../../.tasks/novel-genesis-stage/lld/events.md#事件命名契约) |
| **correlation_id** | 业务流程关联 ID,用于追踪事件链 | [types](../orchestrator-event-structures.md#核心事件结构类型) |
| **system/data** | 领域事件信封结构,system 存系统元数据,data 存业务数据 | [§1.4](agent-message-flow.md#14-领域事件结构systemdataschema_version) |
| **GenerationData** | 能力事件的业务负载模型 | [§5.1](agent-message-flow.md#51-核心数据模型) |

---

## 🛠️ 开发资源

### 代码位置
| 组件 | 路径 |
|------|------|
| Envelope | `apps/backend/src/agents/message.py:15-44` |
| encode_message | `apps/backend/src/agents/message.py:33` |
| CapabilityEventProcessor | `apps/backend/src/agents/orchestrator/capability_event_processor.py` |
| OutboxPayloadBuilder | `apps/backend/src/common/outbox.py` |
| ConversationCommandService | `apps/backend/src/services/conversation_command_service.py` |

### 检查清单
- ✅ [能力事件结构检查清单](agent-message-flow.md#83-能力事件结构检查清单)
- ✅ [领域事件结构检查清单](agent-message-flow.md#84-领域事件结构检查清单)
- ✅ [调试与排错技巧](agent-message-flow.md#85-调试与排错技巧)

---

## ⚠️ 重要提醒

### 设计原则
1. **类型安全** - 使用 Pydantic 模型确保类型安全
2. **命名空间隔离** - 系统元数据与业务数据分离
3. **事件驱动** - 异步、解耦的事件处理机制
4. **可观测性** - 完整的追踪链路

### 常见陷阱
- ❌ 硬编码事件类型(使用枚举或常量)
- ❌ 混淆领域事件和能力事件(不同命名空间和用途)
- ❌ 在 data 中重复系统字段(系统字段在 system 层)
- ❌ 忽略 correlation_id(对追踪和调试至关重要)

### 最佳实践
- ✅ 使用 OutboxEgress 发送能力事件
- ✅ 遵循点式命名规范
- ✅ 使用 system/data 结构封装领域事件
- ✅ 在每个事件中包含 correlation_id 和 causation_id
- ✅ 使用 OutboxPayloadBuilder 构建类型安全的 payload

---

## 📚 使用建议

1. **理解整体流转** → 先阅读《Agent 消息流与数据存储架构》,掌握能力事件的 Outbox + Envelope 流程,并留意与领域事件(system/data/schema_version)的差异。
2. **查字段细节** → 查看《Orchestrator 事件结构》以及 `.tasks` 下的事件定义,确认所需字段。
3. **对照命令/事件映射** → 使用 `commands-events-index.md` 找到对应能力的输入输出关系。
4. **实施修改前复核** → 当调整消息结构时,务必同步检查上述文档,保持术语和字段一致。

---

**最后更新**: 2025-01-12
**维护者**: Backend Architecture Team
