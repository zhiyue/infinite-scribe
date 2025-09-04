# LLD 概述 — 小说创世阶段

文档版本: 1.0  
生成日期: 2025-09-05  
对应 HLD: [design-hld.md](../design-hld.md)

## 概述

本 LLD 基于已批准的 [HLD](../design-hld.md)，细化"小说创世阶段（Stage 0–5）"的实现细节。

**文档关系说明**：

- **HLD ([design-hld.md](../design-hld.md))** - 架构决策、组件交互、数据流设计
- **LLD (本系列文档)** - 具体实现、代码规范、数据库模式、API细节

本文档包含从 HLD 中提取的所有实现层细节，覆盖 API/会话服务、事件与 Outbox、Orchestrator、专门化 Agents、EventBridge（Kafka→Redis SSE）、数据模型（PostgreSQL/Neo4j/Milvus）、异常与重试、测试与容量、部署与回滚等。P1 聚焦"至少一次 + 事务性 Outbox + Kafka"链路与基础安全；P2 预留 Prefect 编排与 RBAC。

## 文档结构

- [概述](overview.md) - 本文档
- [组件详细设计](components.md) - API、Orchestrator、EventBridge、Agents
- [事件设计](events.md) - 事件命名、序列化、Topic映射
- [前端组件](frontend.md) - 前端组件和API端点设计
- [数据模型](data-models.md) - PostgreSQL、Neo4j、Milvus数据模型
- [业务逻辑](business-logic.md) - 质量评分、一致性校验、批量任务
- [版本控制](versioning.md) - 版本控制实现
- [SSE实现](sse.md) - SSE详细实现规范
- [错误处理](error-handling.md) - 异常处理与重试机制
- [部署运维](deployment.md) - 回滚、容量、测试、部署和依赖管理