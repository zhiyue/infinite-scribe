# 事件桥接服务 (EventBridge Service)

实现 Kafka 领域事件到 SSE 通道的桥接服务，采用熔断器模式和优雅降级策略，确保高可用性和容错性。

## 🏗️ 架构概览

### 核心职责

- **事件消费**：从 Kafka 主题消费领域事件
- **事件过滤**：根据业务规则验证和过滤事件
- **熔断保护**：优雅处理 Redis 故障
- **事件发布**：转换并发布到 SSE 通道
- **健康监控**：全面的指标收集和健康状态管理

### 架构图

```mermaid
graph TB
    subgraph "输入层"
        A[Kafka 消费者]
        B[领域事件流]
    end
    
    subgraph "处理层"
        C[DomainEventBridgeService]
        D[EventFilter]
        E[CircuitBreaker]
        F[Publisher]
    end
    
    subgraph "输出层"
        G[Redis SSE]
        H[前端连接]
        I[实时更新]
    end
    
    subgraph "监控层"
        J[MetricsCollector]
        K[健康检查]
        L[日志记录]
    end
    
    A --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
    
    C --> J
    J --> K
    J --> L
```

## 📁 目录结构

```
eventbridge/
├── __init__.py           # 服务导出和注册
├── bridge.py             # 主桥接服务（主要变更）
├── circuit_breaker.py    # 熔断器实现
├── constants.py          # 常量定义
├── factory.py            # 服务工厂
├── filter.py             # 事件过滤器
├── main.py               # 主程序入口
├── metrics.py            # 指标收集器
└── publisher.py          # 事件发布器
```

## 🎯 核心组件

### DomainEventBridgeService

主桥接服务类，协调所有组件实现完整的事件处理流水线：

```mermaid
sequenceDiagram
    participant K as Kafka
    participant E as EventBridge
    participant F as Filter
    participant C as CircuitBreaker
    participant P as Publisher
    participant R as Redis
    participant M as Metrics
    
    K->>E: 接收领域事件
    E->>E: 提取和验证信封
    E->>F: 事件过滤
    F-->>E: 过滤结果
    
    alt 事件有效
        E->>C: 检查熔断器状态
        C-->>E: 熔断器状态
        
        alt 熔断器关闭
            E->>P: 发布事件
            P->>R: 转发到 SSE
            P-->>E: 发布结果
            E->>C: 记录成功
            E->>M: 记录指标
        else 熔断器开启
            E->>M: 记录丢弃事件
        end
    else 事件无效
        E->>M: 记录过滤事件
    end
    
    E-->>K: 提交偏移量
```

### 事件处理流程

```mermaid
flowchart TD
    A[Kafka 消息] --> B[提取信封]
    B --> C{信封格式正确}
    
    C -->|是| D[事件过滤]
    C -->|否| E[记录警告并跳过]
    
    D --> F{事件有效}
    F -->|是| G[检查熔断器]
    F -->|否| H[记录过滤指标]
    
    G --> I{熔断器状态}
    I -->|关闭| J[发布事件]
    I -->|开启| K[丢弃事件]
    
    J --> L[记录成功]
    L --> M[更新熔断器]
    M --> N[记录偏移量]
    
    K --> O[记录丢弃]
    H --> P[继续处理]
    E --> P
    N --> P
    O --> P
```

### CircuitBreaker 熔断器

实现熔断器模式，防止 Redis 故障导致的级联故障：

```mermaid
stateDiagram-v2
    [*] --> CLOSED: 初始状态
    CLOSED --> OPEN: 故障率超过阈值
    OPEN --> HALF_OPEN: 超时重试
    HALF_OPEN --> CLOSED: 重试成功
    HALF_OPEN --> OPEN: 重试失败
    
    CLOSED --> CLOSED: 成功请求
    CLOSED --> CLOSED: 失败但未达阈值
    
    note right of CLOSED
        正常处理请求
        统计故障率
    end
    
    note right of OPEN
        快速失败
        停止处理请求
    end
    
    note right of HALF_OPEN
        有限放行
        探测服务恢复
    end
```

## 🔧 核心功能

### 1. 事件信封处理

```mermaid
graph LR
    A[原始 Kafka 消息] --> B[提取 value]
    B --> C{验证字典格式}
    C -->|是| D[合并 headers]
    C -->|否| E[返回 None]
    
    D --> F[填充 payload]
    F --> G[设置 session_id]
    G --> H[设置 user_id]
    H --> I[设置 timestamp]
    I --> J[返回完整信封]
```

### 2. 事件过滤机制

```mermaid
graph TD
    A[事件信封] --> B[检查事件类型]
    B --> C{白名单匹配}
    C -->|匹配| D[验证必需字段]
    C -->|不匹配| E[过滤掉]
    
    D --> F{字段完整}
    F -->|完整| G[通过验证]
    F -->|缺失| E
    
    G --> H[返回有效事件]
    E --> I[记录过滤原因]
```

### 3. 发布器实现

```mermaid
classDiagram
    class Publisher {
        +publish(envelope) stream_id
        -transform_to_sse_format()
        -extract_routing_info()
    }
    
    class RedisSSEService {
        +publish(stream_id, message)
        +get_stream_key()
        +create_sse_message()
    }
    
    class SSEMessage {
        +event: str
        +data: dict
        +id: str
        +retry: int
    }
    
    Publisher --> RedisSSEService
    Publisher --> SSEMessage
```

### 4. 指标收集器

```mermaid
graph TD
    A[MetricsCollector] --> B[事件计数器]
    A --> C[熔断器状态]
    A --> D[发布延迟]
    A --> E[健康状态]
    
    B --> B1[消费事件数]
    B --> B2[发布事件数]
    B --> B3[丢弃事件数]
    B --> B4[过滤事件数]
    
    C --> C1[成功计数]
    C --> C2[失败计数]
    C --> C3[故障率]
    
    D --> D1[Redis 延迟]
    D --> D2[转换延迟]
    
    E --> E1[整体健康度]
    E --> E2[组件状态]
```

## 🚀 使用示例

### 基础事件处理

```python
# 初始化服务
bridge_service = DomainEventBridgeService(
    kafka_client_manager=kafka_manager,
    offset_manager=offset_manager,
    redis_sse_service=redis_service,
    event_filter=event_filter,
    circuit_breaker=circuit_breaker,
    publisher=publisher,
    metrics_collector=metrics_collector
)

# 设置消费者引用
bridge_service.set_consumer(kafka_consumer)

# 处理事件
result = await bridge_service.process_event(kafka_message)
if result:
    print("事件处理成功")
```

### 自定义事件过滤器

```python
class CustomEventFilter(EventFilter):
    def validate(self, envelope):
        # 实现自定义过滤逻辑
        event_type = envelope.get("event_type", "")
        
        # 只处理特定事件类型
        if not event_type.startswith("Custom."):
            return False, "非自定义事件类型"
            
        # 验证必需字段
        required_fields = ["user_id", "session_id", "payload"]
        for field in required_fields:
            if field not in envelope.get("payload", {}):
                return False, f"缺少必需字段: {field}"
                
        return True, "验证通过"
```

### 健康状态检查

```python
# 获取服务健康状态
health_status = bridge_service.get_health_status()

# 检查服务是否健康
if health_status["healthy"]:
    print("EventBridge 服务运行正常")
    print(f"处理事件数: {health_status['metrics']['events_consumed']}")
    print(f"熔断器状态: {health_status['circuit_breaker']['state']}")
else:
    print("EventBridge 服务存在问题")
    print(f"错误率: {health_status['circuit_breaker']['failure_rate']}")
```

## 📊 监控和调试

### 关键指标

```mermaid
graph TD
    A[监控指标] --> B[业务指标]
    A --> C[技术指标]
    A --> D[健康指标]
    
    B --> B1[事件处理量]
    B --> B2[事件过滤率]
    B --> B3[事件丢弃率]
    
    C --> C1[Kafka 消费延迟]
    C --> C2[Redis 发布延迟]
    C --> C3[熔断器状态]
    
    D --> D1[服务可用性]
    D --> D2[错误率]
    D --> D3[恢复时间]
```

### 日志记录策略

```mermaid
graph LR
    A[日志级别] --> B[DEBUG]
    A --> C[INFO]
    A --> D[WARNING]
    A --> E[ERROR]
    
    B --> B1[详细处理流程]
    B --> B2[事件内容]
    
    C --> C1[事件处理结果]
    C --> C2[服务状态变更]
    
    D --> D1[事件过滤]
    D --> D2[熔断器状态]
    
    E --> E1[处理失败]
    E --> E2[严重错误]
```

### 性能优化

```mermaid
graph TD
    A[优化策略] --> B[批量处理]
    A --> C[异步操作]
    A --> D[缓存机制]
    A --> E[连接池]
    
    B --> B1[批量提交偏移量]
    B --> B2[批量发布事件]
    
    C --> C1[异步日志记录]
    C --> C2[异步指标更新]
    
    D --> D1[事件验证缓存]
    D --> D2[熔断器状态缓存]
    
    E --> E1[Kafka 连接池]
    E --> E2[Redis 连接池]
```

## 🔍 关键变更点

### 1. 桥接服务增强 (bridge.py)

- **事件信封增强**：支持用户 ID 和时间戳的自动填充
- **熔断器集成**：与 Kafka 分区分配的动态集成
- **错误处理优化**：更细粒度的错误分类和处理
- **日志结构化**：采用结构化日志格式便于分析

### 2. 熔断器分区管理

- **动态分区注册**：根据 Kafka 分配自动注册分区
- **分区状态跟踪**：独立跟踪每个分区的状态
- **重平衡处理**：优雅处理分区重平衡

## 📝 最佳实践

### 1. 容错设计

```python
# 实现重试机制
async def process_with_retry(service, message, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await service.process_event(message)
        except Exception as e:
            if attempt == max_retries - 1:
                # 最后一次尝试失败，记录错误
                logger.error("处理失败", error=str(e))
                return False
            # 指数退避
            await asyncio.sleep(2 ** attempt)
```

### 2. 监控告警

```python
# 设置关键指标监控
def setup_monitoring(metrics_collector):
    # 熔断器状态告警
    if metrics_collector.circuit_breaker.failure_rate > 0.5:
        send_alert("熔断器故障率过高")
    
    # 事件丢弃率告警
    if metrics_collector.event_drop_rate > 0.1:
        send_alert("事件丢弃率过高")
    
    # 服务健康状态告警
    if not metrics_collector.is_healthy():
        send_alert("EventBridge 服务不健康")
```

### 3. 配置管理

```python
# 配置熔断器参数
circuit_breaker_config = {
    "failure_threshold": 5,        # 触发熔断的失败次数
    "recovery_timeout": 60,       # 熔断器重试间隔（秒）
    "half_open_max_attempts": 3, # 半开状态最大尝试次数
    "success_threshold": 2,      # 熔断器关闭的成功次数
}

# 配置事件过滤器
event_filter_config = {
    "allowed_event_types": [
        "Genesis.Session.*",
        "Character.Design.*",
        "Theme.Generated.*"
    ],
    "required_fields": ["session_id", "event_type"],
    "max_payload_size": 1024 * 1024  # 1MB
}
```

## 🔗 相关模块

- **Kafka 客户端**：`src.core.kafka.client` - Kafka 消费者管理
- **偏移量管理**：`src.agents.offset_manager` - 偏移量跟踪和提交
- **Redis SSE**：`src.services.sse.redis_client` - Redis SSE 服务
- **指标收集**：`src.services.eventbridge.metrics` - 指标收集和监控
- **日志记录**：`src.core.logging` - 结构化日志记录

## ⚠️ 注意事项

1. **优雅降级**：Redis 故障时继续处理 Kafka，但丢弃 SSE 事件
2. **幂等性**：确保事件处理的幂等性，避免重复处理
3. **资源管理**：合理管理 Kafka 和 Redis 连接资源
4. **监控告警**：设置关键指标监控和异常告警
5. **性能优化**：根据实际负载调整批量处理和并发参数

## 🔄 部署和运维

### 容器化部署

```yaml
# docker-compose.yml
services:
  eventbridge:
    image: infinite-scribe/eventbridge
    environment:
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - REDIS_URL=redis://redis:6379
      - CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
    depends_on:
      - kafka
      - redis
    healthcheck:
      test: ["CMD", "python", "-c", "from src.services.eventbridge.bridge import DomainEventBridgeService; print('OK')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 健康检查

```python
# 实现健康检查端点
@app.get("/health")
async def health_check():
    health_status = bridge_service.get_health_status()
    
    if health_status["healthy"]:
        return {"status": "healthy", **health_status}
    else:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", **health_status}
        )
```