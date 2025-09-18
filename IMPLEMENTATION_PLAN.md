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

## Stage 5: 统一 StageConfig 对话框底部操作栏

**Goal**: 让 StageConfigModal 与 StageConfigForm 使用单一底部操作栏，消除视觉重复。
**Success Criteria**: 模态底部仅显示一组按钮；保存/刷新/放弃逻辑仍可用；禁用态下按钮正确灰显。
**Tests**: `pnpm --filter @infinitescribe/frontend lint`（已因现有其他文件问题失败，需后续单独处理）。
**Status**: Complete

## Stage 6: 梳理数组字段显示问题

**Goal**: 复现并记录特殊要求等数组字段的显示问题，明确需要的布局与交互调整。
**Success Criteria**: 完成现状截图/描述，确定需要修改的组件与样式细节。
**Tests**: 手动检查 StageConfigModal（初始灵感阶段）渲染效果。
**Status**: Complete

## Stage 7: 优化数组字段模板布局

**Goal**: 更新自定义 ArrayFieldTemplate 布局，改善编号、按钮和输入区域的排版；去除重复标题。
**Success Criteria**: 特殊要求/性格偏好等数组项显示更紧凑、编号清晰、按钮排列整齐；表单交互无回归。
**Tests**: `pnpm --filter @infinitescribe/frontend lint`，手动检查 Genesis Stage 表单。
**Status**: Complete

## Stage 8: 更新 UI Schema 与回归验证

**Goal**: 为数组项提供 placeholder/label 配置，隐藏冗余标题，并完成基础回归验证。
**Success Criteria**: 表单项不再显示 ``-1`` 后缀标题，placeholder 正确出现；相关 lint/test 通过或记录已知阻塞。
**Tests**: `pnpm --filter @infinitescribe/frontend lint`，手动回归 StageConfig 表单。
**Status**: Complete
