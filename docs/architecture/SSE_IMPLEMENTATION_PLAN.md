# Server-Sent Events (SSE) 实现方案

## 概述

Server-Sent Events (SSE) 是一种服务器向客户端推送实时数据的技术，非常适合 InfiniteScribe 这样需要实时反馈的 AI 驱动小说创作平台。本文档提供了在 InfiniteScribe 平台中实现 SSE 的详细方案。

## 技术背景

### 为什么选择 SSE

1. **单向通信需求匹配**：InfiniteScribe 主要需要从服务器向客户端推送 AI 生成的内容，SSE 的单向通信模型完美符合
2. **原生浏览器支持**：无需额外的客户端库，通过标准的 EventSource API 即可使用
3. **自动重连**：EventSource 具有内置的自动重连机制，提高了系统的可靠性
4. **文本数据友好**：SSE 专为文本数据设计，适合传输 AI 生成的文本内容
5. **HTTP/2 兼容**：支持多路复用，性能优秀

### 与 WebSocket 的对比

| 特性 | SSE | WebSocket |
|-----|-----|-----------|
| 通信方向 | 单向（服务器→客户端） | 双向 |
| 协议 | HTTP/HTTPS | WS/WSS |
| 自动重连 | 内置 | 需要手动实现 |
| 浏览器支持 | 原生 EventSource | 原生 WebSocket |
| 负载均衡友好度 | 高 | 中 |
| 适用场景 | 实时推送、进度更新 | 实时聊天、游戏 |

## 架构设计

### 整体架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│ API Gateway │────▶│   Agent     │
│   (React)   │◀────│  (FastAPI)  │◀────│  Services   │
└─────────────┘     └─────────────┘     └─────────────┘
      │ SSE              │ SSE              │ Redis
      │                  │                  │ Pub/Sub
      │                  ▼                  │
      │           ┌─────────────┐          │
      └──────────▶│    Redis    │◀─────────┘
                  │  (Pub/Sub)  │
                  └─────────────┘
```

### 核心组件

1. **SSE Manager**: 管理客户端连接和事件流
2. **Event Publisher**: 发布事件到 Redis
3. **Event Subscriber**: 从 Redis 订阅事件并推送给客户端
4. **Connection Pool**: 管理活跃的 SSE 连接

## 实现方案

### 1. 后端实现 (FastAPI)

#### 1.1 SSE 基础设施

```python
# src/common/services/sse_service.py
from typing import AsyncGenerator, Dict, Set
import asyncio
import json
from datetime import datetime
from fastapi import Request
from sse_starlette.sse import EventSourceResponse
import logging

logger = logging.getLogger(__name__)

class SSEManager:
    """管理 SSE 连接和事件分发"""
    
    def __init__(self, redis_service):
        self.redis_service = redis_service
        self.active_connections: Dict[str, Set[asyncio.Queue]] = {}
        self.subscriber_task = None
        
    async def startup(self):
        """启动 SSE 管理器"""
        self.subscriber_task = asyncio.create_task(self._redis_subscriber())
        
    async def shutdown(self):
        """关闭 SSE 管理器"""
        if self.subscriber_task:
            self.subscriber_task.cancel()
            
    async def _redis_subscriber(self):
        """Redis 订阅者，监听所有 SSE 频道"""
        pubsub = self.redis_service.pubsub()
        await pubsub.psubscribe("sse:*")
        
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"].decode()
                data = json.loads(message["data"])
                await self._broadcast_to_channel(channel, data)
                
    async def _broadcast_to_channel(self, channel: str, data: dict):
        """向特定频道的所有连接广播消息"""
        if channel in self.active_connections:
            for queue in self.active_connections[channel]:
                await queue.put(data)
                
    async def subscribe(self, user_id: str, channel: str, request: Request) -> AsyncGenerator:
        """订阅特定频道的事件流"""
        queue = asyncio.Queue()
        channel_key = f"sse:{channel}:{user_id}"
        
        # 注册连接
        if channel_key not in self.active_connections:
            self.active_connections[channel_key] = set()
        self.active_connections[channel_key].add(queue)
        
        try:
            # 发送初始连接事件
            yield {
                "event": "connected",
                "data": json.dumps({
                    "timestamp": datetime.utcnow().isoformat(),
                    "channel": channel
                })
            }
            
            # 持续发送事件
            while True:
                # 检查客户端是否断开
                if await request.is_disconnected():
                    break
                    
                try:
                    # 等待新事件，超时发送心跳
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": data.get("event", "message"),
                        "data": json.dumps(data.get("data", {}))
                    }
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp": datetime.utcnow().isoformat()})
                    }
                    
        except asyncio.CancelledError:
            logger.info(f"SSE connection cancelled for {channel_key}")
        finally:
            # 清理连接
            self.active_connections[channel_key].discard(queue)
            if not self.active_connections[channel_key]:
                del self.active_connections[channel_key]
                
    async def publish(self, user_id: str, channel: str, event: str, data: dict):
        """发布事件到指定频道"""
        channel_key = f"sse:{channel}:{user_id}"
        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.redis_service.publish(channel_key, json.dumps(message))
```

#### 1.2 SSE 路由实现

```python
# src/api/routes/v1/sse.py
from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse
from src.api.deps import get_current_user
from src.common.services.sse_service import sse_manager
from src.models.user import User

router = APIRouter()

@router.get("/stream/{channel}")
async def sse_stream(
    request: Request,
    channel: str,
    current_user: User = Depends(get_current_user)
):
    """SSE 事件流端点"""
    return EventSourceResponse(
        sse_manager.subscribe(
            user_id=str(current_user.id),
            channel=channel,
            request=request
        )
    )
```

#### 1.3 Agent 集成

```python
# src/agents/base.py 扩展
class BaseAgent:
    """基础 Agent 类，支持 SSE"""
    
    async def process_with_streaming(
        self, 
        request: BaseRequest,
        user_id: str,
        channel: str
    ) -> BaseResponse:
        """支持流式输出的处理方法"""
        
        # 发送开始事件
        await sse_manager.publish(
            user_id=user_id,
            channel=channel,
            event="start",
            data={"request_id": request.id}
        )
        
        try:
            # 处理请求，定期发送进度
            async for progress in self._process_streaming(request):
                await sse_manager.publish(
                    user_id=user_id,
                    channel=channel,
                    event="progress",
                    data=progress
                )
                
            # 发送完成事件
            result = await self._finalize_response()
            await sse_manager.publish(
                user_id=user_id,
                channel=channel,
                event="complete",
                data={"result": result.dict()}
            )
            
            return result
            
        except Exception as e:
            # 发送错误事件
            await sse_manager.publish(
                user_id=user_id,
                channel=channel,
                event="error",
                data={"error": str(e)}
            )
            raise
```

### 2. 前端实现 (React)

#### 2.1 SSE Hook

```typescript
// src/hooks/useSSE.ts
import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from './useAuth';

interface SSEOptions {
  onMessage?: (event: MessageEvent) => void;
  onError?: (event: Event) => void;
  onOpen?: (event: Event) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export function useSSE(channel: string, options: SSEOptions = {}) {
  const { token } = useAuth();
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [lastError, setLastError] = useState<Error | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef(0);
  
  const {
    onMessage,
    onError,
    onOpen,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5
  } = options;
  
  const connect = useCallback(() => {
    if (eventSourceRef.current?.readyState === EventSource.OPEN) {
      return;
    }
    
    setConnectionState('connecting');
    
    const url = `${import.meta.env.VITE_API_URL}/api/v1/sse/stream/${channel}`;
    const eventSource = new EventSource(url, {
      withCredentials: true,
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    eventSource.onopen = (event) => {
      setConnectionState('connected');
      reconnectAttemptsRef.current = 0;
      setLastError(null);
      onOpen?.(event);
    };
    
    eventSource.onmessage = (event) => {
      onMessage?.(event);
    };
    
    eventSource.onerror = (event) => {
      setConnectionState('disconnected');
      setLastError(new Error('SSE connection error'));
      onError?.(event);
      
      // 自动重连逻辑
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current++;
        setTimeout(connect, reconnectInterval);
      }
    };
    
    // 监听特定事件
    eventSource.addEventListener('progress', (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      // 处理进度更新
    });
    
    eventSource.addEventListener('complete', (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      // 处理完成事件
    });
    
    eventSourceRef.current = eventSource;
  }, [channel, token, onMessage, onError, onOpen, reconnectInterval, maxReconnectAttempts]);
  
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setConnectionState('disconnected');
    }
  }, []);
  
  useEffect(() => {
    if (token && channel) {
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, [channel, token, connect, disconnect]);
  
  return {
    connectionState,
    lastError,
    reconnect: connect,
    disconnect
  };
}
```

#### 2.2 使用示例

```typescript
// src/components/NovelGenerator.tsx
import React, { useState } from 'react';
import { useSSE } from '@/hooks/useSSE';

export function NovelGenerator() {
  const [generationProgress, setGenerationProgress] = useState<number>(0);
  const [generatedContent, setGeneratedContent] = useState<string>('');
  
  const { connectionState } = useSSE('novel-generation', {
    onMessage: (event) => {
      const data = JSON.parse(event.data);
      
      switch (event.type) {
        case 'progress':
          setGenerationProgress(data.progress);
          if (data.partial_content) {
            setGeneratedContent(prev => prev + data.partial_content);
          }
          break;
        case 'complete':
          setGenerationProgress(100);
          setGeneratedContent(data.result.content);
          break;
        case 'error':
          console.error('Generation error:', data.error);
          break;
      }
    }
  });
  
  return (
    <div>
      <div>连接状态: {connectionState}</div>
      <div>生成进度: {generationProgress}%</div>
      <div>{generatedContent}</div>
    </div>
  );
}
```

## 应用场景

### 1. 小说生成实时反馈

```
用户触发生成 → Agent 处理 → 实时推送进度和部分内容 → 完成推送
```

主要事件：
- `generation.start`: 开始生成
- `generation.progress`: 生成进度（包含部分内容）
- `generation.complete`: 生成完成
- `generation.error`: 生成错误

### 2. 世界构建协作

```
多用户协作 → 实时同步更改 → 推送给所有参与者
```

主要事件：
- `world.update`: 世界元素更新
- `world.conflict`: 编辑冲突
- `world.sync`: 同步完成

### 3. AI 助手对话流

```
用户提问 → AI 思考 → 流式输出回答
```

主要事件：
- `assistant.thinking`: AI 思考中
- `assistant.response`: 流式回答
- `assistant.suggestion`: 建议推送

### 4. 任务进度追踪

```
长时间任务 → 定期进度更新 → 完成通知
```

主要事件：
- `task.created`: 任务创建
- `task.progress`: 进度更新
- `task.completed`: 任务完成
- `task.failed`: 任务失败

## 实施计划

### 第一阶段：基础设施（1-2周）

1. 实现 SSE Manager 服务
2. 集成 Redis Pub/Sub
3. 创建基础 SSE 路由
4. 实现前端 SSE Hook
5. 编写单元测试

### 第二阶段：Agent 集成（1-2周）

1. 扩展 BaseAgent 支持流式输出
2. 更新现有 Agent 支持 SSE
3. 实现进度追踪机制
4. 集成测试

### 第三阶段：应用场景实现（2-3周）

1. 实现小说生成实时反馈
2. 添加世界构建协作功能
3. 集成 AI 助手对话流
4. 完善任务进度追踪

### 第四阶段：优化和监控（1周）

1. 性能优化
2. 添加监控指标
3. 错误处理完善
4. 文档编写

## 技术考虑

### 1. 连接管理

- **连接限制**：每用户最多 5 个并发 SSE 连接
- **超时处理**：30秒无活动发送心跳
- **重连策略**：指数退避算法

### 2. 安全性

- **认证**：JWT Token 认证
- **授权**：基于用户权限的频道访问控制
- **速率限制**：防止滥用

### 3. 可扩展性

- **水平扩展**：通过 Redis Pub/Sub 支持多实例
- **负载均衡**：SSE 友好的会话亲和性
- **资源管理**：连接池和内存优化

### 4. 监控指标

- 活跃连接数
- 消息吞吐量
- 连接持续时间
- 错误率和重连率

## 测试策略

### 1. 单元测试

```python
# tests/unit/services/test_sse_service.py
async def test_sse_connection():
    """测试 SSE 连接建立"""
    pass

async def test_event_publishing():
    """测试事件发布"""
    pass

async def test_connection_cleanup():
    """测试连接清理"""
    pass
```

### 2. 集成测试

```python
# tests/integration/test_sse_flow.py
async def test_end_to_end_streaming():
    """测试端到端流式传输"""
    pass

async def test_multi_client_broadcast():
    """测试多客户端广播"""
    pass
```

### 3. 性能测试

- 并发连接数测试
- 消息吞吐量测试
- 内存使用测试
- 重连压力测试

## 总结

SSE 为 InfiniteScribe 提供了一个轻量级、可靠的实时通信方案，特别适合 AI 生成内容的流式传输场景。通过合理的架构设计和实现，可以为用户提供流畅的实时体验，同时保持系统的可扩展性和可维护性。