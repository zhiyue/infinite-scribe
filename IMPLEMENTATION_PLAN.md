## Stage 1: 审查对话轮次服务测试失败

**Goal**: 明确 `ConversationRoundService` 相关单测失败的根本原因。
**Success Criteria**: 梳理出依赖注入、返回数据结构等与现有实现不符的点，并记录需要的代码改动。
**Tests**: `uv run pytest tests/unit/services/conversation/test_conversation_round_service.py -k list_rounds`
**Status**: Complete

## Stage 2: 调整服务层以恢复兼容接口

**Goal**: 更新 `conversation_round_service`、`conversation_round_query_service` 与 `conversation_round_creation_service`，确保共享依赖、支持注入并返回原始模型对象同时保留序列化数据供缓存使用。
**Success Criteria**: 代码中新增/更新的接口能被测试替换依赖，且返回包含模型对象；静态类型和 lint 通过自检。
**Tests**: `uv run pytest tests/unit/services/conversation/test_conversation_round_query_service.py`
**Status**: In Progress

## Stage 3: 更新并运行相关测试

**Goal**: 调整 `ConversationRoundService` 的单测以契合新接口，并确保所有相关测试通过。
**Success Criteria**: 目标单测全部通过，必要时补充断言覆盖；记录验证命令输出。
**Tests**: `uv run pytest tests/unit/services/conversation/test_conversation_round_service.py`
**Status**: Not Started
