## Stage 1: 修复阶段配置 Schema 辅助方法

**Goal**: 为 Genesis 阶段配置提供示例模板获取函数，并修正 `get_all_stage_config_schemas` 输出。
**Success Criteria**: 新增的模板函数返回每个阶段配置的示例数据；调用不再抛出 `ValidationError`。
**Tests**: `pytest apps/backend/tests/unit/schemas/test_genesis_stage_config_schemas.py::TestStageConfigTemplates`。
**Status**: Complete

## Stage 2: 修正 API 端点配置校验错误处理

**Goal**: 更新 Genesis Flow API 中配置校验逻辑，统一捕获 `ValidationError` 并返回 400。
**Success Criteria**: `CreateStageRequest` 和 `update_stage_config_endpoint` 在配置错误时返回可读错误信息；模板端点可返回示例。
**Tests**: `pytest apps/backend/tests/integration/api/genesis/test_flows_api.py::TestGenesisStagesConfigAPI`。
**Status**: Complete

## Stage 3: 扩充单元与集成测试

**Goal**: 为新模板函数和 API 错误处理补充测试覆盖，验证正常及异常路径。
**Success Criteria**: 新增测试在旧实现下失败，在修复后通过。
**Tests**: `pytest apps/backend/tests/unit/schemas/test_genesis_stage_config_schemas.py apps/backend/tests/integration/api/genesis/test_stage_config_api.py`。
**Status**: Complete

## Stage 4: 回归验证

**Goal**: 运行受影响测试套件确认修改正确。
**Success Criteria**: 上述测试全部绿灯，PLAN 状态更新。
**Tests**: `pnpm backend test --filter genesis-stage-config`（或等效 pytest 命令）。
**Status**: In Progress
