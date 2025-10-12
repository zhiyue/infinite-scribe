# Agent Messaging Reference Index

> 汇总与能力事件、领域事件及消息封装相关的关键文档，方便快速定位具体规范与示例。

## 内容地图

| 分类 | 描述 | 文档 |
|------|------|------|
| 能力事件流程 | 介绍 Envelope、Outbox、Kafka 与编排器之间的分层数据流，以及能力事件负载约定 | [`docs/architecture/agent-message-flow.md`](agent-message-flow.md) |
| 能力 & 领域事件结构 | 详细列出 Orchestrator 处理的事件 Schema、`system/data` 分层示例、常用字段约束 | [`docs/orchestrator-event-structures.md`](../orchestrator-event-structures.md) |
| 命令/事件总览 | Genesis 阶段命令与事件的索引关系（高层导航） | [`.tasks/novel-genesis-stage/lld/commands-events-index.md`](../../.tasks/novel-genesis-stage/lld/commands-events-index.md) |
| 领域事件详情 | 列出各事件类型的字段含义与触发条件 | [`.tasks/novel-genesis-stage/lld/events.md`](../../.tasks/novel-genesis-stage/lld/events.md) |
| 事件类型字典 | 定义所有标准化事件类型字符串，便于统一命名 | [`.tasks/novel-genesis-stage/lld/event-types.md`](../../.tasks/novel-genesis-stage/lld/event-types.md) |

## 使用建议

1. **理解整体流转** → 先阅读《Agent 消息流与数据存储架构》，掌握能力事件的 Outbox + Envelope 流程，并留意与领域事件（system/data/schema_version）的差异。
2. **查字段细节** → 查看《Orchestrator 事件结构》以及 `.tasks` 下的事件定义，确认所需字段。
3. **对照命令/事件映射** → 使用 `commands-events-index.md` 找到对应能力的输入输出关系。
4. **实施修改前复核** → 当调整消息结构时，务必同步检查上述文档，保持术语和字段一致。
