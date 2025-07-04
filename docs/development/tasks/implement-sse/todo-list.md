# SSE 实现任务清单

> **MVP 说明**：当前项目处于 MVP 阶段，仅需实施 P0 优先级的核心功能。P1 和 P2 任务将在 MVP 验证成功后的后续版本中实施。

## P0 - 立即实施（MVP 必须）

### 数据模型与契约定义
- [ ] **创建 SSE 事件模型** [2h]
  - [ ] 创建 `/packages/shared-types/src/sse_events.py`
  - [ ] 定义 SSEMessage 基类（包含 event, data, id, retry, scope, version 字段）
  - [ ] 定义具体事件类型（TaskProgressEvent, TaskStatusChangeEvent, SystemNotificationEvent, ContentUpdateEvent, SSEErrorEvent）
  - [ ] 实现 to_sse_format() 方法
  - [ ] 更新 `/packages/shared-types/src/index.ts` 添加 TypeScript 类型

- [ ] **创建 Kafka → SSE 映射文档** [1h]
  - [ ] 在 `docs/development/sse-event-mapping.md` 创建映射表
  - [ ] 定义事件命名规范（domain.action-past）
  - [ ] 明确每个 Kafka 事件对应的 SSE 事件格式
  - [ ] 定义数据转换规则（精简字段、权限过滤）

### 事件补偿机制
- [ ] **设计事件补偿方案** [3h]
  - [ ] 实现事件 ID 生成器（格式：{source}:{partition}:{offset}）
  - [ ] 设计 Redis 事件缓存结构（使用 Redis Stream）
  - [ ] 实现 Last-Event-ID 解析器
  - [ ] 实现事件重放逻辑（从 Kafka/Redis 获取历史事件）

### 核心后端组件
- [ ] **创建目录结构** [0.5h]
  - [ ] `/apps/backend/src/api/v1/events/`
  - [ ] `/apps/backend/src/services/sse/`
  - [ ] `/apps/backend/src/adapters/events/`

- [ ] **实现 EventBus 接口（Protocol/ABC）** [2h]
  - [ ] 定义抽象接口，支持多种消息中间件
  - [ ] 实现 Kafka 适配器
  - [ ] 实现 Redis 适配器
  - [ ] 确保与 Transactional Outbox 集成

- [ ] **实现 Event Adapter 层** [3h]
  - [ ] Kafka 事件 → SSE 事件转换器
  - [ ] 权限过滤器（基于 user_id, novel_id, session_id）
  - [ ] 数据精简处理（移除敏感字段）
  - [ ] 批量转换优化

- [ ] **实现 SSEManager 核心功能** [4h]
  - [ ] 连接池管理（使用 asyncio.Queue）
  - [ ] 基于 JWT 的认证检查
  - [ ] 多标签订阅支持
  - [ ] ~~背压机制（队列满时丢弃低优先级事件）~~ *[后期实施]*
  - [ ] ~~心跳机制（每 15s 发送 `:\n\n`）~~ *[后期实施]*

- [ ] **实现 SSE 端点** [3h]
  - [ ] `/api/v1/events/stream` GET 端点
  - [ ] StreamingResponse 实现
  - [ ] Last-Event-ID 头部处理
  - [ ] 查询参数解析（filter context）
  - [ ] ~~速率限制中间件（20 连接/分钟）~~ *[后期实施]*

## P1 - 实现前完善（后期实施）

### 前端实现
- [ ] **实现 SSE 客户端基础** [3h]
  - [ ] 创建 `/apps/frontend/src/services/sse/SSEClient.ts`
  - [ ] EventSource 封装（包含认证头）
  - [ ] 自动重连（指数退避）
  - [ ] Last-Event-ID 持久化

- [ ] **实现 React 集成** [4h]
  - [ ] 创建 SSEProvider Context
  - [ ] 实现 useSSE Hook
  - [ ] 事件类型安全处理
  - [ ] 与 TanStack Query 集成（自动 invalidate）

- [ ] **替换现有轮询** [2h]
  - [ ] 识别所有轮询代码
  - [ ] 逐步替换为 SSE 订阅
  - [ ] 保留降级到轮询的开关

### 监控与可观测性
- [ ] **实现 Prometheus 指标** [3h]
  - [ ] sse_current_connections
  - [ ] sse_connection_duration
  - [ ] sse_events_sent_total
  - [ ] sse_event_delivery_lag
  - [ ] sse_queue_size
  - [ ] sse_queue_overflow_total

- [ ] **实现结构化日志** [2h]
  - [ ] 连接建立/断开日志
  - [ ] 事件发送日志
  - [ ] 错误和异常日志
  - [ ] 性能采样日志

- [ ] **创建 Grafana Dashboard** [2h]
  - [ ] 连接监控面板
  - [ ] 性能监控面板
  - [ ] 错误监控面板
  - [ ] 业务指标面板

### 测试
- [ ] **单元测试** [4h]
  - [ ] SSEManager 测试
  - [ ] EventBus 测试
  - [ ] Event Adapter 测试
  - [ ] 事件补偿逻辑测试

- [ ] **集成测试** [4h]
  - [ ] 端到端事件流测试
  - [ ] 断线重连测试
  - [ ] 权限拒绝测试
  - [ ] 事件重放测试

- [ ] **前端测试** [3h]
  - [ ] SSEProvider 测试
  - [ ] useSSE Hook 测试
  - [ ] 模拟断线场景
  - [ ] TanStack Query 集成测试

### 文档
- [ ] **API 文档更新** [2h]
  - [ ] SSE 端点文档
  - [ ] 事件类型说明
  - [ ] 认证要求
  - [ ] 示例代码

- [ ] **开发者指南** [2h]
  - [ ] SSE 使用指南
  - [ ] 事件订阅示例
  - [ ] 故障排除指南
  - [ ] 最佳实践

## P2 - 上线前优化（后期实施）

### 性能优化
- [ ] **压力测试** [4h]
  - [ ] 5k 并发连接测试
  - [ ] 10k 并发连接测试
  - [ ] 内存使用分析
  - [ ] CPU 使用分析
  - [ ] 网络带宽测试

- [ ] **性能调优** [3h]
  - [ ] 考虑使用 uvloop
  - [ ] 实现连接分片（如需要）
  - [ ] 优化事件序列化
  - [ ] 实现事件批处理

### 运维配置
- [ ] **负载均衡器配置** [2h]
  - [ ] Nginx proxy_read_timeout 设置
  - [ ] ALB/NLB idle timeout 配置
  - [ ] 缓冲区优化
  - [ ] Keep-alive 设置

- [ ] **灰度发布支持** [3h]
  - [ ] 实现版本标识头（X-Server-Version）
  - [ ] 连接迁移策略
  - [ ] 蓝绿部署脚本
  - [ ] 回滚方案

### 安全加固
- [ ] **安全审计** [2h]
  - [ ] 权限检查完整性
  - [ ] 速率限制有效性
  - [ ] 输入验证
  - [ ] XSS 防护

- [ ] **DDoS 防护** [2h]
  - [ ] 连接数限制
  - [ ] IP 黑名单
  - [ ] 异常检测
  - [ ] 自动熔断

### E2E 场景测试
- [ ] **核心场景覆盖** [4h]
  - [ ] 正常事件流
  - [ ] 断线重连 + 事件补偿
  - [ ] 权限变更
  - [ ] 高负载降级
  - [ ] 跨版本兼容性

## 任务统计

### MVP 阶段（当前）
- **P0 任务**：12 项，预计 29.5 小时（MVP 必须完成）

### 后续版本
- **P1 任务**：13 项，预计 35 小时（功能完善）  
- **P2 任务**：10 项，预计 24 小时（性能优化）

### 总计
- **MVP 工作量**：29.5 小时
- **全部工作量**：88.5 小时

## 进行中

（当前没有进行中的任务）

## 已完成

- [x] 任务背景调研
- [x] 技术方案设计
- [x] 架构图绘制
- [x] 任务计划制定
- [x] 架构评审和改进