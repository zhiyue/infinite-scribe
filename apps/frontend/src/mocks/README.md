# Frontend Mock Services

使用 MSW (Mock Service Worker) 实现的前端 mock 服务系统。

## 特点

- 🚀 **现代化**: 使用 MSW 在 Service Worker 层面拦截网络请求
- 🎯 **精准**: 只 mock 特定的 API 端点，其他请求正常通过  
- 🛠️ **可配置**: 通过环境变量控制启用/禁用
- 🧪 **开发友好**: 支持开发模式和测试环境
- 🔄 **真实**: 模拟真实的网络延迟和响应

## 快速开始

### 启用/禁用 Mock

通过环境变量控制：

```bash
# 启用 mock (默认)
VITE_USE_MOCK_GENESIS=true

# 禁用 mock，使用真实 API
VITE_USE_MOCK_GENESIS=false
```

### 开发模式

Mock 服务只在开发模式下启用：
- ✅ `NODE_ENV=development` + `VITE_USE_MOCK_GENESIS=true`
- ❌ `NODE_ENV=production` (自动禁用)

## 目录结构

```
src/mocks/
├── README.md                    # 说明文档
├── browser.ts                   # MSW 浏览器配置
├── handlers.ts                  # 统一导出所有 handlers
├── handlers/
│   └── genesis-handlers.ts      # Genesis API mock handlers
└── services/
    └── genesis-mock-service.ts  # Genesis mock 业务逻辑
```

## 支持的 API

### 创世阶段管理
- `GET /api/v1/conversations/sessions/{id}/stage` - 获取当前阶段
- `PUT /api/v1/conversations/sessions/{id}/stage` - 切换阶段

### 对话轮次管理  
- `GET /api/v1/conversations/sessions/{id}/rounds` - 获取对话历史
- `POST /api/v1/conversations/sessions/{id}/messages` - 发送消息
- `POST /api/v1/conversations/sessions/{id}/rounds` - 创建轮次

## 添加新的 Mock

### 1. 创建 Handler

```typescript
// src/mocks/handlers/new-feature-handlers.ts
import { http, HttpResponse } from 'msw'

export const newFeatureHandlers = [
  http.get('/api/v1/new-feature', () => {
    return HttpResponse.json({
      code: 0,
      msg: '成功',
      data: { /* mock data */ }
    })
  })
]
```

### 2. 注册 Handler

```typescript
// src/mocks/handlers.ts
import { newFeatureHandlers } from './handlers/new-feature-handlers'

export const handlers = [
  ...genesisHandlers,
  ...newFeatureHandlers
]
```

## Mock 数据特性

### 创世对话
- 支持多阶段对话 (INITIAL_PROMPT, WORLDVIEW, CHARACTERS, PLOT_OUTLINE)
- 智能 AI 回复生成
- 模拟真实的响应延迟 (1.5s)
- 阶段状态持久化

### 响应格式
- 统一的 API 响应格式
- 正确的 HTTP 状态码
- 添加 `X-Mock-Response: true` 标识 mock 响应

## 调试

### 浏览器控制台
MSW 会在浏览器控制台显示拦截的请求：
```
[MSW] GET /api/v1/conversations/sessions/123/stage (200 OK)
```

### 网络面板
在浏览器开发者工具中可以看到正常的网络请求，响应头包含 `X-Mock-Response: true`。

## 与真实 API 切换

### 开发阶段
```bash
# 使用 mock
VITE_USE_MOCK_GENESIS=true pnpm run dev

# 使用真实 API
VITE_USE_MOCK_GENESIS=false pnpm run dev
```

### 渐进式替换
1. 当真实 API 准备好时，设置 `VITE_USE_MOCK_GENESIS=false`
2. MSW 会自动放行所有请求到真实后端
3. 无需修改任何业务代码

## 最佳实践

1. **保持简洁**: Mock 数据应该简单且专注于业务场景
2. **真实性**: 模拟真实的延迟和错误情况  
3. **维护性**: 定期清理不再需要的 mock handlers
4. **文档化**: 为复杂的 mock 逻辑添加注释

## 故障排除

### MSW 未启动
- 检查 `public/mockServiceWorker.js` 文件是否存在
- 确认环境变量设置正确
- 查看浏览器控制台是否有 MSW 启动信息

### Mock 不生效
- 确认请求 URL 匹配 handler 的路径
- 检查是否在开发模式下运行
- 验证环境变量 `VITE_USE_MOCK_GENESIS=true`