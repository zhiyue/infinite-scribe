# Agent Messaging Reference Index

> 汇总与能力事件、领域事件及消息封装相关的关键文档,方便快速定位具体规范与示例。

## 📋 内容地图

### 核心文档

| 分类 | 描述 | 文档 |
|------|------|------|
| 能力事件流程 | 介绍 Envelope、Outbox、Kafka 与编排器之间的分层数据流,以及能力事件负载约定 | [`docs/architecture/agent-message-flow.md`](agent-message-flow.md) |
| 能力 & 领域事件结构 | 详细列出 Orchestrator 处理的事件 Schema、`system/data` 分层示例、常用字段约束 | [`docs/orchestrator-event-structures.md`](../orchestrator-event-structures.md) |
| 命令/事件总览 | Genesis 阶段命令与事件的索引关系(高层导航) | [`.tasks/novel-genesis-stage/lld/commands-events-index.md`](../../.tasks/novel-genesis-stage/lld/commands-events-index.md) |
| 领域事件详情 | 列出各事件类型的字段含义与触发条件 | [`.tasks/novel-genesis-stage/lld/events.md`](../../.tasks/novel-genesis-stage/lld/events.md) |
| 事件类型字典 | 定义所有标准化事件类型字符串,便于统一命名 | [`.tasks/novel-genesis-stage/lld/event-types.md`](../../.tasks/novel-genesis-stage/lld/event-types.md) |

## 🧭 补充参考

### 高层架构
- [`ARCHITECTURE_OVERVIEW.md`](ARCHITECTURE_OVERVIEW.md) — 系统模块依赖与事件流向总览。
- [`components.md`](components.md) — 各后台服务/Agent 在命令、领域事件、能力事件中的职责。
- [`core-workflows.md`](core-workflows.md) — 命令→Outbox→Kafka→Agent→结果事件的关键时序图。
- [`high-level-architecture.md`](high-level-architecture.md) — Prefect、Kafka、Outbox 的分层定位。

### 事件命名与映射
- [`event-naming-conventions.md`](event-naming-conventions.md) — 领域/能力事件的命名规则与受控动词表。
- [`.tasks/novel-genesis-stage/lld/event-mapping-unification.md`](../../.tasks/novel-genesis-stage/lld/event-mapping-unification.md) — 命令/事件映射与序列化统一策略。
- [`.tasks/novel-genesis-stage/lld/eventbridge.md`](../../.tasks/novel-genesis-stage/lld/eventbridge.md) — EventBridge 与 SSE 推送的消息桥接方案。

### Genesis LLD 细化文档
- [`.tasks/novel-genesis-stage/lld/overview.md`](../../.tasks/novel-genesis-stage/lld/overview.md) — LLD 约束、术语和上下游契约。
- [`.tasks/novel-genesis-stage/lld/command-types.md`](../../.tasks/novel-genesis-stage/lld/command-types.md) — 命令类型、受控命名与字段说明。
- [`.tasks/novel-genesis-stage/lld/events.md`](../../.tasks/novel-genesis-stage/lld/events.md) — 领域事件/能力事件字段详解与 Topic 映射。
- [`.tasks/novel-genesis-stage/lld/data-examples.md`](../../.tasks/novel-genesis-stage/lld/data-examples.md) — 命令/事件/任务的端到端数据样本。
- [`.tasks/novel-genesis-stage/lld/serialization-implementation.md`](../../.tasks/novel-genesis-stage/lld/serialization-implementation.md) — 序列化层实现与 API/数据库约束。
- [`.tasks/novel-genesis-stage/lld/consistency-guidelines.md`](../../.tasks/novel-genesis-stage/lld/consistency-guidelines.md) — 命名、字段与流程一致性检查清单。

### 设计背景
- [`../design/genesis-stage-decoupling-architecture.md`](../design/genesis-stage-decoupling-architecture.md) — 创世阶段解耦、命令/领域事件持久化设计。
- [`../genesis_stages_decoupling_design.md`](../genesis_stages_decoupling_design.md) — 阶段记录、EventOutbox 复用与数据库演进方案。

### 基础规范 ⭐**必读**

| 分类 | 描述 | 文档 |
|------|------|------|
| **事件命名约定** | **官方动词表、聚合根规则、版本化策略、DLQ处理** - 事件系统的基石规范 | [`docs/architecture/event-naming-conventions.md`](event-naming-conventions.md) |
| 命令类型定义 | 命令的命名格式、Python枚举、Payload结构示例 | [`.tasks/novel-genesis-stage/lld/command-types.md`](../../.tasks/novel-genesis-stage/lld/command-types.md) |

### 前端通信

| 分类 | 描述 | 文档 |
|------|------|------|
| **SSE 事件映射** | **Kafka到SSE的映射规则、权限过滤、数据精简策略** - 前端开发必读 | [`docs/guides/development/sse-event-mapping.md`](../guides/development/sse-event-mapping.md) |
| EventBridge LLD | Kafka→Redis→SSE桥接设计、熔断降级、指标监控 | [`.tasks/novel-genesis-stage/lld/eventbridge.md`](../../.tasks/novel-genesis-stage/lld/eventbridge.md) |

### 架构设计

| 分类 | 描述 | 文档 |
|------|------|------|
| 事件映射统一分析 | 映射架构分析、重构建议、实施方案 | [`.tasks/novel-genesis-stage/lld/event-mapping-unification.md`](../../.tasks/novel-genesis-stage/lld/event-mapping-unification.md) |

---

## 🎯 快速导航

### 按角色查找

#### 前端开发者
**命令发送**:
- [前端 Command 结构](../orchestrator-event-structures.md#1-前端-command-结构) - 了解如何发送命令
- [命令类型定义](../../.tasks/novel-genesis-stage/lld/command-types.md) - 命令的命名和Payload结构

**实时事件接收**:
- [SSE 事件映射](../guides/development/sse-event-mapping.md) - **必读** Kafka到SSE的映射规则和权限过滤
- [事件响应格式](../../.tasks/novel-genesis-stage/lld/event-types.md#事件结构规范) - 了解事件返回格式
- [EventBridge LLD](../../.tasks/novel-genesis-stage/lld/eventbridge.md) - 理解实时推送机制

#### Agent 开发者
**消息发送**:
- [Envelope 标准格式](agent-message-flow.md#1-envelope-标准格式) - 消息封装标准
- [Agent 发送消息](agent-message-flow.md#81-agent-发送消息推荐) - 发送消息最佳实践

**事件命名**:
- [事件命名约定](event-naming-conventions.md) - **必读** 官方动词表和聚合根规则
- [能力事件命名](../../.tasks/novel-genesis-stage/lld/events.md#能力事件命名规范内部使用) - Agent命名空间规范

#### Orchestrator 开发者
**数据流转**:
- [完整数据流转](../orchestrator-event-structures.md#完整数据流转概览) - 端到端数据流
- [事件转换流程](../orchestrator-event-structures.md#事件转换流程) - 转换逻辑

**映射配置**:
- [命令到事件映射](../../.tasks/novel-genesis-stage/lld/event-types.md#命令到事件映射) - 映射表
- [事件映射统一](../../.tasks/novel-genesis-stage/lld/event-mapping-unification.md) - 映射架构和实施方案

#### 架构师
**命名规范**:
- [事件命名约定](event-naming-conventions.md) - **基石文档** 命名规则和版本化策略

**完整架构**:
- [消息流架构](agent-message-flow.md) - 系统级消息流设计
- [事件设计详细实现](../../.tasks/novel-genesis-stage/lld/events.md) - 事件系统的架构决策
- [数据转换流程](../orchestrator-event-structures.md#事件转换流程) - 理解数据转换层次

**桥接设计**:
- [EventBridge LLD](../../.tasks/novel-genesis-stage/lld/eventbridge.md) - 实时推送架构设计

---

### 按主题查找

#### 命名规范 ⭐
- [事件命名约定](event-naming-conventions.md) - **官方动词表**、聚合根规则、版本化策略
- [点式命名规范](../../.tasks/novel-genesis-stage/lld/events.md#事件命名契约) - `Domain.AggregateRoot.Action`格式
- [命令命名格式](../../.tasks/novel-genesis-stage/lld/command-types.md#命名格式) - 命令的祈使语态命名

#### 消息格式
- [Envelope 格式](agent-message-flow.md#1-envelope-标准格式) | [GenerationData 结构](agent-message-flow.md#13-能力事件的业务负载约定generationdata) | [system/data 结构](agent-message-flow.md#14-领域事件结构systemdataschema_version)

#### 事件类型
- [Stage 0-5 事件](../../.tasks/novel-genesis-stage/lld/event-types.md#创世阶段事件类型) | [Python 枚举](../../.tasks/novel-genesis-stage/lld/event-types.md#python-枚举定义) | [命令类型枚举](../../.tasks/novel-genesis-stage/lld/command-types.md#python-枚举定义)

#### 数据存储
- [EventOutbox 表](agent-message-flow.md#31-postgresql-层eventoutbox-表) | [Kafka 存储](agent-message-flow.md#32-kafka-层broker-磁盘) | [Context 构建](agent-message-flow.md#4-context-的来源分析)

#### 数据转换
- [转换流程图](../orchestrator-event-structures.md#事件转换流程) | [核心组件](../orchestrator-event-structures.md#核心转换组件) | [完整示例](../orchestrator-event-structures.md#前端-command-到-orchestrator-完整转换流程)

#### 实时推送
- [SSE 映射规则](../guides/development/sse-event-mapping.md#映射规则表) | [权限过滤](../guides/development/sse-event-mapping.md#2-权限过滤规则) | [EventBridge 设计](../../.tasks/novel-genesis-stage/lld/eventbridge.md)

#### Topic 架构
- [领域总线和能力总线](../../.tasks/novel-genesis-stage/lld/events.md#事件与-topic-映射领域总线-能力总线) | [Topic 结构](../../.tasks/novel-genesis-stage/lld/event-types.md#topic-架构) | [Orchestrator 职责](../../.tasks/novel-genesis-stage/lld/events.md#路由职责中央协调者orchestrator)

#### 容错与监控
- [DLQ 策略](event-naming-conventions.md#6-死信队列-dead-letter-queue---dlq) | [熔断降级](../../.tasks/novel-genesis-stage/lld/eventbridge.md#生命周期与容错) | [指标监控](../../.tasks/novel-genesis-stage/lld/eventbridge.md#指标与日志)

---

## 🔍 常见场景

| 场景 | 推荐阅读 |
|------|----------|
| **开发新 Agent** | [事件命名约定](event-naming-conventions.md) → [Envelope 格式](agent-message-flow.md#1-envelope-标准格式) → [发送消息](agent-message-flow.md#81-agent-发送消息推荐) |
| **添加新事件** | [命名约定](event-naming-conventions.md#2-官方动词表-controlled-verb-vocabulary) → [枚举定义](../../.tasks/novel-genesis-stage/lld/event-types.md#python-枚举定义) → [命令映射](../../.tasks/novel-genesis-stage/lld/event-types.md#命令到事件映射) |
| **前端接收事件** | [SSE 映射](../guides/development/sse-event-mapping.md) → [EventBridge](../../.tasks/novel-genesis-stage/lld/eventbridge.md) → [事件格式](../../.tasks/novel-genesis-stage/lld/event-types.md#事件结构规范) |
| **调试消息流** | [数据流全景](agent-message-flow.md#2-数据流全景) → [排错技巧](agent-message-flow.md#85-调试与排错技巧) → [流转概览](../orchestrator-event-structures.md#完整数据流转概览) |
| **处理 Command** | [Command 结构](../orchestrator-event-structures.md#1-前端-command-结构) → [命令类型](../../.tasks/novel-genesis-stage/lld/command-types.md) → [转换流程](../orchestrator-event-structures.md#前端-command-到-orchestrator-完整转换流程) |
| **配置 Topic** | [Topic 映射](../../.tasks/novel-genesis-stage/lld/events.md#事件与-topic-映射领域总线-能力总线) → [Topic 架构](../../.tasks/novel-genesis-stage/lld/event-types.md#topic-架构) → [路由职责](../../.tasks/novel-genesis-stage/lld/events.md#路由职责中央协调者orchestrator) |
| **实现处理器** | [核心组件](../orchestrator-event-structures.md#核心转换组件) → [类型系统](agent-message-flow.md#5-orchestrator-类型系统详解) → [转换流程](../orchestrator-event-structures.md#事件转换流程) |
| **配置实时推送** | [EventBridge LLD](../../.tasks/novel-genesis-stage/lld/eventbridge.md) → [SSE 映射](../guides/development/sse-event-mapping.md) → [熔断降级](../../.tasks/novel-genesis-stage/lld/eventbridge.md#生命周期与容错) |
| **事件版本升级** | [版本化策略](event-naming-conventions.md#3-事件版本化策略-event-versioning-strategy) → [强制结构](event-naming-conventions.md#4-强制事件结构-mandatory-event-structure) |

---

## 📖 核心概念

| 术语 | 定义 | 参考 |
|------|------|------|
| **Envelope** | 统一的消息封装格式,包含 id、ts、type、data 等 | [§1](agent-message-flow.md#1-envelope-标准格式) |
| **EventOutbox** | Outbox 模式的数据库表,用于可靠消息发布 | [§3.1](agent-message-flow.md#31-postgresql-层eventoutbox-表) |
| **领域事件** | 表示业务事实,使用 `Genesis.Session.*` 命名空间 | [events.md](../../.tasks/novel-genesis-stage/lld/events.md#核心领域事件) |
| **能力事件** | Agent 内部事件,使用 `Outliner.*`、`Writer.*` 等命名空间 | [events.md](../../.tasks/novel-genesis-stage/lld/events.md#能力事件命名规范内部使用) |
| **点式命名** | 事件类型格式 `Domain.AggregateRoot.Action`,使用过去式 | [conventions](event-naming-conventions.md#1-命名公式与聚合根-naming-formula--aggregate-root) |
| **聚合根** | 具有独立生命周期的核心业务实体,是事件命名的锚点 | [conventions](event-naming-conventions.md#1-命名公式与聚合根-naming-formula--aggregate-root) |
| **官方动词表** | 受控词汇表(Requested/Created/Proposed/Confirmed等) | [conventions](event-naming-conventions.md#2-官方动词表-controlled-verb-vocabulary) |
| **correlation_id** | 业务流程关联 ID,用于追踪事件链 | [types](../orchestrator-event-structures.md#核心事件结构类型) |
| **causation_id** | 因果关系ID,标识触发当前事件的上游事件 | [conventions](event-naming-conventions.md#4-强制事件结构-mandatory-event-structure) |
| **system/data** | 领域事件信封结构,system 存系统元数据,data 存业务数据 | [§1.4](agent-message-flow.md#14-领域事件结构systemdataschema_version) |
| **GenerationData** | 能力事件的业务负载模型 | [§5.1](agent-message-flow.md#51-核心数据模型) |
| **SSE** | Server-Sent Events,基于HTTP的服务器推送技术 | [sse-mapping](../guides/development/sse-event-mapping.md) |
| **EventBridge** | Kafka到SSE的桥接服务,负责实时事件推送 | [eventbridge](../../.tasks/novel-genesis-stage/lld/eventbridge.md) |
| **DLQ** | Dead-Letter Queue,死信队列,用于处理失败消息 | [conventions](event-naming-conventions.md#6-死信队列-dead-letter-queue---dlq) |

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
| EventBridge (建议) | `apps/backend/src/services/eventbridge/bridge.py` |
| SSE Service | `apps/backend/src/services/sse/redis_client.py` |

### 检查清单
- ✅ [能力事件结构检查清单](agent-message-flow.md#83-能力事件结构检查清单)
- ✅ [领域事件结构检查清单](agent-message-flow.md#84-领域事件结构检查清单)
- ✅ [调试与排错技巧](agent-message-flow.md#85-调试与排错技巧)
- ✅ [SSE 数据转换规则](../guides/development/sse-event-mapping.md#数据转换详细规则)
- ✅ [EventBridge 测试计划](../../.tasks/novel-genesis-stage/lld/eventbridge.md#测试计划)

---

## ⚠️ 重要提醒

### 设计原则
1. **类型安全** - 使用 Pydantic 模型确保类型安全
2. **命名空间隔离** - 系统元数据与业务数据分离
3. **事件驱动** - 异步、解耦的事件处理机制
4. **可观测性** - 完整的追踪链路
5. **命名规范** - 严格遵循官方动词表和聚合根规则

### 常见陷阱
- ❌ 硬编码事件类型(使用枚举或常量)
- ❌ 混淆领域事件和能力事件(不同命名空间和用途)
- ❌ 在 data 中重复系统字段(系统字段在 system 层)
- ❌ 忽略 correlation_id(对追踪和调试至关重要)
- ❌ **使用非官方动词** - 必须从[官方动词表](event-naming-conventions.md#2-官方动词表-controlled-verb-vocabulary)选择
- ❌ **事件名称加版本后缀** - 使用 event_version 字段而非 `.v2` 后缀
- ❌ **忽略 SSE 权限过滤** - 前端接收事件前必须检查权限

### 最佳实践
- ✅ 使用 OutboxEgress 发送能力事件
- ✅ 遵循点式命名规范
- ✅ 使用 system/data 结构封装领域事件
- ✅ 在每个事件中包含 correlation_id 和 causation_id
- ✅ 使用 OutboxPayloadBuilder 构建类型安全的 payload
- ✅ **事件名称使用过去式动词** - 表示已发生的事实
- ✅ **以聚合根为命名锚点** - 确保事件归属清晰
- ✅ **实现 DLQ 和重试机制** - 使用指数退避策略
- ✅ **SSE 数据精简** - 移除敏感信息和大对象

---

## 📚 使用建议

### 入门路径
1. **理解命名规范** → 从[事件命名约定](event-naming-conventions.md)开始,掌握**官方动词表**和聚合根规则
2. **理解整体流转** → 阅读[Agent 消息流](agent-message-flow.md),掌握 Outbox + Envelope 流程
3. **查字段细节** → 查看[Orchestrator 事件结构](../orchestrator-event-structures.md)和 `.tasks` 下的事件定义

### 前端开发路径
1. **发送命令** → [命令类型定义](../../.tasks/novel-genesis-stage/lld/command-types.md) + [前端 Command 结构](../orchestrator-event-structures.md#1-前端-command-结构)
2. **接收事件** → [SSE 事件映射](../guides/development/sse-event-mapping.md) + [EventBridge](../../.tasks/novel-genesis-stage/lld/eventbridge.md)
3. **调试问题** → [数据转换规则](../guides/development/sse-event-mapping.md#数据转换详细规则) + [错误处理](../guides/development/sse-event-mapping.md#错误事件)

### 后端开发路径
1. **事件命名** → [事件命名约定](event-naming-conventions.md) + [能力事件命名](../../.tasks/novel-genesis-stage/lld/events.md#能力事件命名规范内部使用)
2. **消息发送** → [Envelope 格式](agent-message-flow.md#1-envelope-标准格式) + [Agent 发送消息](agent-message-flow.md#81-agent-发送消息推荐)
3. **映射配置** → [命令到事件映射](../../.tasks/novel-genesis-stage/lld/event-types.md#命令到事件映射) + [事件映射统一](../../.tasks/novel-genesis-stage/lld/event-mapping-unification.md)

### 架构设计路径
1. **命名规范** → [事件命名约定](event-naming-conventions.md)(完整阅读)
2. **完整架构** → [消息流架构](agent-message-flow.md) + [事件设计](../../.tasks/novel-genesis-stage/lld/events.md)
3. **实时推送** → [EventBridge LLD](../../.tasks/novel-genesis-stage/lld/eventbridge.md) + [SSE 映射](../guides/development/sse-event-mapping.md)
4. **架构演进** → [事件映射统一分析](../../.tasks/novel-genesis-stage/lld/event-mapping-unification.md)

---

## 🔗 相关资源

### 官方文档
- [Kafka 文档](https://kafka.apache.org/documentation/) - 消息队列
- [Redis Streams](https://redis.io/docs/data-types/streams/) - SSE 实现基础
- [Pydantic](https://docs.pydantic.dev/) - 类型验证

### 最佳实践
- [Domain Events Pattern](https://martinfowler.com/eaaDev/DomainEvent.html) - Martin Fowler
- [Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html) - 事件溯源
- [Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html) - 事务发件箱

---

**最后更新**: 2025-01-12
**维护者**: Backend Architecture Team
**版本**: 2.0 - 新增命名规范、SSE映射、EventBridge等核心文档
