# 小说创世阶段 - 低层设计文档集

本目录包含小说创世阶段（Stage 0-5）的详细低层设计文档，已从原始的 `design-lld.md` 文件按逻辑模块分割为多个独立文档。

## 文档结构

### 核心设计文档

1. **[概述](overview.md)** - 项目概述和文档关系说明
2. **[组件详细设计](components.md)** - API服务、Orchestrator、EventBridge、Agents 的详细实现
3. **[事件设计](events.md)** - 事件命名规范、序列化实现、Topic映射
4. **[前端组件](frontend.md)** - 前端组件设计和API端点定义
5. **[数据模型](data-models.md)** - PostgreSQL、Neo4j、Milvus 数据模型设计

### 业务逻辑实现

6. **[业务逻辑](business-logic.md)** - 质量评分、一致性校验、批量任务调度
7. **[版本控制](versioning.md)** - 创世内容版本化实现策略
8. **[SSE实现](sse.md)** - Server-Sent Events 详细实现规范

### 运维与部署

9. **[错误处理](error-handling.md)** - 异常分类与重试机制
10. **[部署运维](deployment.md)** - 回滚、容量、测试、CI/CD、依赖管理

## 实现阶段

文档设计支持分阶段实现：

- **P1 阶段**：基础事件驱动架构，简单调度，至少一次投递保证
- **P2 阶段**：Prefect 工作流编排，RBAC 权限控制，高级功能

## 技术栈

- **后端**: Python 3.11 + FastAPI
- **数据库**: PostgreSQL (主存储) + Redis (缓存/SSE) + Neo4j (图模型) + Milvus (向量检索)  
- **消息队列**: Kafka (事件总线)
- **工作流**: Prefect (P2阶段)
- **前端**: React + TypeScript

## 关键特性

- **事件溯源**: 完整的事件存储和重放能力
- **事务性Outbox**: 可靠的事件投递机制  
- **点式命名**: 统一的事件类型命名规范
- **质量评分**: 多维度内容质量自动评估
- **一致性校验**: Neo4j 图数据一致性验证
- **版本控制**: 创世内容的版本化管理

## 使用指南

1. 从 [概述](overview.md) 开始了解整体架构
2. 查看 [组件详细设计](components.md) 了解核心组件
3. 参考 [事件设计](events.md) 理解事件流转
4. 根据实现需求查看相应的专项文档

## 文档维护

- 文档版本: 1.0
- 生成日期: 2025-09-05  
- 对应 HLD: [design-hld.md](../design-hld.md)

各文档保持相互引用和一致性，如有更新请同步修改相关文档。