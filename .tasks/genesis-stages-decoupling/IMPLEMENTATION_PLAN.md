# Genesis 阶段解耦实现计划

## 概述

基于 `docs/genesis_stages_decoupling_design.md` 设计文档，实现 Genesis 阶段与对话会话的解耦，通过新建 `genesis_flows`、`genesis_stage_records`、`genesis_stage_sessions` 表来管理 Genesis 业务状态，同时清理 `conversation_sessions` 表中的冗余字段。

## Stage 1: 数据库迁移和模型定义

**目标**: 创建新的数据库表和索引，同时清理现有表的冗余字段

**成功标准**:
- 创建 `genesis_flows`、`genesis_stage_records`、`genesis_stage_sessions` 三张表
- 添加所有必要的索引和约束
- 清理 `conversation_sessions` 表的 `stage`、`state` 字段
- 可选清理 `version` 字段（根据是否需要乐观并发控制）

**测试**:
- 迁移脚本成功执行
- 新表结构符合设计规范
- 外键约束正确设置
- 索引优化查询性能

**状态**: 未开始

## Stage 2: 数据模型和 Enum 定义

**目标**: 实现 SQLAlchemy 模型和相关枚举类型

**成功标准**:
- 定义 `GenesisFlow`、`GenesisStageRecord`、`GenesisStageSession` 模型
- 实现 `GenesisStatus`、`GenesisStage`、`StageStatus` 等枚举
- 更新 `ConversationSession` 模型，移除 `stage`、`state` 字段
- 设置正确的关系和约束

**测试**:
- 模型实例化和基本 CRUD 操作
- 外键关系正确建立
- 枚举值验证
- 约束条件生效

**状态**: 未开始

## Stage 3: 仓储层实现

**目标**: 实现 Genesis 相关的仓储类

**成功标准**:
- `GenesisFlowRepository`: 流程管理（创建、查询、更新状态）
- `GenesisStageRepository`: 阶段记录管理
- `GenesisStageSessionRepository`: 阶段-会话关联管理
- 更新 `ConversationSessionRepository`，移除 stage/state 相关操作

**测试**:
- 基本 CRUD 操作
- 复杂查询（按阶段查询会话、按流程查询阶段等）
- 约束验证（主会话唯一性、绑定校验等）
- 事务处理

**状态**: 未开始

## Stage 4: 服务层核心业务逻辑

**目标**: 实现 Genesis 核心服务类

**成功标准**:
- `GenesisFlowService`: 流程生命周期管理
- `GenesisStageService`: 阶段管理和会话绑定
- 绑定校验逻辑（scope_type=GENESIS, scope_id=novel_id）
- 会话创建和关联逻辑

**测试**:
- 流程创建和推进
- 阶段创建和完成
- 多会话绑定和主会话管理
- 权限校验和错误处理

**状态**: 未开始

## Stage 5: API 端点和路由

**目标**: 实现新的 Genesis API 端点，更新现有会话 API

**成功标准**:
- 新增 Genesis 流程和阶段管理 API
- 更新会话 API，移除 stage/state 相关端点
- 实现 ETag 机制（基于 updated_at）
- API 文档和 Schema 更新

**测试**:
- API 端点功能测试
- 权限验证
- 错误处理和状态码
- OpenAPI 文档生成

**状态**: 未开始

## Stage 6: 前端适配和集成

**目标**: 更新前端代码以适配新的 API 结构

**成功标准**:
- 更新前端类型定义
- 修改会话相关组件
- 实现新的 Genesis 阶段管理界面
- SSE 事件处理适配

**测试**:
- 前端集成测试
- UI 功能验证
- 实时更新功能

**状态**: 未开始

## Stage 7: 集成测试和验证

**目标**: 端到端测试完整功能

**成功标准**:
- 创建阶段 → 绑定会话 → 发送消息 → 按阶段查询的完整流程
- SSE 事件携带 stage_id/flow_id
- 并发场景测试
- 性能测试

**测试**:
- 端到端集成测试
- 负载测试
- 并发安全性测试
- 数据一致性验证

**状态**: 未开始

## Stage 8: 数据迁移和部署

**目标**: 生产环境部署和数据迁移

**成功标准**:
- 现有数据迁移脚本（可选）
- 平滑部署策略
- 监控和告警设置
- 回滚方案

**测试**:
- 迁移脚本验证
- 部署流程测试
- 监控指标验证

**状态**: 未开始

## 实现注意事项

### 字段清理详情

#### 立即删除的字段
- `conversation_sessions.stage`: 移至 `genesis_flows.current_stage`
- `conversation_sessions.state`: 移至 `genesis_flows.state` 和 `genesis_stage_records.config/result`

#### 可选删除的字段
- `conversation_sessions.version`: 可用 `updated_at` 作为 ETag 替代

#### 必须保留的字段
- `id`, `scope_type`, `scope_id`, `status`, `round_sequence`, `created_at`, `updated_at`

### 连带影响调整

1. **API 模型更新**
   - `SessionResponse` 移除 `stage/state/version` 字段
   - ETag 改用 `updated_at`

2. **废弃接口**
   - `GET/PUT /sessions/{id}/stage` 需要移除或重定向到新接口

3. **仓储层调整**
   - `ConversationSessionRepository` 移除 stage/state 相关操作
   - 简化乐观并发控制逻辑

### 性能考虑

- 核心查询使用 `(stage_id)` 和 `(session_id)` 索引
- 阶段→回合查询通过 JOIN 优化
- 大量历史数据考虑归档策略

### 安全考虑

- 绑定校验：`scope_type=GENESIS` 且 `scope_id=novel_id`
- API 访问权限复用现有鉴权
- 用户必须是 `novel.owner`

## Definition of Done

- [ ] 所有 8 个 Stage 完成
- [ ] 数据库迁移成功执行
- [ ] 新旧 API 功能对等
- [ ] 集成测试全部通过
- [ ] 性能指标满足要求
- [ ] 文档完整更新
- [ ] 部署到开发环境验证成功