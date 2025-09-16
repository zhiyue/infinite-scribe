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
