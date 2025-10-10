# SSE 详细实现规范

## 连接管理配置

- **并发限制**：每用户最多 2 条连接（超限返回 429，`Retry-After: 30s`）。
- **心跳与超时**：`ping` 间隔 15s，发送超时 30s；自动检测客户端断连并清理。
- **重连语义**：支持 `Last-Event-ID` 续传近期事件（支持请求头和查询参数）。
- **健康检查**：`/api/v1/events/health` 返回 Redis 状态与连接统计；异常时 503。
- **响应头**：`Cache-Control: no-cache`、`Connection: keep-alive`。
- **连接状态跟踪**：使用 `SSEConnectionState` 模型，包含连接ID、用户ID、标签页ID、时间戳等。
- **垃圾回收**：定期清理过期连接（阈值 300s），批量大小 10，间隔 60s。
- **鉴权**：`POST /api/v1/auth/sse-token` 获取短时效 `sse_token`（TTL由 `settings.auth.sse_token_expire_seconds` 配置），`GET /api/v1/events/stream?sse_token=...` 建立连接。
- **预检支持**：`GET /api/v1/events/stream?sse_token=...&preflight=true` 进行连接数限制检查（返回 204 或 429）。
- **同标签页抢占**：支持 `X-Tab-ID` 头部，同一标签页的新连接会抢占旧连接。
- **SLO 口径**：重连场景不计入"首 Token"延迟；新会话从事件生成时刻开始计时。

## SSE历史窗口与保留策略

### Redis Stream配置

```yaml
历史事件保留:
  stream_maxlen: 1000 # settings.database.redis_sse_stream_maxlen
  stream_ttl: 3600 # 1小时后自动清理（未实现）
  user_history_limit: 50 # 每用户保留最近50条（DEFAULT_HISTORY_LIMIT）

回放策略:
  初次连接:
    max_events: 50 # 仅回放最近50条（DEFAULT_HISTORY_LIMIT）
    time_window: 300 # 或最近5分钟内的事件

  重连场景:
    from_last_event_id: true # 从Last-Event-ID开始全量补发
    batch_size: 100 # 每批发送100条（MAX_HISTORY_BATCH_SIZE）
    max_backfill: 500 # 最多补发500条
    timeout_ms: 5000 # 补发超时时间
```

### 裁剪策略

- **Stream裁剪**：使用 `XADD ... MAXLEN ~` 近似裁剪，避免精确裁剪的性能开销
- **定期清理**：每60秒清理超过300秒的过期连接（CLEANUP_INTERVAL_SECONDS、STALE_CONNECTION_THRESHOLD_SECONDS）
- **用户隔离**：按 `user_id` 维度独立管理连接计数，支持按标签页隔离

## SSE Token管理与续签策略

### Token生命周期

```yaml
token_config:
  ttl: settings.auth.sse_token_expire_seconds  # 从配置读取TTL
  algorithm: settings.auth.jwt_algorithm       # 与主JWT相同算法
  secret_key: settings.auth.jwt_secret_key     # 与主JWT相同密钥
  refresh_window: 15                           # 过期前15秒可续签

签发流程:
  1. POST /api/v1/auth/sse-token
     - 验证JWT主令牌有效性（通过 get_current_user 依赖）
     - 生成JWT格式SSE令牌（token_type="sse"）
     - 返回: {sse_token: "jwt_token", expires_at: "ISO-8601"}

  2. GET /api/v1/events/stream?sse_token=xxx&last-event-id=xxx&tab_id=xxx
     - 使用JWT解码验证SSE令牌
     - 检查token_type="sse"和user_id
     - 支持可选的last-event-id和tab_id参数
     - 建立SSE连接
     - 开始推送事件流
```

### 客户端续签策略

**重要说明**：EventSource不支持自定义请求头，因此`last-event-id`只能通过：
1. **浏览器自动**：浏览器会自动在重连时发送`Last-Event-ID`请求头
2. **查询参数**：手动重连时可在URL中添加`last-event-id`参数

```javascript
// 前端续签示例时序
class SSETokenManager {
  constructor() {
    this.token = null
    this.expiresAt = null
    this.refreshTimer = null
  }

  async connect() {
    // 1. 获取初始token
    const tokenData = await fetch('/api/v1/auth/sse-token', {
      method: 'POST',
      headers: { Authorization: `Bearer ${mainJWT}` },
    }).then((r) => r.json())

    this.token = tokenData.sse_token
    this.expiresAt = new Date(tokenData.expires_at).getTime()

    // 2. 建立SSE连接
    const url = new URL('/api/v1/events/stream', window.location.origin)
    url.searchParams.set('sse_token', this.token)
    this.eventSource = new EventSource(url.toString())

    // 3. 设置自动续签（提前15秒）
    this.scheduleRefresh()
  }

  scheduleRefresh() {
    const refreshTime = this.expiresAt - Date.now() - 15000 // 提前15秒
    this.refreshTimer = setTimeout(() => this.refresh(), refreshTime)
  }

  async refresh() {
    try {
      // 4. 获取新token
      const newTokenData = await fetch('/api/v1/auth/sse-token', {
        method: 'POST',
        headers: { Authorization: `Bearer ${mainJWT}` },
      }).then((r) => r.json())

      // 5. 无缝切换连接
      const oldEventSource = this.eventSource
      this.token = newTokenData.sse_token
      this.expiresAt = new Date(newTokenData.expires_at).getTime()

      // 6. 创建新连接（带Last-Event-ID查询参数）
      const url = new URL('/api/v1/events/stream', window.location.origin)
      url.searchParams.set('sse_token', this.token)
      if (this.lastEventId) {
        url.searchParams.set('last-event-id', this.lastEventId)
      }
      this.eventSource = new EventSource(url.toString())

      // 7. 关闭旧连接
      setTimeout(() => oldEventSource.close(), 1000)

      // 7. 关闭旧连接
      setTimeout(() => oldEventSource.close(), 1000)

      // 8. 设置事件监听器来跟踪last-event-id
      this.eventSource.onmessage = (event) => {
        this.lastEventId = event.lastEventId
        // 处理事件...
      }

      // 9. 递归设置下次续签
      this.scheduleRefresh()
    } catch (error) {
      console.error('Token refresh failed:', error)
      // 触发重连逻辑
      this.reconnect()
    }
  }

  // 重连方法（利用浏览器自动重连机制）
  reconnect() {
    if (this.eventSource) {
      this.eventSource.close()
    }
    // 浏览器会自动重连并发送Last-Event-ID头
    setTimeout(() => this.connect(), 1000)
  }
}
```

### 服务端验证流程

```python
def verify_sse_token(sse_token: str) -> str:
    """验证SSE令牌并返回用户ID"""
    # 1. 输入验证
    if not sse_token or not sse_token.strip():
        raise HTTPException(401, "Token is required")

    try:
        # 2. JWT解码（使用与主JWT相同的密钥和算法）
        payload = jwt.decode(
            sse_token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm]
        )

        # 3. 验证token类型
        if payload.get("token_type") != "sse":
            raise HTTPException(401, "Invalid token type")

        # 4. 提取用户ID
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(401, "Invalid token payload")

        return str(user_id)

    except ExpiredSignatureError:
        raise HTTPException(401, "SSE token has expired")
    except JWTError:
        raise HTTPException(401, "Invalid token")
```

## SSE 事件格式

推送到SSE的事件遵循W3C标准格式，基于`SSEMessage`模型：

### 实际SSE消息格式

```
id: 1735689234567-0
event: Genesis.Session.Theme.Proposed
data: {"event_id":"uuid","event_type":"Genesis.Session.Theme.Proposed","session_id":"uuid","novel_id":"uuid","correlation_id":"uuid","timestamp":"2025-01-01T10:30:00Z","payload":{"stage":"Stage_1","content":{"theme":"...","summary":"..."}},"_scope":"user","_version":"1.0"}

```

### SSEMessage模型结构

```python
class SSEMessage(BaseModel):
    event: str              # 事件类型（如 "Genesis.Session.Theme.Proposed"）
    data: dict[str, Any]    # 事件数据（从领域事件转换）
    id: str | None          # 事件ID（Redis Stream ID，如 "1735689234567-0"）
    retry: int | None       # 重连延迟（毫秒）
    scope: EventScope       # 事件作用域（user/session/novel/global）
    version: str            # 事件版本（默认 "1.0"）
```

### 元信息添加

实际推送时，系统会自动在data中添加元信息：
- `_scope`: 事件作用域（如 "user"）
- `_version`: 事件版本（如 "1.0"）

## 可推送事件白名单

仅以下领域事件会推送到SSE（都来自 `genesis.session.events`）：

- `Genesis.Session.Started` - 会话开始
- `Genesis.Session.*.Proposed` - AI提议（需用户审核）
- `Genesis.Session.*.Confirmed` - 用户确认
- `Genesis.Session.*.Updated` - 内容更新
- `Genesis.Session.StageCompleted` - 阶段完成
- `Genesis.Session.Finished` - 创世完成
- `Genesis.Session.Failed` - 处理失败

注意：能力事件（`*.tasks/events`）不推送到SSE，仅用于内部协调。

## 实际配置参数

当前实现使用的配置值（来自 `SSEConfig`）：

```python
@dataclass
class SSEConfig:
    # 连接限制
    MAX_CONNECTIONS_PER_USER: int = 2
    CONNECTION_EXPIRY_SECONDS: int = 300
    RETRY_AFTER_SECONDS: int = 30

    # 事件流
    PING_INTERVAL_SECONDS: int = 15
    SEND_TIMEOUT_SECONDS: int = 30

    # 历史处理
    MAX_HISTORY_BATCH_SIZE: int = 100
    DEFAULT_HISTORY_LIMIT: int = 50

    # 清理配置
    STALE_CONNECTION_THRESHOLD_SECONDS: int = 300
    CLEANUP_INTERVAL_SECONDS: int = 60
    CLEANUP_BATCH_SIZE: int = 10
    ENABLE_PERIODIC_CLEANUP: bool = True
```

以上与当前 sse-starlette + Redis 实现一致。

## 迁移策略

- 使用 Alembic 版本化迁移脚本；顺序：新建表→数据迁移→切换读写→删除旧表
- 回滚脚本配套：每个升级脚本必须包含 downgrade 分支
- 热点索引基于查询模式建立（会话按更新时间、事件按 event_type/correlation）

## 连接状态管理

### SSEConnectionState 模型

```python
class SSEConnectionState(BaseModel):
    connection_id: str              # 唯一连接标识符
    user_id: str                   # 关联的用户ID
    tab_id: str | None             # 浏览器标签页标识符（用于同标签页抢占）
    connected_at: datetime         # 连接时间戳
    last_activity_at: datetime     # 最后活动时间戳（事件、心跳）
    last_event_id: str | None      # 最后处理的事件ID（用于重连）
    channel_subscriptions: list[str] # 订阅的频道列表

    # 运行时控制（不序列化）
    abort_event: asyncio.Event      # 中止事件
    counter_decremented: bool       # 计数器是否已递减
```

### 连接生命周期管理

1. **连接创建**：
   - 检查并发限制（Redis 计数器）
   - 同标签页抢占检查
   - 创建连接状态并注册
   - 启动事件流生成器

2. **连接维护**：
   - 自动心跳检测（15s 间隔）
   - 客户端断连检测
   - 活动时间戳更新
   - 垃圾回收标记

3. **连接清理**：
   - Redis 计数器递减
   - 内存状态移除
   - 资源释放
   - 异常情况恢复

### 监控与健康检查

`/api/v1/events/health` 端点返回简化的健康状态：

```json
{
  "status": "healthy",
  "redis_status": "healthy",
  "connection_statistics": {
    "active_connections": 15,
    "redis_connection_counters": 15
  },
  "service": "sse",
  "version": "1.0"
}
```

**状态值**：
- `healthy`: 正常运行
- `degraded`: 部分功能降级
- `unhealthy`: 服务不可用

**详细监控统计**：
复杂的监控数据可通过 `SSEConnectionManager.get_detailed_monitoring_stats()` 获取，包含清理统计、性能指标和健康告警。

## 缓存策略

```typescript
export interface CacheStrategy {
  generateKey(params: any): string
  getTTL(key: string): number
  invalidate(pattern: string): Promise<void>
  warmup(keys: string[]): Promise<void>
}

export class SessionCache implements CacheStrategy {
  private readonly DEFAULT_TTL = 60 * 60 // 1h
  generateKey(params: any) {
    return `dialogue:session:${params.sessionId}`
  }
  getTTL(_key: string) {
    return this.DEFAULT_TTL
  }
  async invalidate(pattern: string) {
    /* redis scan+del */
  }
  async warmup(keys: string[]) {
    /* batch mget */
  }
}
```