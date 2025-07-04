# 实现 Server-Sent Events (SSE) 支持

## 任务背景

当前系统使用 HTTP 轮询（30秒间隔）来获取实时更新，这种方式存在以下问题：
- 延迟高：最多需要等待30秒才能看到更新
- 资源浪费：大量无效的轮询请求
- 用户体验差：需要手动刷新才能及时看到最新状态

根据产品需求文档（PRD），系统需要实现 SSE 以支持：
- 实时的任务进度更新
- 状态变化的即时通知
- 新内容的自动推送
- 无需手动刷新的用户体验

## 目标

1. **实现后端 SSE 端点**
   - 创建 `/api/v1/events/stream` 端点（已在 REST API 规范中定义）
   - 实现 SSEManager 管理连接和事件分发
   - 集成 Kafka/Redis 进行事件订阅和推送

2. **实现前端 SSE 客户端**
   - 使用 EventSource API 连接 SSE 端点
   - 替换现有的轮询机制
   - 实现自动重连和错误处理

3. **支持的事件类型**
   - 任务进度更新（task.progress）
   - 任务状态变化（task.status_change）
   - 系统通知（system.notification）
   - 内容更新（content.update）

## 相关文件

### 设计文档
- `/docs/architecture/rest-api-spec.md` - SSE 端点规范定义
- `/docs/development/ASYNC_TASKS_DATABASE_DESIGN.md` - 异步任务和 SSE 集成设计
- `/docs/prd/epic-2-ai驱动的创世工作室-ai-driven-genesis-studio.md` - 业务需求

### 后端相关
- `/apps/backend/src/api/main.py` - FastAPI 应用主文件
- `/apps/backend/src/api/v1/` - API v1 路由（需要添加 events 路由）
- `/apps/backend/src/services/` - 服务层（需要添加 SSEManager）

### 前端相关
- `/apps/frontend/src/services/api.ts` - API 服务（需要扩展 SSE 支持）
- `/apps/frontend/src/hooks/useHealthCheck.ts` - 当前轮询实现（需要替换）
- `/apps/frontend/src/contexts/` - 上下文管理（需要添加 SSE 上下文）

### 基础设施
- Kafka - 用于事件流处理
- Redis - 用于发布/订阅模式
- PostgreSQL - 存储任务状态和事件日志

## 参考资料

- [FastAPI SSE 文档](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [MDN EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [SSE vs WebSocket 比较](https://www.ruanyifeng.com/blog/2017/05/server-sent_events.html)