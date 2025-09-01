---
id: ADR-20250901-development-mode-enhancement
title: 开发模式增强与热重载机制设计
status: Proposed
date: 2025-09-01
decision_makers: [backend-lead, devex-lead]
related_requirements: [FR-005, NFR-003, NFR-005]
related_stories: [STORY-005]
supersedes: []
superseded_by: null
tags: [development, hot-reload, debugging]
---

# 开发模式增强与热重载机制设计

## Status
Proposed

## Context

### Business Context
统一后端启动器需要在开发环境中提供热重载、调试支持和详细日志输出，以提升开发效率和调试体验，减少开发周期中的反馈延迟。
- 相关用户故事：STORY-005 开发模式增强
- 业务价值：提升开发效率，减少调试时间，改善开发者体验
- 业务约束：开发模式不能影响生产环境性能，必须支持IDE集成

### Technical Context
- 当前架构：FastAPI的--reload模式，手动重启Agent服务
- 现有技术栈：uvicorn --reload，Python标准logging，手动调试流程
- 现有约定：
  - 使用uvicorn --reload启动API Gateway
  - Agent服务需要手动重启以应用代码变更
  - 调试通过print和logging进行
- 集成点：需要监控代码文件变更，集成调试端口，统一日志管理

### Requirements Driving This Decision
- FR-005: 系统SHALL自动启用热重载和调试功能（开发环境检测）
- NFR-003: 代码变更检测到服务重启完成 < 10秒
- NFR-005: 统一的日志格式和级别管理

### Constraints
- 技术约束：不能影响生产环境的性能和稳定性
- 业务约束：必须支持主流IDE的调试器集成
- 成本约束：文件监控不能消耗过多系统资源

## Decision Drivers
- 开发效率：快速的代码变更反馈循环
- 调试能力：支持断点调试和IDE集成
- 文件监控：准确的变更检测和合理的重启策略
- 日志管理：开发调试友好的日志输出
- 环境隔离：开发功能不影响生产部署

## Considered Options

### Option 1: 扩展uvicorn reload - 多服务文件监控
- **描述**：扩展uvicorn的--reload机制，添加对Agent服务的文件监控，使用watchdog实现统一的文件变更检测
- **与现有架构的一致性**：高 - 基于现有uvicorn reload模式
- **实现复杂度**：低 - 主要是文件监控和重启逻辑
- **优点**：
  - 与现有FastAPI reload模式一致
  - 利用成熟的uvicorn重启机制
  - 实现简单，维护成本低
  - 开发者熟悉的工作模式
- **缺点**：
  - uvicorn reload仅支持单个应用
  - 难以实现细粒度的服务重启控制
  - 缺乏对Agent服务的原生支持
- **风险**：多服务重启的协调复杂度

### Option 2: 自定义热重载引擎 - 分层文件监控
- **描述**：开发专门的热重载引擎，支持不同服务类型的文件监控策略，提供细粒度的重启控制和调试端口管理
- **与现有架构的一致性**：中 - 需要替换现有reload机制
- **实现复杂度**：中 - 文件监控引擎和服务重启协调
- **优点**：
  - 支持细粒度的服务重启控制
  - 可以针对不同服务类型优化重启策略
  - 支持调试端口的动态分配
  - 更好的重启性能和资源控制
- **缺点**：
  - 需要开发和维护自定义引擎
  - 可能与IDE的默认集成不兼容
  - 文件监控的跨平台兼容性挑战
- **风险**：自定义引擎的稳定性和维护成本

### Option 3: IDE集成优先 - 调试协议适配
- **描述**：优化IDE调试器集成，支持remote debugging和DAP协议，结合简单的文件监控实现开发模式
- **与现有架构的一致性**：中 - 需要添加调试协议支持
- **实现复杂度**：中 - 调试协议实现和IDE适配
- **优点**：
  - 优秀的IDE集成和调试体验
  - 支持断点调试和变量检查
  - 标准化的调试协议支持
  - 更好的开发者体验
- **缺点**：
  - 调试协议的实现复杂度
  - 需要配置和学习新的调试流程
  - 可能影响热重载的响应速度
- **风险**：调试协议兼容性，IDE配置复杂度

## Decision
[待定 - 将在设计评审后填写]

## Consequences
### Positive
- 显著提升开发效率和调试体验
- 减少代码变更的反馈时间
- 提供专业的IDE集成支持

### Negative
- 增加开发模式的复杂度和维护成本
- 文件监控可能消耗额外系统资源
- 需要新的开发工具和文档

### Risks
- 文件监控的性能影响 - 通过智能过滤和节流机制缓解
- 热重载的稳定性问题 - 通过异常恢复和服务隔离缓解
- IDE集成的兼容性挑战 - 通过标准协议和文档支持缓解

## Implementation Plan
[待定 - 将在决策接受后填写]

### Integration with Existing Architecture
- **代码位置**：
  - `apps/backend/src/dev_mode/` - 开发模式核心模块
  - `apps/backend/src/dev_mode/watchers/` - 文件监控器
  - `apps/backend/src/dev_mode/debugger/` - 调试器集成
- **模块边界**：
  - 开发模式模块只在开发环境激活
  - 文件监控与服务管理分离
  - 调试支持作为可选功能
- **依赖管理**：开发依赖与生产依赖严格分离，通过环境检测激活

### Migration Strategy
- **阶段1**：实现基础的文件监控和自动重启
- **阶段2**：添加调试端口支持和IDE集成
- **阶段3**：优化重启性能和增加高级调试特性
- **向后兼容**：保持现有的--reload模式完全兼容

### Rollback Plan
- **触发条件**：开发模式影响系统稳定性或重启时间 > 15秒
- **回滚步骤**：
  1. 禁用自动热重载，回退到手动重启
  2. 关闭文件监控和调试端口
  3. 恢复标准的uvicorn --reload模式
- **数据恢复**：不涉及数据变更，仅开发配置恢复

## Validation

### Alignment with Existing Patterns
- **架构一致性检查**：与FastAPI开发模式和现有日志系统对齐
- **代码审查重点**：文件监控性能，重启稳定性，调试安全性

### Metrics
- **性能指标**：
  - 代码变更检测延迟：< 1s
  - 服务重启时间：< 10s
  - 文件监控资源消耗：< 5% CPU
- **质量指标**：
  - 热重载成功率：≥ 95%
  - IDE调试器连接成功率：≥ 90%

### Test Strategy
- **单元测试**：文件监控逻辑，重启协调，调试端口管理
- **集成测试**：与IDE调试器集成，完整的热重载流程测试
- **性能测试**：文件监控性能影响，重启时间基准测试
- **回归测试**：确保生产模式不受开发功能影响

## References
- uvicorn reload实现: [uvicorn auto-reload](https://www.uvicorn.org/#command-line-options)
- Python调试协议: [DAP Protocol](https://microsoft.github.io/debug-adapter-protocol/)
- 文件监控库: [watchdog](https://python-watchdog.readthedocs.io/)

## Changelog
- 2025-09-01: 初始草稿创建