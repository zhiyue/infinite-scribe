# SSE 详细实现规范

## 连接管理配置

- **并发限制**：每用户最多 2 条连接（超限返回 429，`Retry-After` 按配置）。
- **心跳与超时**：`ping` 间隔 15s，发送超时 30s；自动检测客户端断连并清理。
- **重连语义**：支持 `Last-Event-ID` 续传近期事件（Redis 历史 + 实时聚合队列）。
- **健康检查**：`/api/v1/events/health` 返回 Redis 状态与连接统计；异常时 503。
- **响应头**：`Cache-Control: no-cache`、`Connection: keep-alive`。
- **鉴权**：`POST /api/v1/auth/sse-token` 获取短时效 `sse_token`（**默认 TTL=60秒**），`GET /api/v1/events/stream?sse_token=...` 建立连接。
- **SLO 口径**：重连场景不计入"首 Token"延迟；新会话从事件生成时刻开始计时。

## SSE历史窗口与保留策略

### Redis Stream配置

```yaml
历史事件保留:
  stream_maxlen: 1000 # XADD maxlen ≈ 1000（默认值）
  stream_ttl: 3600 # 1小时后自动清理
  user_history_limit: 100 # 每用户保留最近100条

回放策略:
  初次连接:
    max_events: 20 # 仅回放最近20条
    time_window: 300 # 或最近5分钟内的事件

  重连场景:
    from_last_event_id: true # 从Last-Event-ID开始全量补发
    batch_size: 50 # 每批发送50条
    max_backfill: 500 # 最多补发500条
    timeout_ms: 5000 # 补发超时时间
```

### 裁剪策略

- **Stream裁剪**：使用 `XADD ... MAXLEN ~` 近似裁剪，避免精确裁剪的性能开销
- **定期清理**：每小时清理超过TTL的历史记录
- **用户隔离**：按 `user_id:session_id` 维度独立管理历史

## SSE Token管理与续签策略

### Token生命周期

```yaml
token_config:
  default_ttl: 60           # 默认60秒有效期
  max_ttl: 300             # 最长5分钟（用于长连接）
  refresh_window: 15       # 过期前15秒可续签

签发流程:
  1. POST /api/v1/auth/sse-token
     - 验证JWT主令牌有效性
     - 生成短时效SSE令牌
     - 返回: {token, expires_in: 60}

  2. GET /api/v1/events/stream?sse_token=xxx
     - 验证SSE令牌
     - 建立SSE连接
     - 开始推送事件流
```

### 客户端续签策略

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

    this.token = tokenData.token
    this.expiresAt = Date.now() + tokenData.expires_in * 1000

    // 2. 建立SSE连接
    this.eventSource = new EventSource(
      `/api/v1/events/stream?sse_token=${this.token}`,
    )

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
      this.token = newTokenData.token
      this.expiresAt = Date.now() + newTokenData.expires_in * 1000

      // 6. 创建新连接（带Last-Event-ID）
      this.eventSource = new EventSource(
        `/api/v1/events/stream?sse_token=${this.token}`,
        { headers: { 'Last-Event-ID': this.lastEventId } },
      )

      // 7. 关闭旧连接
      setTimeout(() => oldEventSource.close(), 1000)

      // 8. 递归设置下次续签
      this.scheduleRefresh()
    } catch (error) {
      console.error('Token refresh failed:', error)
      // 触发重连逻辑
      this.reconnect()
    }
  }
}
```

### 服务端验证流程

```python
async def validate_sse_token(token: str) -> dict:
    """验证SSE令牌"""
    # 1. 从Redis获取token信息
    token_data = await redis.get(f"sse_token:{token}")
    if not token_data:
        raise HTTPException(401, "Invalid or expired SSE token")

    # 2. 检查过期时间
    if datetime.now() > token_data["expires_at"]:
        await redis.delete(f"sse_token:{token}")
        raise HTTPException(401, "SSE token expired")

    # 3. 可选：检查主JWT是否仍有效
    if not await is_main_jwt_valid(token_data["user_id"]):
        raise HTTPException(401, "Main session expired")

    return token_data
```

## SSE 事件格式

推送到SSE的事件（仅领域Facts）：

```json
{
  "id": "event-123", // Last-Event-ID
  "event": "Genesis.Session.Theme.Proposed", // 事件类型（点式命名）
  "data": {
    "event_id": "uuid", // 事件唯一ID
    "event_type": "Genesis.Session.Theme.Proposed",
    "session_id": "uuid", // 会话ID
    "novel_id": "uuid", // 小说ID
    "correlation_id": "uuid", // 关联ID（跟踪整个流程）
    "trace_id": "uuid", // 追踪ID（分布式追踪）
    "timestamp": "ISO-8601", // 事件时间戳
    "payload": {
      // 业务数据（最小集）
      "stage": "Stage_1",
      "content": {
        // 仅必要的展示数据
        "theme": "...",
        "summary": "..."
      }
    }
  }
}
```

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

以上与当前 sse-starlette + Redis 实现一致。

## 迁移策略

- 使用 Alembic 版本化迁移脚本；顺序：新建表→数据迁移→切换读写→删除旧表
- 回滚脚本配套：每个升级脚本必须包含 downgrade 分支
- 热点索引基于查询模式建立（会话按更新时间、事件按 event_type/correlation）

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