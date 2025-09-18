# SSE (Server-Sent Events) 集成

InfiniteScribe 前端的 SSE 实时事件集成，用于接收后端推送的实时事件通知。

## 核心组件

### 1. SSE 服务 (`sseService.ts`)

负责管理 EventSource 连接的底层服务类（通过Context管理，不使用全局单例）：

```typescript
import { SSEService } from '@/services/sseService'

// SSE服务由SSEContext管理，在组件中通过useSSE hook使用
// 不要直接创建SSEService实例

// 在组件中使用：
import { useSSE } from '@/contexts'

function MyComponent() {
  const { connect, disconnect, addMessageListener } = useSSE()

  // 连接到 SSE 端点
  connect()

  // 监听特定事件
  const handler = (event) => {
    console.log('小说创建:', event.data)
  }
  addMessageListener(handler)

  // 清理
  return () => {
    removeMessageListener(handler)
  }
}
```

### 2. React Hooks (`useSSE.ts`)

提供 React 组件友好的 SSE 集成：

#### 基础连接管理

```typescript
import { useSSEConnection } from '@/hooks/useSSE'

function MyComponent() {
  const { isConnected, connect, disconnect, error } = useSSEConnection({
    endpoint: '/events',
    autoConnect: true
  })
  
  return (
    <div>
      <p>连接状态: {isConnected ? '已连接' : '未连接'}</p>
      {error && <p>错误: {error.message}</p>}
    </div>
  )
}
```

#### 事件监听

```typescript
import { useDomainEvent } from '@/hooks/useSSE'

function NovelUpdates() {
  useDomainEvent('novel.created', (event) => {
    toast.success(`新小说创建: ${event.payload.title}`)
  })
  
  return <div>监听小说事件中...</div>
}
```

#### 特定小说事件监听

```typescript
import { useNovelEvents } from '@/hooks/useSSE'

function NovelProgress({ novelId }: { novelId: string }) {
  useNovelEvents(novelId, (event) => {
    switch (event.event_type) {
      case 'chapter.updated':
        console.log('章节更新:', event.payload.chapter_number)
        break
      case 'workflow.completed':
        console.log('工作流完成:', event.payload.status)
        break
    }
  })
  
  return <div>监听小说 {novelId} 的事件中...</div>
}
```

#### Genesis 进度监控

```typescript
import { useGenesisEvents } from '@/hooks/useSSE'

function GenesisProgress({ sessionId }: { sessionId: string }) {
  const [progress, setProgress] = useState(0)
  
  useGenesisEvents(sessionId, (event) => {
    if (event.event_type === 'genesis.progress') {
      setProgress(event.payload.progress || 0)
    }
  })
  
  return <ProgressBar value={progress} />
}
```

#### Agent 活动监控

```typescript
import { useAgentActivity } from '@/hooks/useSSE'

function AgentMonitor() {
  useAgentActivity(
    { agentType: 'story-generator' },
    (event) => {
      console.log('Story Generator 活动:', event.payload.activity_type)
    }
  )
  
  return <div>监听 Agent 活动中...</div>
}
```

#### 事件历史记录

```typescript
import { useEventHistory } from '@/hooks/useSSE'

function EventLog() {
  const { events, clearHistory, count } = useEventHistory(
    ['novel.created', 'chapter.updated'], 
    100 // 最多保存100条
  )
  
  return (
    <div>
      <p>共 {count} 条事件</p>
      <button onClick={clearHistory}>清除历史</button>
      {events.map((event, i) => (
        <div key={i}>{event.type}: {JSON.stringify(event.data)}</div>
      ))}
    </div>
  )
}
```

## 可用事件类型

### 小说相关事件

- `novel.created` - 小说创建
- `chapter.updated` - 章节更新

### 工作流事件

- `workflow.started` - 工作流开始
- `workflow.completed` - 工作流完成

### Agent 事件

- `agent.activity` - Agent 活动状态

### Genesis 事件

- `genesis.progress` - 创世流程进度

## 最佳实践

### 1. 在应用根组件初始化连接

```typescript
// App.tsx
function App() {
  const { connect } = useSSEConnection({ autoConnect: true })
  
  useEffect(() => {
    // 应用启动时自动连接
    connect()
  }, [])
  
  return <AppRoutes />
}
```

### 2. 组件级别的事件监听

```typescript
function NovelEditor({ novelId }: { novelId: string }) {
  const [chapters, setChapters] = useState([])
  
  // 只监听当前小说的事件
  useNovelEvents(novelId, (event) => {
    if (event.event_type === 'chapter.updated') {
      // 更新章节列表
      refetchChapters()
    }
  })
  
  return <Editor />
}
```

### 3. 错误处理和重连

```typescript
function SSEStatus() {
  const { connectionState, error, reconnect } = useSSEConnection()
  
  if (error) {
    return (
      <div className="error">
        <p>连接错误: {error.message}</p>
        <button onClick={reconnect}>重新连接</button>
      </div>
    )
  }
  
  return <StatusIndicator state={connectionState} />
}
```

### 4. 性能优化

```typescript
// 使用依赖数组控制重新订阅
useDomainEvent('novel.created', handleNovelCreated, [userId])

// 使用过滤器减少不必要的处理
useAgentActivity(
  { novelId, agentType: 'editor' }, // 只监听特定 Agent
  handleAgentActivity
)
```

## 故障排查

### 连接问题

1. 检查 API_BASE_URL 配置
2. 确认后端 SSE 端点可用
3. 检查认证 token 是否有效

### 事件未收到

1. 确认事件类型拼写正确
2. 检查事件过滤条件
3. 查看浏览器 DevTools 的 Network 标签页

### 性能问题

1. 限制事件历史记录数量
2. 使用事件过滤器减少处理量
3. 避免在事件处理器中进行重复的 API 调用

## 类型安全

所有 SSE 相关的类型定义位于 `@/types/events`：

- `SSEEvent<T>` - 基础 SSE 事件接口
- `DomainEvent` - 领域事件联合类型
- `EventType` - 事件类型枚举
- `SSEConnectionConfig` - 连接配置接口