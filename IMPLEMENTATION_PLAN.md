## Stage 1: 诊断 MissingGreenlet 报错

**Goal**: 复现 `greenlet_spawn has not been called` 报错并定位触发代码路径。
**Success Criteria**: 找到导致日志打印触发 ORM 懒加载的具体语句。
**Tests**: 自建脚本调用 `OutboxRelayService._process_row` 并记录堆栈。
**Status**: Complete

## Stage 2: 修复 OutboxRelayService 日志访问

**Goal**: 调整 `OutboxRelayService` 成功日志，避免访问可能已过期的 ORM 属性。
**Success Criteria**: 成功路径不再访问 `row.status` 等需要额外 IO 的属性。
**Tests**: 复现脚本重新运行，不再抛出 MissingGreenlet。
**Status**: Complete

## Stage 3: 回归验证 Outbox Relay 行为

**Goal**: 确保 outbox 消息发送流程正常，警告消失且记录正确。
**Success Criteria**: 手动脚本及必要单元测试通过，日志无 MissingGreenlet。
**Tests**: 手工脚本 + `uv run pytest apps/backend/tests/unit/services/infrastructure/test_outbox_relay_service.py::TestOutboxRelayService::test_process_row_success -q`
**Status**: Complete

## Stage 4: 引入内容分析与知识更新 Agents

**Goal**: 增加 `content_analyzer` 与 `knowledge_updater`，实现基于 LLM 的分析与存储投影流水线。
**Success Criteria**: 
- 新增 Agent 能够注册并加载；
- `content_analyzer` 消费 `genesis.writer.events` 并产出 `content_analyzed`；
- `knowledge_updater` 消费 `genesis.analyzer.events` 并并行更新 Neo4j/Milvus；
- 新话题映射集中于 `agent_config.py`。
**Tests**: 手动通过 Launcher 仅加载新 Agents，向 `genesis.writer.events` 投递模拟 `chapter_written`，观察产出事件与日志。
**Status**: Complete

## Stage 5: 加强 Stage Session 路由归属校验

**Goal**: 在 stage session 创建与查询接口中增加小说/阶段归属校验，防止跨用户访问。
**Success Criteria**: 非归属用户访问返回 404/403；请求体不再信任外部 `novel_id`；接口仍能为合法用户创建/列出记录。
**Tests**: 现有集成测试 + 新增越权场景测试。
**Status**: In Progress

## Stage 6: 补充越权与数据串联测试

**Goal**: 为 stage session 路由新增覆盖越权访问与 novel_id 伪造的测试用例。
**Success Criteria**: 新测试在未修复版本失败，在修复后通过；同时回归已有场景。
**Tests**: `pnpm backend test --filter genesis stage session routes`（或对应 pytest 选择器）。
**Status**: Complete

## Stage 7: 回归验证与文档更新

**Goal**: 运行受影响测试套件并确认实现与计划一致，必要时更新文档。
**Success Criteria**: 所有相关测试通过；PLAN 状态更新；无额外文档缺口。
**Tests**: `pnpm backend test apps/backend/tests/integration/api/genesis/test_genesis_stage_session_routes.py`。
**Status**: Complete
