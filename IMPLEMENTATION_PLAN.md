## Stage 1: 编排流程现状梳理

**Goal**: 明确 `DomainEventProcessor` 的命令处理链路与可插入的意图识别位置  
**Success Criteria**: 列出命令映射、可安全覆盖的 command_type（预计聚焦 Details.Request）以及能力任务路由点  
**Tests**: 无（分析阶段）  
**Status**: Complete

## Stage 2: LLM 意图分类器实现

**Goal**: 新增 `CommandIntentClassifier`，支持 LLM + 规则兜底并可依赖注入  
**Success Criteria**: 成功返回 `query` / `question` / `feedback_generation`，异常时回退到规则推断  
**Tests**: 单元测试模拟 LLM 响应与异常兜底  
**Status**: Complete

## Stage 3: 编排器集成与路由调整

**Goal**: 在 `DomainEventProcessor` 中接入分类器，针对启用的命令类型写入 `intent` 并根据意图调整能力任务  
**Success Criteria**: `feedback_generation` 能切换到 review 任务主题，其余意图保持原始逻辑但带上标注；领域事件保持幂等  
**Tests**: 单元测试验证 Details.Request 的映射与出队消息  
**Status**: Complete

## Stage 4: 测试覆盖与文档说明

**Goal**: 增补/更新测试与 README（如需），确保新增行为可回归  
**Success Criteria**: 相关测试通过，必要处标明意图路由策略  
**Tests**: pytest 针对新增测试用例  
**Status**: Complete
