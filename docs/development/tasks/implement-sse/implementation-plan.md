# SSE 实现方案

## 技术方案

### 1. 后端架构设计

采用分层架构实现 SSE：
- **API 层**：FastAPI SSE 端点，处理客户端连接
- **管理层**：SSEManager 管理连接池和事件分发
- **事件层**：EventBus 统一事件发布接口
- **集成层**：Kafka/Redis 订阅器，接收外部事件

### 2. 前端架构设计

基于 React Context 和 Hooks 实现：
- **SSEContext**：管理 SSE 连接生命周期
- **useSSE Hook**：订阅特定事件类型
- **EventHandler**：处理不同类型的事件
- **自动重连机制**：处理连接中断

### 3. 事件流设计

事件格式遵循标准 SSE 规范：
```
event: task.progress
data: {"task_id": "123", "progress": 50, "message": "Processing..."}
id: 1234567890
retry: 5000
```

## 架构设计

### 系统架构图

```mermaid
graph TB
    subgraph "前端 Frontend"
        UI[React UI]
        ES[EventSource Client]
        CTX[SSE Context]
        HOOK[useSSE Hook]
    end
    
    subgraph "后端 Backend"
        API[FastAPI SSE Endpoint]
        MGR[SSE Manager]
        EB[Event Bus]
        
        subgraph "事件源 Event Sources"
            KAFKA[Kafka Consumer]
            REDIS[Redis Subscriber]
            DB[Database Triggers]
        end
    end
    
    subgraph "消息中间件"
        KF[Kafka Broker]
        RD[Redis Pub/Sub]
    end
    
    UI --> CTX
    CTX --> ES
    ES -.SSE Connection.-> API
    API --> MGR
    MGR --> EB
    
    KAFKA --> EB
    REDIS --> EB
    DB --> EB
    
    KF --> KAFKA
    RD --> REDIS
    
    style ES fill:#f9f,stroke:#333,stroke-width:2px
    style API fill:#f9f,stroke:#333,stroke-width:2px
    style MGR fill:#bbf,stroke:#333,stroke-width:2px
```

### SSE 连接流程图

```mermaid
flowchart LR
    Start[客户端启动] --> Connect[建立 SSE 连接]
    Connect --> Auth{认证检查}
    Auth -->|成功| Register[注册连接]
    Auth -->|失败| Error[返回错误]
    
    Register --> Subscribe[订阅事件]
    Subscribe --> Listen[监听事件流]
    
    Listen --> Event{接收事件}
    Event --> Process[处理事件]
    Process --> Update[更新 UI]
    Update --> Listen
    
    Listen --> Disconnect{连接断开?}
    Disconnect -->|是| Reconnect[自动重连]
    Disconnect -->|否| Listen
    Reconnect --> Connect
    
    Error --> End[结束]
```

### 事件处理时序图

```mermaid
sequenceDiagram
    participant Agent
    participant Kafka
    participant EventBus
    participant SSEManager
    participant Client
    
    Agent->>Kafka: 发布任务进度事件
    Kafka->>EventBus: 消费事件
    EventBus->>SSEManager: 分发事件
    SSEManager->>SSEManager: 查找订阅者
    SSEManager->>Client: 推送 SSE 事件
    Client->>Client: 更新 UI
    
    Note over Client: 如果连接断开
    Client->>SSEManager: 重新连接
    SSEManager->>Client: 恢复事件流
```

### 组件类图

```mermaid
classDiagram
    class SSEManager {
        -connections: Dict[str, SSEConnection]
        -event_bus: EventBus
        +register_connection(client_id, connection)
        +unregister_connection(client_id)
        +broadcast_event(event)
        +send_to_client(client_id, event)
    }
    
    class SSEConnection {
        -client_id: str
        -session_id: str
        -subscriptions: Set[str]
        -queue: asyncio.Queue
        +subscribe(event_type)
        +unsubscribe(event_type)
        +send_event(event)
        +close()
    }
    
    class EventBus {
        -subscribers: Dict[str, List[Callable]]
        +publish(event_type, data)
        +subscribe(event_type, handler)
        +unsubscribe(event_type, handler)
    }
    
    class SSEEvent {
        +event_type: str
        +data: Dict
        +id: str
        +retry: int
        +to_sse_format(): str
    }
    
    SSEManager "1" --> "*" SSEConnection
    SSEManager --> EventBus
    SSEConnection --> SSEEvent
    EventBus --> SSEEvent
```

## 实现细节

### 后端实现要点

1. **连接管理**
   - 使用 asyncio.Queue 管理每个客户端的事件队列
   - 实现心跳机制检测断开的连接
   - 限制每个用户的最大连接数

2. **事件过滤**
   - 基于 session_id 过滤事件
   - 支持事件类型订阅
   - 实现权限检查

3. **性能优化**
   - 使用连接池管理数据库连接
   - 批量处理事件减少网络开销
   - 实现事件去重机制

### 前端实现要点

1. **连接管理**
   - 使用 React Context 全局管理 SSE 连接
   - 实现指数退避重连策略
   - 处理页面切换时的连接保持

2. **事件处理**
   - 使用事件总线模式分发事件
   - 实现事件缓存避免丢失
   - 支持离线事件队列

3. **错误处理**
   - 捕获网络错误并自动重试
   - 提供降级到轮询的备选方案
   - 显示连接状态指示器

## 风险评估

### 技术风险

1. **连接数限制**
   - 风险：大量并发连接可能耗尽服务器资源
   - 对策：实现连接池限制和负载均衡

2. **网络不稳定**
   - 风险：频繁断线重连影响用户体验
   - 对策：实现智能重连和事件缓存

3. **浏览器兼容性**
   - 风险：老版本浏览器不支持 EventSource
   - 对策：提供 polyfill 或降级方案

### 安全风险

1. **未授权访问**
   - 风险：恶意用户订阅他人事件
   - 对策：实现基于 JWT 的认证和权限检查

2. **DDoS 攻击**
   - 风险：大量连接请求导致服务不可用
   - 对策：实现速率限制和连接数限制

## 测试计划

### 单元测试

1. **后端测试**
   - SSEManager 连接管理功能
   - EventBus 事件分发逻辑
   - 事件过滤和权限检查

2. **前端测试**
   - SSE Context 状态管理
   - 重连逻辑测试
   - 事件处理器测试

### 集成测试

1. **端到端测试**
   - 完整的事件流测试
   - 断线重连测试
   - 并发连接测试

2. **性能测试**
   - 1000+ 并发连接测试
   - 事件吞吐量测试
   - 内存泄漏检测

### 兼容性测试

1. **浏览器测试**
   - Chrome/Firefox/Safari 最新版
   - Edge 兼容性测试
   - 移动端浏览器测试

2. **网络环境测试**
   - 弱网环境测试
   - 代理服务器测试
   - 防火墙穿透测试