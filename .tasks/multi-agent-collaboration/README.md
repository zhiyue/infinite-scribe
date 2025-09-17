# 多Agent协作追踪设计文档

本目录包含了关于多Agent协作追踪的完整设计方案和实现指南。

## 文档结构

### 📋 [design-overview.md](./design-overview.md)
**总体设计方案**
- 系统架构分析
- 现有数据模型评估
- 与过度设计方案的对比
- 核心结论和优势总结

### 📚 [best-practices.md](./best-practices.md)
**最佳实践指南**
- correlation_id统一策略
- Round分层规范
- Agent标识标准
- 实现模式和监控方法

### 💻 [implementation-example.md](./implementation-example.md)
**完整实现示例**
- 端到端的实现流程
- 具体代码示例
- 前端集成方案
- 数据流转详解

## 核心结论

**现有系统已经足够支撑多agent协作和迭代追踪，无需新增核心表。**

### 关键设计模式

1. **分层Round**: 使用 `round_path` 支持树状结构（1, 1.1, 1.2, 1.2.1...）
2. **correlation_id链路**: 使用 `command.id` 串联整条工作流链路
3. **三层架构**: 对话层/工作流层/事件层各司其职
4. **原子操作**: CommandInbox + ConversationRound + DomainEvent 同时创建

### 实际使用场景

**用户命令**: "分析角色心理并生成对话"

```
顶层Round: 3 (用户命令)
├── 3.1 (CharacterExpert分析)
├── 3.2 (Director生成对话)
└── 3.3 (QualityAssurance评估)
    ├── 3.3.1 (第1次迭代)
    ├── 3.3.2 (第2次迭代)
    └── 3.3.3 (最终收敛)
```

所有Round和相关事件都使用同一个 `correlation_id = command.id`

## 优势分析

### ✅ 对比过度设计方案

| 维度 | 现有方案 | 过度设计方案 |
|------|----------|-------------|
| 复杂度 | 简单，复用现有结构 | 复杂，新增多张表 |
| 维护性 | 高，模式统一 | 低，增加维护负担 |
| 性能 | 优，索引优化充分 | 差，多表JOIN查询 |
| 扩展性 | 强，JSONB灵活配置 | 弱，schema变更成本高 |

### ✅ 关键优势

- **数据一致性**: 原子操作保证Command和Round同步创建
- **实时性能**: EventOutbox + SSE实现毫秒级状态更新
- **可扩展性**: JSONB字段支持灵活的agent元数据
- **可观测性**: correlation_id串联完整链路追踪

## 实施建议

### 阶段1: 规范化现有机制
- [ ] 统一correlation_id使用command.id
- [ ] 规范Round分层标准
- [ ] 标准化Agent元数据格式

### 阶段2: 增强服务层
- [ ] 扩展ConversationCommandService支持多Agent工作流
- [ ] 增强OrchestratorAgent的协调能力
- [ ] 实现Agent间依赖管理

### 阶段3: 前端优化
- [ ] 工作流进度可视化
- [ ] Round树状展示
- [ ] 实时状态更新

## 相关代码位置

### 核心模型
- `apps/backend/src/models/conversation.py` - ConversationRound模型
- `apps/backend/src/models/workflow.py` - CommandInbox, AsyncTask模型

### 核心服务
- `apps/backend/src/common/services/conversation/conversation_command_service.py`
- `apps/backend/src/common/services/conversation/conversation_round_creation_service.py`

### Agent框架
- `apps/backend/src/agents/base_agent.py` - Agent基类
- `apps/backend/src/agents/orchestrator.py` - 协调器Agent

## 总结

这个设计方案的核心思想是**复用现有的优秀设计**，而不是重新发明轮子。

分层Round + correlation_id的设计已经是一个**简单而强大**的解决方案，能够支撑任意复杂的多Agent协作模式，同时保持优秀的性能和可维护性。

关键是要**统一标准**，确保所有Agent都遵循相同的Round创建和事件发布规范。