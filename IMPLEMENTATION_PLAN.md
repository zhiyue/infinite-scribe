## Stage 1: 明确对话集成测试依赖缺失原因

**Goal**: 分析 `apps/backend/tests/integration/domains/conversation` 当前失败堆栈，确认 `testcontainers` 模块缺失是否由依赖配置或运行方式导致。
**Success Criteria**: 梳理出问题成因，列出需要修改的文件或脚本。
**Tests**: `uv run pytest apps/backend/tests/integration/domains/conversation -k kafka -q`
**Status**: In Progress

## Stage 2: 修复依赖加载流程

**Goal**: 调整依赖或测试装置，确保运行集成测试时能够正确加载 Kafka 所需容器依赖并初始化环境。
**Success Criteria**: 本地执行入口可成功导入 `testcontainers.kafka.KafkaContainer` 并启动所需资源。
**Tests**: `uv run python -c "import testcontainers.kafka"`
**Status**: Not Started

## Stage 3: 验证对话域集成测试

**Goal**: 运行并通过 `apps/backend/tests/integration/domains/conversation` 下所有测试。
**Success Criteria**: 目标测试全部通过且无新增回归。
**Tests**: `uv run pytest apps/backend/tests/integration/domains/conversation -q`
**Status**: Not Started
