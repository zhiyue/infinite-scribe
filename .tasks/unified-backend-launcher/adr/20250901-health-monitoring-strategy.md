---
id: ADR-20250901-health-monitoring-strategy
title: 健康监控策略与状态管理设计
status: Proposed
date: 2025-09-01
decision_makers: [platform-arch, backend-lead, sre]
related_requirements: [FR-003, NFR-002, NFR-003]
related_stories: [STORY-003]
supersedes: []
superseded_by: null
tags: [monitoring, health-check, observability]
---

# 健康监控策略与状态管理设计

## Status
Proposed

## Context

### Business Context
统一后端启动器需要提供实时的服务状态监控，包括启动过程中的状态跟踪、健康检查和故障诊断信息，确保系统的可观测性和故障快速定位。
- 相关用户故事：STORY-003 实时状态监控
- 业务价值：提升系统可观测性，加速故障诊断，提供运维数据支持
- 业务约束：必须支持现有的health check接口，不影响服务性能

### Technical Context
- 当前架构：各服务独立的health check endpoint，基础的连接状态检查
- 现有技术栈：FastAPI健康检查endpoints，service层的check_connection方法
- 现有约定：
  - 数据库服务通过`check_connection()`方法检查状态
  - API Gateway提供`/health`端点
  - 服务启动时记录基础日志信息
- 集成点：需要监控API Gateway, Agent services, Database services, External dependencies

### Requirements Driving This Decision
- FR-003: 系统SHALL实时显示每个服务的状态（启动中/已启动/启动失败）
- NFR-002: 启动成功率 >= 95%
- NFR-003: 服务状态查询响应时间 < 200毫秒

### Constraints
- 技术约束：监控系统不能显著影响服务性能
- 业务约束：必须与现有健康检查接口兼容
- 成本约束：避免引入复杂的监控基础设施

## Decision Drivers
- 实时性：快速反映服务状态变化
- 准确性：精确的健康状态判断和故障检测
- 性能：最小化监控对服务性能的影响
- 可扩展性：支持新服务类型的监控集成
- 诊断能力：提供详细的故障信息和日志引用

## Considered Options

### Option 1: 扩展现有Health Check - 轮询聚合模式
- **描述**：扩展现有的health check endpoints，通过定时轮询收集状态，在启动器中聚合和展示
- **与现有架构的一致性**：高 - 基于现有health check模式
- **实现复杂度**：低 - 主要是轮询和聚合逻辑
- **优点**：
  - 与现有健康检查完全兼容
  - 实现简单，维护成本低
  - 不需要修改现有服务代码
  - 支持现有的监控工具集成
- **缺点**：
  - 轮询延迟影响状态更新实时性
  - 难以捕获瞬时状态变化
  - 缺乏细粒度的状态信息
- **风险**：轮询频率与性能的平衡，网络延迟影响

### Option 2: 事件驱动监控 - 状态事件流
- **描述**：设计事件驱动的监控系统，服务状态变化时发送事件，启动器订阅和聚合状态事件
- **与现有架构的一致性**：中 - 需要为服务添加事件发送能力
- **实现复杂度**：中 - 事件系统和状态聚合逻辑
- **优点**：
  - 实时的状态更新能力
  - 支持细粒度的状态变化跟踪
  - 更好的性能特性
  - 支持状态历史和趋势分析
- **缺点**：
  - 需要修改现有服务以支持事件发送
  - 事件系统的复杂度和可靠性挑战
  - 需要额外的事件传输机制
- **风险**：事件丢失或重复，系统复杂度增加

### Option 3: 混合监控模式 - 推拉结合
- **描述**：结合轮询和事件驱动，关键状态变化通过事件推送，定期轮询作为兜底和验证机制
- **与现有架构的一致性**：中 - 需要适配现有接口并添加事件能力
- **实现复杂度**：中 - 推拉结合的协调逻辑
- **优点**：
  - 平衡实时性和可靠性
  - 支持渐进式集成
  - 兜底机制提高可靠性
  - 灵活的监控粒度控制
- **缺点**：
  - 系统复杂度较高
  - 推拉协调的逻辑复杂性
  - 需要管理两套状态更新机制
- **风险**：推拉状态不一致，协调逻辑的bug

## Decision
[待定 - 将在设计评审后填写]

## Consequences
### Positive
- 提供实时、准确的服务状态监控
- 加速故障诊断和问题定位
- 提升系统运维和观测能力

### Negative
- 增加监控系统的开发和维护成本
- 可能对服务性能产生轻微影响
- 需要新的监控数据存储和查询机制

### Risks
- 监控系统本身的可用性影响 - 通过简化设计和快速恢复机制缓解
- 状态检查的性能开销 - 通过异步检查和缓存策略缓解
- 监控数据的存储和清理 - 通过数据保留策略和自动清理缓解

## Implementation Plan
[待定 - 将在决策接受后填写]

### Integration with Existing Architecture
- **代码位置**：
  - `apps/backend/src/monitoring/` - 监控核心模块
  - `apps/backend/src/monitoring/collectors/` - 状态收集器
  - `apps/backend/src/monitoring/aggregators/` - 状态聚合器
- **模块边界**：
  - 监控系统独立于业务逻辑
  - 收集器适配不同服务的监控接口
  - 聚合器负责状态汇总和展示
- **依赖管理**：通过现有的健康检查接口，最小化对现有服务的侵入

### Migration Strategy
- **阶段1**：实现基础的轮询监控和状态聚合
- **阶段2**：为关键服务添加事件推送能力
- **阶段3**：优化监控性能和添加高级诊断功能
- **向后兼容**：保持所有现有健康检查接口不变

### Rollback Plan
- **触发条件**：监控系统影响服务性能 > 5% 或监控准确率 < 90%
- **回滚步骤**：
  1. 禁用监控聚合，保留基础健康检查
  2. 回退到服务独立的状态展示
  3. 移除监控相关的性能开销
- **数据恢复**：监控数据可以清理，不影响业务数据

## Validation

### Alignment with Existing Patterns
- **架构一致性检查**：与现有health check endpoint模式对齐
- **代码审查重点**：监控性能影响，状态准确性验证，异常处理机制

### Metrics
- **性能指标**：
  - 状态查询响应时间：< 200ms
  - 监控开销：服务性能影响 < 2%
  - 状态更新延迟：< 5s（轮询模式）或 < 1s（事件模式）
- **质量指标**：
  - 监控准确率：≥ 95%
  - 故障检测时间：< 10s

### Test Strategy
- **单元测试**：状态收集器，聚合逻辑，故障检测算法
- **集成测试**：与现有健康检查集成，端到端状态监控测试
- **性能测试**：监控系统的性能影响基准测试
- **回归测试**：确保现有健康检查功能不受影响

## References
- 现有健康检查: `apps/backend/src/api/routes/health.py`
- 服务连接检查: `apps/backend/src/common/services/`
- FastAPI health endpoints: `apps/backend/src/api/main.py`

## Changelog
- 2025-09-01: 初始草稿创建