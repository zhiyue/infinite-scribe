# Genesis 阶段解耦任务

## 概述

基于 `docs/genesis_stages_decoupling_design.md` 设计文档，实现 Genesis 阶段与对话会话的解耦。通过新建专用的 Genesis 数据表来管理业务状态，同时清理 `conversation_sessions` 表中的冗余字段，实现关注点分离。

## 任务目标

将 Genesis 的"流程/阶段/阶段配置与产出"从对话聚合中解耦，支持"每个阶段可以拥有独立的 session，且可能有多个 session"，同时保持与现有命令、任务、事件体系的兼容性。

## 核心设计

### 新增数据表

1. **`genesis_flows`** - 创世流程实例（对某部小说的总进度）
2. **`genesis_stage_records`** - 阶段业务记录（配置、结果、指标、状态、迭代）
3. **`genesis_stage_sessions`** - 阶段↔对话会话的关联（多对多，含主会话标记与类别）

### 字段清理

从 `conversation_sessions` 表中清理 Genesis 业务相关字段：

- **删除**: `stage`, `state` - 移至专用的 Genesis 表
- **可选删除**: `version` - 可用 `updated_at` 作为 ETag 替代
- **保留**: `scope_type`, `scope_id`, `status`, `round_sequence`, `created_at`, `updated_at`

## 文档结构

```
.tasks/genesis-stages-decoupling/
├── README.md                     # 本文件
├── IMPLEMENTATION_PLAN.md        # 详细实现计划（8个Stage）
└── (待添加的实现文件)
```

## 相关文档

- **设计文档**: [docs/genesis_stages_decoupling_design.md](../../docs/genesis_stages_decoupling_design.md)
- **实现计划**: [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)

## 实现策略

采用 8 个 Stage 的渐进式实现：

1. **Stage 1**: 数据库迁移和模型定义 ✅
2. **Stage 2**: 数据模型和 Enum 定义
3. **Stage 3**: 仓储层实现
4. **Stage 4**: 服务层核心业务逻辑
5. **Stage 5**: API 端点和路由
6. **Stage 6**: 前端适配和集成
7. **Stage 7**: 集成测试和验证
8. **Stage 8**: 数据迁移和部署

## 成功标准

- [ ] 新的 Genesis 表结构完整且符合设计规范
- [ ] 会话表字段成功清理，业务逻辑正常
- [ ] 新旧 API 功能对等，向后兼容
- [ ] 支持一个阶段绑定多个会话的核心用例
- [ ] 集成测试全部通过
- [ ] 性能指标满足要求

## 关键约束

- **低侵入**: 不修改 `conversation_sessions/rounds` 的核心结构
- **向后兼容**: 现有对话/命令/任务 API 保持不变
- **性能**: 核心查询通过索引优化，支持大量数据
- **安全**: 绑定校验确保 `scope_type=GENESIS` 且 `scope_id=novel_id`

## 下一步行动

参考 [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) 开始 Stage 2 的实现工作。