# Conversation API 前端集成指南

## 概述

本模块提供了完整的对话管理API前端集成，包括：
- TypeScript 类型定义
- API 服务层封装
- React Hooks (基于 TanStack Query)
- 示例组件

## 文件结构

```
src/
├── types/api/
│   └── conversations.ts      # 对话相关的类型定义
├── services/
│   └── conversationsService.ts  # API 服务层实现
├── hooks/
│   └── useConversations.ts   # React Hooks
└── components/conversations/
    └── ConversationExample.tsx  # 使用示例
```

## 快速开始

### 1. 创建会话

```typescript
import { useCreateSession } from '@/hooks/useConversations'

function MyComponent() {
  const createSession = useCreateSession({
    onSuccess: (session) => {
      console.log('会话创建成功:', session.id)
    }
  })

  const handleCreate = () => {
    createSession.mutate({
      scope_type: 'GENESIS',
      scope_id: 'novel-123',
      stage: 'initial'
    })
  }

  return (
    <button onClick={handleCreate}>
      创建会话
    </button>
  )
}
```

### 2. 发送消息

```typescript
import { useSendMessage } from '@/hooks/useConversations'

function ChatComponent({ sessionId }) {
  const sendMessage = useSendMessage(sessionId)

  const handleSend = (text: string) => {
    sendMessage.mutate({
      input: {
        text,
        type: 'user_message'
      }
    })
  }

  return (
    // ... UI 组件
  )
}
```

### 3. 管理会话状态

```typescript
import { useSession, useUpdateSession } from '@/hooks/useConversations'

function SessionManager({ sessionId }) {
  const { data: session } = useSession(sessionId)
  const updateSession = useUpdateSession(sessionId)

  const pauseSession = () => {
    updateSession.mutate({
      status: 'PAUSED',
      headers: {
        'If-Match': session?.version.toString()
      }
    })
  }

  return (
    // ... UI 组件
  )
}
```

## 主要功能

### 会话管理 (Sessions)

- **创建会话**: `useCreateSession()`
- **获取会话**: `useSession(sessionId)`
- **更新会话**: `useUpdateSession(sessionId)`
- **删除会话**: `useDeleteSession()`

### 轮次管理 (Rounds)

- **获取轮次列表**: `useRounds(sessionId, params)`
- **创建轮次**: `useCreateRound(sessionId)`
- **发送消息**: `useSendMessage(sessionId)` (便捷方法)

### 命令管理 (Commands)

- **提交命令**: `useSubmitCommand(sessionId)`
- **查询命令状态**: `useCommandStatus(sessionId, commandId)`
- **轮询命令状态**: `usePollCommandStatus(sessionId, commandId)`

### 阶段管理 (Stages)

- **获取当前阶段**: `useStage(sessionId)`
- **设置阶段**: `useSetStage(sessionId)`

### 内容管理 (Content)

- **获取聚合内容**: `useContent(sessionId)`
- **搜索内容**: `useSearchContent(sessionId)`
- **导出内容**: `useExportContent(sessionId)`

### 质量管理 (Quality)

- **获取质量评分**: `useQualityScore(sessionId)`
- **检查一致性**: `useCheckConsistency(sessionId)`

### 版本控制 (Versions)

- **获取版本列表**: `useVersions(sessionId)`
- **创建版本**: `useCreateVersion(sessionId)`
- **合并版本**: `useMergeVersions(sessionId)`

## 高级特性

### 1. 乐观并发控制

使用 `If-Match` 头进行版本检查：

```typescript
updateSession.mutate({
  status: 'COMPLETED',
  headers: {
    'If-Match': session.version.toString()
  }
})
```

### 2. 幂等性保证

使用幂等键确保请求不会重复执行：

```typescript
import { useIdempotencyKey } from '@/hooks/useConversations'

const idempotencyKey = useIdempotencyKey()

createSession.mutate({
  // ... 请求数据
  headers: {
    'Idempotency-Key': idempotencyKey
  }
})
```

### 3. 请求追踪

使用关联ID追踪请求链路：

```typescript
import { useCorrelationId } from '@/hooks/useConversations'

const correlationId = useCorrelationId()

sendMessage.mutate({
  // ... 请求数据
  headers: {
    'X-Correlation-Id': correlationId
  }
})
```

### 4. 异步命令处理

对于长时间运行的操作，使用命令模式：

```typescript
// 提交命令
const submitCommand = useSubmitCommand(sessionId)
const { mutate } = submitCommand

mutate({
  type: 'GENERATE_CONTENT',
  payload: { /* ... */ }
}, {
  onSuccess: (response) => {
    // 开始轮询状态
    pollStatus(response.command_id)
  }
})

// 轮询状态
const { data: status } = usePollCommandStatus(
  sessionId,
  commandId,
  {
    interval: 1000,
    onProgress: (status) => {
      console.log('进度:', status)
    }
  }
)
```

## 错误处理

所有 hooks 都提供标准的错误处理：

```typescript
const createSession = useCreateSession({
  onError: (error) => {
    if (error.message.includes('已存在')) {
      // 处理重复创建
    } else {
      // 通用错误处理
    }
  }
})
```

## 缓存管理

使用 TanStack Query 的缓存策略：

```typescript
// 手动使缓存失效
import { useQueryClient } from '@tanstack/react-query'

const queryClient = useQueryClient()

// 使特定会话缓存失效
queryClient.invalidateQueries(['conversations', 'sessions', sessionId])

// 使所有会话缓存失效
queryClient.invalidateQueries(['conversations', 'sessions'])
```

## 完整示例

查看 `src/components/conversations/ConversationExample.tsx` 获取完整的使用示例。

## 注意事项

1. **会话生命周期**: 会话状态遵循 ACTIVE → PROCESSING → COMPLETED/FAILED 流程
2. **轮次路径**: 支持层级结构 ("1", "2", "2.1", "2.1.1")
3. **版本控制**: 使用乐观锁避免并发冲突
4. **异步操作**: 长时间运行的操作返回 202 状态码，需要轮询结果

## 开发建议

1. 使用 TypeScript 获得完整的类型支持
2. 合理使用缓存策略，避免频繁请求
3. 对关键操作添加幂等键
4. 使用关联ID便于问题排查
5. 处理好乐观锁冲突（412 错误）