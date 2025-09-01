---
id: ADR-20250901-service-orchestration-framework
title: 服务编排框架选型与依赖管理策略
status: Proposed
date: 2025-09-01
decision_makers: [platform-arch, backend-lead, devops]
related_requirements: [FR-002, FR-004, NFR-002]
related_stories: [STORY-002, STORY-004]
supersedes: []
superseded_by: null
tags: [architecture, service-orchestration, dependency-management]
---

# 服务编排框架选型与依赖管理策略

## Status
Proposed

## Context

### Business Context
统一后端启动器需要管理多个相互依赖的服务（Kafka, PostgreSQL, Redis, API Gateway, Agents），确保正确的启动顺序和优雅的停止机制。
- 相关用户故事：STORY-002 选择性服务控制, STORY-004 优雅停止管理
- 业务价值：确保服务可靠启动，提供细粒度控制，降低运维复杂度
- 业务约束：必须支持部分服务启动，不影响现有服务架构

### Technical Context
- 当前架构：独立的服务启动脚本，手动管理启动顺序
- 现有技术栈：FastAPI lifespan管理，AgentLauncher，Docker Compose服务编排
- 现有约定：
  - 数据库服务在FastAPI启动时连接
  - Agent服务通过AgentLauncher管理生命周期
  - 服务健康检查通过独立的check_connection方法
- 集成点：需要编排API Gateway, Agent集群, 数据库服务, 外部依赖（Kafka）

### Requirements Driving This Decision
- FR-002: 系统SHALL检查服务依赖关系并确保依赖服务优先启动
- FR-004: 系统SHALL优雅关闭所有通过启动器启动的服务
- NFR-002: 优雅停止成功率 >= 99%（零数据丢失）

### Constraints
- 技术约束：必须与现有Docker Compose基础设施兼容
- 业务约束：不能改变现有服务的内部架构
- 成本约束：避免引入复杂的外部编排工具

## Decision Drivers
- 依赖管理：清晰的服务依赖图和启动顺序
- 故障处理：单个服务失效不应影响整个系统
- 资源控制：支持选择性服务启动和资源优化
- 监控能力：实时的服务状态监控和健康检查
- 向后兼容：与现有FastAPI和AgentLauncher模式兼容

## Considered Options

### Option 1: 扩展现有模式 - 依赖图 + AsyncIO编排
- **描述**：基于现有FastAPI lifespan和AgentLauncher，增加依赖图管理，使用asyncio.gather控制启动顺序
- **与现有架构的一致性**：高 - 直接扩展现有模式
- **实现复杂度**：低 - 主要是依赖图逻辑
- **优点**：
  - 与现有代码库完全兼容
  - 利用FastAPI的生命周期管理
  - 简单的异步编排逻辑
  - 最小化学习成本
- **缺点**：
  - 缺乏复杂故障恢复能力
  - 有限的服务监控和控制能力
  - 扩展性受asyncio限制
- **风险**：复杂依赖场景下的死锁问题

### Option 2: 基于状态机的服务编排器
- **描述**：设计专门的服务编排器，使用状态机管理服务生命周期，支持复杂的依赖管理和故障恢复
- **与现有架构的一致性**：中 - 需要适配现有服务接口
- **实现复杂度**：中 - 状态机设计和实现
- **优点**：
  - 清晰的服务状态管理
  - 支持复杂的依赖和故障场景
  - 良好的可测试性和可维护性
  - 详细的状态监控和日志
- **缺点**：
  - 需要设计新的状态模型
  - 增加系统复杂度
  - 需要适配现有服务接口
- **风险**：状态转换逻辑复杂度，调试困难

### Option 3: 轻量级编排 + 监控适配器模式
- **描述**：创建轻量级编排框架，为每个服务创建监控适配器，结合Docker Compose的基础设施能力
- **与现有架构的一致性**：中 - 通过适配器保持兼容
- **实现复杂度**：中 - 适配器设计和编排逻辑
- **优点**：
  - 平衡复杂度和功能性
  - 利用Docker Compose的成熟能力
  - 支持灵活的服务控制
  - 清晰的监控接口
- **缺点**：
  - 需要为每个服务类型设计适配器
  - Docker Compose依赖增加部署复杂度
  - 适配器层增加调试复杂度
- **风险**：适配器一致性维护，Docker依赖管理

## Decision
[待定 - 将在设计评审后填写]

## Consequences
### Positive
- 提供可靠的服务启动和依赖管理
- 支持细粒度的服务控制和监控
- 提升系统可观测性和故障诊断能力

### Negative
- 增加服务编排层的复杂度
- 需要新的监控和调试工具
- 可能影响服务启动性能

### Risks
- 复杂依赖场景下的循环依赖 - 通过依赖图验证和静态分析缓解
- 服务编排器本身成为单点故障 - 通过简单化设计和快速重启缓解
- 现有服务适配成本 - 通过适配器模式和渐进式集成缓解

## Implementation Plan
[待定 - 将在决策接受后填写]

### Integration with Existing Architecture
- **代码位置**：
  - `apps/backend/src/orchestrator/` - 服务编排核心
  - `apps/backend/src/orchestrator/adapters/` - 服务适配器
  - `apps/backend/src/orchestrator/dependencies.py` - 依赖关系定义
- **模块边界**：
  - 编排器负责服务生命周期管理
  - 适配器负责具体服务的控制接口
  - 依赖管理与业务逻辑分离
- **依赖管理**：通过配置文件定义依赖关系，运行时验证

### Migration Strategy
- **阶段1**：设计服务适配器接口和基础编排框架
- **阶段2**：为现有服务创建适配器（Database, API Gateway）
- **阶段3**：集成Agent服务，实现完整的编排能力
- **向后兼容**：通过适配器层保持现有服务接口不变

### Rollback Plan
- **触发条件**：服务编排失败率 > 5% 或依赖管理出现死锁
- **回滚步骤**：
  1. 禁用编排器，恢复手动启动模式
  2. 保留适配器但绕过编排逻辑
  3. 恢复原有的服务启动脚本
- **数据恢复**：不涉及数据变更，仅配置恢复

## Validation

### Alignment with Existing Patterns
- **架构一致性检查**：与FastAPI dependency injection模式对齐
- **代码审查重点**：依赖图设计，适配器接口一致性，异常处理策略

### Metrics
- **性能指标**：
  - 服务启动成功率：≥ 95%
  - 依赖解析时间：< 1s
  - 优雅停止成功率：≥ 99%
- **质量指标**：
  - 依赖图覆盖率：100%（所有服务依赖明确定义）
  - 适配器接口测试覆盖率：≥ 90%

### Test Strategy
- **单元测试**：依赖图算法，状态转换逻辑，适配器实现
- **集成测试**：完整的服务编排场景，故障恢复测试
- **性能测试**：并发启动测试，资源使用监控
- **回归测试**：确保现有服务功能不受影响

## References
- Docker Compose编排模式: `deploy/docker-compose.yml`
- 现有服务健康检查: `apps/backend/src/common/services/`
- FastAPI lifespan管理: `apps/backend/src/api/main.py`

## Changelog
- 2025-09-01: 初始草稿创建