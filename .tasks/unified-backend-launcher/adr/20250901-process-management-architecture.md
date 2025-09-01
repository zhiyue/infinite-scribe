---
id: ADR-20250901-process-management-architecture
title: 统一后端启动器进程管理架构选型
status: Proposed
date: 2025-09-01
decision_makers: [platform-arch, backend-lead]
related_requirements: [FR-001, NFR-001, NFR-004]
related_stories: [STORY-001]
supersedes: []
superseded_by: null
tags: [architecture, performance, resource-management]
---

# 统一后端启动器进程管理架构选型

## Status
Proposed

## Context

### Business Context
统一后端启动器需要支持单进程和多进程两种运行模式，以满足不同开发和部署场景的需求。
- 相关用户故事：STORY-001 统一服务启动管理
- 业务价值：提升开发效率，简化服务管理，降低资源消耗
- 业务约束：需要与现有pnpm脚本工作流100%兼容

### Technical Context
- 当前架构：FastAPI + AgentLauncher的多服务架构，每个服务独立运行
- 现有技术栈：Python 3.11, FastAPI, asyncio, SQLAlchemy, Docker
- 现有约定：
  - 服务通过FastAPI lifespan管理生命周期
  - 数据库服务通过service层统一管理
  - Agent服务使用AgentLauncher进行启动和管理
- 集成点：API Gateway, Agent services, Database services (PostgreSQL, Redis, Neo4j)

### Requirements Driving This Decision
- FR-001: 系统SHALL提供单进程和多进程两种运行模式选择
- NFR-001: 单进程模式相比多进程模式资源开销降低 >= 30%
- NFR-004: 与现有pnpm脚本工作流100%兼容

### Constraints
- 技术约束：必须基于Python 3.11和asyncio
- 业务约束：不能破坏现有API契约
- 成本约束：开发和维护成本需要可控

## Decision Drivers
- 资源效率：单进程模式需要显著减少内存和CPU使用
- 开发体验：简化本地开发环境搭建
- 生产部署：支持灵活的部署模式选择
- 架构一致性：与现有FastAPI和AgentLauncher模式对齐
- 故障隔离：多进程模式需要保证服务间故障隔离

## Considered Options

### Option 1: 扩展现有AgentLauncher - 单FastAPI实例管理
- **描述**：扩展现有AgentLauncher，在单进程模式下所有服务共享同一个FastAPI实例，将Agent作为后台任务运行
- **与现有架构的一致性**：高 - 基于现有AgentLauncher模式
- **实现复杂度**：低 - 主要是扩展现有代码
- **优点**：
  - 与现有代码库高度一致
  - 团队对AgentLauncher已经熟悉
  - 最小化代码重复
  - 保持现有服务接口不变
- **缺点**：
  - FastAPI实例共享可能导致路由冲突
  - 服务间依赖不清晰
  - 难以实现细粒度的服务控制
- **风险**：路由命名空间冲突，服务耦合度增加

### Option 2: 独立启动器 + 进程池管理
- **描述**：创建新的统一启动器，使用multiprocessing.Pool管理多个FastAPI服务进程，单进程模式使用async.gather并发运行
- **与现有架构的一致性**：中 - 需要创建新的管理层
- **实现复杂度**：中 - 需要进程间通信和状态同步
- **优点**：
  - 清晰的进程边界和故障隔离
  - 支持细粒度的服务控制
  - 更好的可扩展性
  - 独立的健康检查和监控
- **缺点**：
  - 进程间通信复杂度增加
  - 需要额外的状态同步机制
  - 资源监控和管理更复杂
- **风险**：进程间通信延迟，状态一致性问题

### Option 3: 混合架构 - 组件化FastAPI + 动态路由
- **描述**：设计组件化的FastAPI架构，API Gateway作为主服务，Agent作为可插拔组件，根据模式动态加载路由和启动后台任务
- **与现有架构的一致性**：中 - 需要重构现有服务结构
- **实现复杂度**：中 - 需要设计组件系统和动态路由
- **优点**：
  - 平衡资源效率和服务隔离
  - 支持细粒度的服务控制
  - 良好的可测试性
  - 保持FastAPI的特性优势
- **缺点**：
  - 需要重构现有Agent架构
  - 组件间依赖管理复杂
  - 路由动态加载的复杂性
- **风险**：重构风险，组件接口设计复杂度

## Decision
[待定 - 将在设计评审后填写]

## Consequences
### Positive
- 提供灵活的部署模式选择
- 提升开发环境的资源效率
- 简化服务启动和管理流程

### Negative
- 增加系统架构复杂度
- 需要新的监控和调试工具
- 可能影响现有服务的独立性

### Risks
- 单进程模式下服务故障传播风险 - 通过异常隔离和重试机制缓解
- 进程间状态同步复杂度 - 通过Redis作为状态存储缓解
- 现有Agent重构风险 - 通过渐进式迁移策略缓解

## Implementation Plan
[待定 - 将在决策接受后填写]

### Integration with Existing Architecture
- **代码位置**：`apps/backend/src/launcher/` - 新的启动器模块
- **模块边界**：
  - 启动器负责进程管理和生命周期
  - 服务层保持现有接口不变
  - Agent保持现有实现，通过适配器集成
- **依赖管理**：通过现有的依赖注入系统，避免引入新的依赖管理机制

### Migration Strategy
- **阶段1**：创建基础启动器框架，支持多进程模式
- **阶段2**：实现单进程模式，集成现有API Gateway
- **阶段3**：集成Agent服务，验证功能和性能
- **向后兼容**：保持现有pnpm脚本接口，内部调用新的启动器

### Rollback Plan
- **触发条件**：性能指标不达标或关键功能失效
- **回滚步骤**：
  1. 恢复原有的独立服务启动脚本
  2. 删除新的启动器代码
  3. 恢复原有的pnpm脚本配置
- **数据恢复**：不涉及数据变更，仅代码回滚

## Validation

### Alignment with Existing Patterns
- **架构一致性检查**：与FastAPI lifespan管理模式对齐
- **代码审查重点**：服务边界设计，异常处理机制，资源管理策略

### Metrics
- **性能指标**：
  - 启动时间：多进程 60s → 单进程 30s
  - 内存使用：多进程 100% → 单进程 ≤ 70%
  - CPU使用：空闲时单进程模式 ≤ 多进程模式的 70%
- **质量指标**：
  - 代码覆盖率：≥ 85%
  - 启动成功率：≥ 95%

### Test Strategy
- **单元测试**：启动器组件，服务管理逻辑，异常处理
- **集成测试**：与现有API Gateway和Agent集成测试
- **性能测试**：资源使用对比，启动时间基准测试
- **回归测试**：确保现有API功能不受影响

## References
- 现有AgentLauncher实现: `apps/backend/src/agents/launcher.py`
- FastAPI lifespan管理: `apps/backend/src/api/main.py`
- 项目架构文档: `docs/architecture/`

## Changelog
- 2025-09-01: 初始草稿创建