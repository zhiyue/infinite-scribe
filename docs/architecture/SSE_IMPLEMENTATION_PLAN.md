# 服务器推送事件 (SSE) 实现方案

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

## 推荐的 SSE 开源库

### 后端库

#### 1. sse-starlette (推荐)
- **GitHub**: https://github.com/sysid/sse-starlette
- **特点**: 专为 Starlette/FastAPI 设计，易于集成
- **优势**: 
  - 原生支持 FastAPI
  - 内置心跳机制
  - 支持事件类型和 ID
  - 异步生成器支持

```python
pip install sse-starlette
```

#### 2. aiohttp-sse
- **GitHub**: https://github.com/aio-libs/aiohttp-sse
- **特点**: 基于 aiohttp 的 SSE 实现
- **优势**: 成熟稳定，社区支持好
- **劣势**: 需要额外适配 FastAPI

#### 3. python-sse
- **GitHub**: https://github.com/mpetazzoni/python-sse
- **特点**: 轻量级 SSE 库
- **优势**: 简单易用，无依赖
- **劣势**: 功能相对基础

### 前端库

#### 1. EventSource Polyfill
- **GitHub**: https://github.com/EventSource/eventsource
- **特点**: 增强原生 EventSource，提供更好的错误处理和重连机制
- **安装**: `npm install eventsource`

#### 2. @microsoft/fetch-event-source
- **GitHub**: https://github.com/Azure/fetch-event-source
- **特点**: 基于 Fetch API 的 SSE 客户端，支持 POST 请求和自定义 headers
- **优势**: 
  - 支持自定义 headers（解决认证问题）
  - 支持 POST 请求
  - TypeScript 原生支持

```typescript
npm install @microsoft/fetch-event-source
```

### 选择理由

基于 InfiniteScribe 的技术栈，推荐：
- **后端**: `sse-starlette` - FastAPI 原生支持，功能完整
- **前端**: `@microsoft/fetch-event-source` - 支持自定义 headers，解决 JWT 认证问题

## SSE 与 Prefect 集成设计

### 集成架构

```text
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Prefect Flow   │────▶│ SSE Manager  │────▶│   Client    │
│   (Worker)      │     │  (FastAPI)   │     │  (React)    │
└────────┬────────┘     └──────┬───────┘     └─────────────┘
         │                     │
         │                     │
    ┌────▼────────┐      ┌────▼──────┐
    │ Prefect API │      │   Redis   │
    │  (Events)   │      │ (Pub/Sub) │
    └─────────────┘      └───────────┘
```

### Prefect 集成实现

#### 1. Prefect SSE 钩子

```python
# src/common/services/prefect_sse_hook.py
from prefect import flow, task, get_run_logger
from prefect.events import emit_event
from typing import Optional, Dict, Any
import asyncio

class PrefectSSEHook:
    """Prefect 工作流的 SSE 集成钩子"""
    
    def __init__(self, sse_manager):
        self.sse_manager = sse_manager
        
    async def emit_task_event(
        self,
        user_id: str,
        channel: str,
        task_name: str,
        event_type: str,
        data: Dict[str, Any]
    ):
        """发送任务事件到 SSE"""
        await self.sse_manager.publish(
            user_id=user_id,
            channel=channel,
            event=f"task.{event_type}",
            data={
                "task_name": task_name,
                "event_type": event_type,
                **data
            }
        )

# 创建装饰器
def sse_task(channel: str, user_id: Optional[str] = None):
    """SSE 任务装饰器"""
    def decorator(func):
        @task
        async def wrapper(*args, **kwargs):
            # 从上下文获取 user_id
            actual_user_id = user_id or kwargs.get("user_id")
            if not actual_user_id:
                raise ValueError("user_id is required for SSE tasks")
                
            logger = get_run_logger()
            
            # 发送任务开始事件
            await sse_hook.emit_task_event(
                user_id=actual_user_id,
                channel=channel,
                task_name=func.__name__,
                event_type="start",
                data={"args": str(args), "kwargs": str(kwargs)}
            )
            
            try:
                # 执行任务
                result = await func(*args, **kwargs)
                
                # 发送任务完成事件
                await sse_hook.emit_task_event(
                    user_id=actual_user_id,
                    channel=channel,
                    task_name=func.__name__,
                    event_type="complete",
                    data={"result": str(result)}
                )
                
                return result
                
            except Exception as e:
                # 发送任务失败事件
                await sse_hook.emit_task_event(
                    user_id=actual_user_id,
                    channel=channel,
                    task_name=func.__name__,
                    event_type="error",
                    data={"error": str(e)}
                )
                raise
                
        return wrapper
    return decorator
```

#### 2. Prefect Flow 与 SSE 集成示例

```python
# src/workflows/novel_generation_flow.py
from prefect import flow, task
from prefect.task_runners import SequentialTaskRunner
from src.common.services.prefect_sse_hook import sse_task, PrefectSSEHook

@sse_task(channel="novel-generation")
async def analyze_plot_task(plot_outline: str, user_id: str) -> Dict:
    """分析剧情大纲"""
    # 发送进度更新
    await sse_hook.emit_task_event(
        user_id=user_id,
        channel="novel-generation",
        task_name="analyze_plot",
        event_type="progress",
        data={"progress": 30, "message": "正在分析剧情结构..."}
    )
    
    # 实际的分析逻辑
    result = await plot_analyzer.analyze(plot_outline)
    
    await sse_hook.emit_task_event(
        user_id=user_id,
        channel="novel-generation",
        task_name="analyze_plot",
        event_type="progress",
        data={"progress": 100, "message": "剧情分析完成"}
    )
    
    return result

@sse_task(channel="novel-generation")
async def generate_chapter_task(chapter_config: Dict, user_id: str) -> str:
    """生成章节内容"""
    total_words = chapter_config.get("target_words", 3000)
    generated_words = 0
    content = ""
    
    # 流式生成并推送进度
    async for chunk in chapter_generator.generate_streaming(chapter_config):
        content += chunk
        generated_words += len(chunk.split())
        progress = min(100, int(generated_words / total_words * 100))
        
        await sse_hook.emit_task_event(
            user_id=user_id,
            channel="novel-generation",
            task_name="generate_chapter",
            event_type="progress",
            data={
                "progress": progress,
                "partial_content": chunk,
                "generated_words": generated_words
            }
        )
    
    return content

@flow(
    name="novel-generation-flow",
    task_runner=SequentialTaskRunner()
)
async def novel_generation_flow(
    novel_config: Dict,
    user_id: str
) -> Dict:
    """小说生成工作流"""
    # 发送工作流开始事件
    await sse_hook.emit_task_event(
        user_id=user_id,
        channel="novel-generation",
        task_name="novel_generation_flow",
        event_type="start",
        data={"config": novel_config}
    )
    
    # 分析剧情
    plot_analysis = await analyze_plot_task(
        novel_config["plot_outline"],
        user_id=user_id
    )
    
    # 生成各章节
    chapters = []
    for i, chapter_config in enumerate(plot_analysis["chapters"]):
        # 更新工作流进度
        flow_progress = int((i + 1) / len(plot_analysis["chapters"]) * 100)
        await sse_hook.emit_task_event(
            user_id=user_id,
            channel="novel-generation",
            task_name="novel_generation_flow",
            event_type="progress",
            data={
                "progress": flow_progress,
                "current_chapter": i + 1,
                "total_chapters": len(plot_analysis["chapters"])
            }
        )
        
        chapter_content = await generate_chapter_task(
            chapter_config,
            user_id=user_id
        )
        chapters.append(chapter_content)
    
    # 发送工作流完成事件
    await sse_hook.emit_task_event(
        user_id=user_id,
        channel="novel-generation",
        task_name="novel_generation_flow",
        event_type="complete",
        data={
            "chapters_count": len(chapters),
            "total_words": sum(len(ch.split()) for ch in chapters)
        }
    )
    
    return {
        "chapters": chapters,
        "metadata": plot_analysis
    }
```

#### 3. Prefect 事件监听器

```python
# src/common/services/prefect_event_listener.py
from prefect.events import Event
from prefect import get_client
from typing import AsyncGenerator
import asyncio

class PrefectEventListener:
    """监听 Prefect 事件并转发到 SSE"""
    
    def __init__(self, sse_manager):
        self.sse_manager = sse_manager
        self.running = False
        
    async def start(self):
        """启动事件监听器"""
        self.running = True
        asyncio.create_task(self._listen_events())
        
    async def stop(self):
        """停止事件监听器"""
        self.running = False
        
    async def _listen_events(self):
        """监听 Prefect 事件流"""
        async with get_client() as client:
            while self.running:
                try:
                    # 订阅所有流程运行事件
                    async for event in client.subscribe_to_events(
                        filter={
                            "event_type": ["prefect.flow-run.*", "prefect.task-run.*"]
                        }
                    ):
                        await self._process_event(event)
                except Exception as e:
                    logger.error(f"Error in Prefect event listener: {e}")
                    await asyncio.sleep(5)  # 重试延迟
                    
    async def _process_event(self, event: Event):
        """处理 Prefect 事件"""
        # 从事件标签中提取用户信息
        user_id = event.tags.get("user_id")
        channel = event.tags.get("sse_channel", "prefect-events")
        
        if user_id:
            # 转换事件类型
            event_type = event.event_type.replace("prefect.", "")
            
            # 发布到 SSE
            await self.sse_manager.publish(
                user_id=user_id,
                channel=channel,
                event=event_type,
                data={
                    "id": event.id,
                    "occurred": event.occurred.isoformat(),
                    "resource": event.resource.dict(),
                    "related": [r.dict() for r in event.related],
                    "payload": event.payload
                }
            )
```

### 前端集成示例

```typescript
// src/components/WorkflowMonitor.tsx
import React, { useState, useEffect } from 'react';
import { useSSE } from '@/hooks/useSSE';

interface TaskProgress {
  taskName: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  message?: string;
}

export function WorkflowMonitor({ workflowId }: { workflowId: string }) {
  const [tasks, setTasks] = useState<Record<string, TaskProgress>>({});
  const [overallProgress, setOverallProgress] = useState(0);
  
  const { connectionState } = useSSE(`workflow-${workflowId}`, {
    onMessage: (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // 处理不同类型的事件
        if (event.type === 'task.start') {
          setTasks(prev => ({
            ...prev,
            [data.task_name]: {
              taskName: data.task_name,
              status: 'running',
              progress: 0
            }
          }));
        } else if (event.type === 'task.progress') {
          setTasks(prev => ({
            ...prev,
            [data.task_name]: {
              ...prev[data.task_name],
              progress: data.progress,
              message: data.message
            }
          }));
        } else if (event.type === 'task.complete') {
          setTasks(prev => ({
            ...prev,
            [data.task_name]: {
              ...prev[data.task_name],
              status: 'completed',
              progress: 100
            }
          }));
        }
      } catch (error) {
        console.error('Failed to parse workflow event:', error);
      }
    }
  });
  
  return (
    <div className="workflow-monitor">
      <h3>工作流进度监控</h3>
      <div className="connection-status">
        连接状态: {connectionState}
      </div>
      
      <div className="overall-progress">
        <label>总体进度</label>
        <progress value={overallProgress} max={100} />
      </div>
      
      <div className="task-list">
        {Object.values(tasks).map(task => (
          <div key={task.taskName} className="task-progress">
            <h4>{task.taskName}</h4>
            <progress value={task.progress} max={100} />
            {task.message && <p>{task.message}</p>}
            <span className={`status ${task.status}`}>{task.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

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
                try:
                    data = json.loads(message["data"])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode JSON from SSE message on channel {channel}")
                    continue
                await self._broadcast_to_channel(channel, data)
                
    async def _broadcast_to_channel(self, channel: str, data: dict):
        """向特定频道的所有连接广播消息"""
        if queues := self.active_connections.get(channel):
            for queue in queues.copy():
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
from fastapi import APIRouter, Depends, Request, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sse_starlette.sse import EventSourceResponse
from src.api.deps import get_current_user
from src.common.services.sse_service import sse_manager
from src.models.user import User
from typing import Optional

router = APIRouter()
security = HTTPBearer()

@router.get("/stream/{channel}")
async def sse_stream(
    request: Request,
    channel: str,
    current_user: User = Depends(get_current_user)  # 支持 Bearer token
):
    """
    SSE 事件流端点
    
    支持通过 Authorization header 传递 Bearer token
    使用 @microsoft/fetch-event-source 可以发送自定义 headers
    """
    return EventSourceResponse(
        sse_manager.subscribe(
            user_id=str(current_user.id),
            channel=channel,
            request=request
        ),
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # 禁用 Nginx 缓冲
        }
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

#### 2.1 SSE Hook (使用 @microsoft/fetch-event-source)

```typescript
// src/hooks/useSSE.ts
import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from './useAuth';
import { 
  fetchEventSource,
  EventStreamContentType,
  FetchEventSourceInit 
} from '@microsoft/fetch-event-source';

interface SSEOptions {
  onMessage?: (event: MessageEvent) => void;
  onError?: (error: Error) => void;
  onOpen?: () => void;
  onProgress?: (data: any) => void;
  onComplete?: (data: any) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

type ConnectionState = 'connecting' | 'connected' | 'disconnected';

export function useSSE(channel: string, options: SSEOptions = {}) {
  const { token } = useAuth();
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [lastError, setLastError] = useState<Error | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  
  const {
    onMessage,
    onError,
    onOpen,
    onProgress,
    onComplete,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5
  } = options;
  
  const connect = useCallback(async () => {
    // 清理之前的连接
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    setConnectionState('connecting');
    abortControllerRef.current = new AbortController();
    
    const url = `${import.meta.env.VITE_API_URL}/api/v1/sse/stream/${channel}`;
    
    try {
      await fetchEventSource(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': EventStreamContentType,
        },
        signal: abortControllerRef.current.signal,
        
        onopen: async (response) => {
          if (response.ok && response.headers.get('content-type') === EventStreamContentType) {
            setConnectionState('connected');
            reconnectAttemptsRef.current = 0;
            setLastError(null);
            onOpen?.();
          } else {
            throw new Error(`Unexpected response: ${response.status}`);
          }
        },
        
        onmessage: (ev) => {
          try {
            // 处理不同类型的事件
            if (ev.event === 'progress') {
              const data = JSON.parse(ev.data);
              onProgress?.(data);
            } else if (ev.event === 'complete') {
              const data = JSON.parse(ev.data);
              onComplete?.(data);
            } else if (ev.event === 'error') {
              const data = JSON.parse(ev.data);
              onError?.(new Error(data.error || 'Unknown error'));
            } else {
              // 通用消息处理
              onMessage?.(ev);
            }
          } catch (error) {
            console.error('Failed to parse SSE event:', error);
            onError?.(error as Error);
          }
        },
        
        onerror: (error) => {
          setConnectionState('disconnected');
          setLastError(error);
          onError?.(error);
          
          // 指数退避重连
          if (reconnectAttemptsRef.current < maxReconnectAttempts) {
            reconnectAttemptsRef.current++;
            const delay = Math.min(
              reconnectInterval * Math.pow(2, reconnectAttemptsRef.current - 1),
              30000 // 最大延迟30秒
            );
            
            if (reconnectTimeoutRef.current) {
              clearTimeout(reconnectTimeoutRef.current);
            }
            
            reconnectTimeoutRef.current = window.setTimeout(() => {
              connect();
            }, delay);
            
            // 返回新的 Promise 以防止自动重连
            throw error;
          }
        },
        
        // 自定义获取函数以支持更多控制
        fetch: (input, init) => {
          return fetch(input, {
            ...init,
            credentials: 'include', // 支持 cookies
          });
        },
      });
    } catch (error) {
      // 错误已在 onerror 中处理
      console.error('SSE connection failed:', error);
    }
  }, [channel, token, onMessage, onError, onOpen, onProgress, onComplete, reconnectInterval, maxReconnectAttempts]);
  
  const disconnect = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setConnectionState('disconnected');
    reconnectAttemptsRef.current = 0;
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
    onProgress: (data) => {
      setGenerationProgress(data.progress);
      if (data.partial_content) {
        setGeneratedContent(prev => prev + data.partial_content);
      }
    },
    onComplete: (data) => {
      setGenerationProgress(100);
      setGeneratedContent(data.result.content);
    },
    onMessage: (event) => {
      // 处理通用消息事件
      try {
        const data = JSON.parse(event.data);
        if (data.error) {
          console.error('Generation error:', data.error);
        }
      } catch (error) {
        console.error('Failed to parse SSE message:', error);
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

```text
长时间任务 → 定期进度更新 → 完成通知
```

主要事件：
- `task.created`: 任务创建
- `task.progress`: 进度更新
- `task.completed`: 任务完成
- `task.failed`: 任务失败

### 5. Prefect 工作流实时监控 (新增)

```text
Prefect Flow 执行 → 实时事件推送 → 前端进度展示
```

主要事件：
- `flow-run.pending`: 工作流等待中
- `flow-run.running`: 工作流运行中
- `task-run.pending`: 任务等待中
- `task-run.running`: 任务执行中
- `task-run.completed`: 任务完成
- `task-run.failed`: 任务失败
- `flow-run.completed`: 工作流完成
- `flow-run.failed`: 工作流失败

特点：
- **细粒度进度追踪**: 在任务内部推送详细进度
- **实时状态同步**: Prefect 事件自动转发到 SSE
- **用户级隔离**: 基于 user_id 的事件过滤

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

### 第三阶段：Prefect 集成（1-2周）

1. 实现 Prefect SSE 钩子
2. 创建任务装饰器
3. 部署 Prefect 事件监听器
4. 测试工作流实时推送

### 第四阶段：应用场景实现（2-3周）

1. 实现小说生成实时反馈
2. 添加世界构建协作功能
3. 集成 AI 助手对话流
4. 完善任务进度追踪
5. 集成 Prefect 工作流监控

### 第五阶段：优化和监控（1周）

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

- **认证**：JWT Token 认证（通过查询参数传递）
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

### 5. 为什么选择 Redis 而不是 Kafka

#### 当前阶段选择 Redis 的原因：

**需求匹配度**：
- **短暂消息**：SSE 推送的是实时状态更新，不需要持久化
- **低延迟要求**：Redis 内存操作提供毫秒级延迟
- **简单扇出**：一对多的发布订阅模式完美匹配 SSE 需求
- **轻量运维**：避免 Kafka 的复杂部署和运维成本

**技术优势**：
| 特性 | Redis Pub/Sub | Kafka |
|-----|--------------|-------|
| 延迟 | 1-2ms | 10-100ms |
| 持久化 | 无（不需要） | 有（过度设计） |
| 运维复杂度 | 低 | 高（需要 ZooKeeper/KRaft） |
| 资源占用 | 低 | 高（磁盘、内存） |
| 适用规模 | 中小型（数万连接） | 大型（百万级） |

**务实考虑**：
- InfiniteScribe 已经使用 Redis 作为缓存层
- 当前用户规模不需要 Kafka 级别的吞吐量
- SSE 消息不需要重放功能
- 保持架构简单，避免过度工程化

**未来升级路径**：
如果未来需要：
- 消息持久化和重放
- 超大规模扇出（百万级）
- 复杂的消费者组管理
- 事件溯源能力

可以通过抽象发布接口，平滑迁移到 Kafka 或 Redis Streams。

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

## 部署配置建议

### Nginx 配置

```nginx
# 针对 SSE 的 Nginx 配置优化
location /api/v1/sse/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    
    # SSE 必需的头部
    proxy_set_header Connection '';
    proxy_set_header Cache-Control 'no-cache';
    proxy_set_header X-Accel-Buffering 'no';
    
    # 禁用缓冲
    proxy_buffering off;
    proxy_cache off;
    
    # 超时设置
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
    
    # 保持连接
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Docker Compose 配置

```yaml
# docker-compose.yml 添加
services:
  api-gateway:
    environment:
      # SSE 相关配置
      - SSE_HEARTBEAT_INTERVAL=30
      - SSE_MAX_CONNECTIONS_PER_USER=5
      - SSE_CONNECTION_TIMEOUT=86400
      
  redis:
    # 确保 Redis 配置支持 Pub/Sub
    command: redis-server --notify-keyspace-events AKE
```

### 环境变量配置

```bash
# .env 文件
# SSE 配置
SSE_HEARTBEAT_INTERVAL=30  # 心跳间隔（秒）
SSE_MAX_CONNECTIONS_PER_USER=5  # 每用户最大连接数
SSE_CONNECTION_TIMEOUT=86400  # 连接超时（秒）
SSE_REDIS_CHANNEL_PREFIX=sse  # Redis 频道前缀

# Prefect 集成配置
PREFECT_SSE_ENABLED=true
PREFECT_SSE_USER_TAG=user_id  # Prefect 事件中的用户标签
PREFECT_SSE_CHANNEL_TAG=sse_channel  # Prefect 事件中的频道标签
```

## 总结

本方案为 InfiniteScribe 提供了一个完整的 SSE 实时通信解决方案：

### 关键特性
1. **开源库选型**：
   - 后端使用 `sse-starlette`，与 FastAPI 无缝集成
   - 前端使用 `@microsoft/fetch-event-source`，支持自定义 headers 和更好的错误处理

2. **Prefect 深度集成**：
   - 自定义任务装饰器实现细粒度进度推送
   - 事件监听器自动转发 Prefect 事件到 SSE
   - 工作流级别的实时监控

3. **技术决策**：
   - 选择 Redis 而非 Kafka，保持架构简单高效
   - 支持水平扩展和高可用部署
   - 完善的错误处理和重连机制

### 实施价值
- **用户体验提升**：实时反馈让 AI 生成过程透明可见
- **开发效率**：统一的实时通信框架，简化开发
- **运维友好**：基于现有基础设施，降低部署复杂度

通过这个方案，InfiniteScribe 将具备强大的实时通信能力，为 AI 驱动的小说创作提供流畅的交互体验。