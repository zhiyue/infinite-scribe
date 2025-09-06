# EventBridge（Kafka→SSE 桥接）LLD

本文档定义 EventBridge 的低层设计（Low-Level Design）。EventBridge 负责消费领域总线上的事实事件（Facts），按用户维度路由到 SSE 通道，实现 UI 实时性更新。其失败不影响事务事实与状态一致性。

## 概览

- 角色定位：Kafka（领域总线）→ Redis（SSE）单向桥接
- 作用域：Genesis（可扩展到 Chapter/Review 等对话域）
- 一致性：不参与业务事务；SSE 仅提升实时性
- 语义：至少一次（at-least-once）消费；不保证 UI 端“恰好一次”展示

## 关联文档与代码

- HLD：`../design-hld.md`（事件驱动架构与“仅影响 UI 实时性”的语义）
- 事件：`./events.md`（点式命名、Topic 架构、领域/能力命名空间）
- SSE：`./sse.md`（Redis Streams + Pub/Sub、Last-Event-ID 回放与限流）
- 需求：`../requirements.md`（FR-001/002/003/005、NFR-001/007）
- 代码复用：
  - Kafka 客户端：`apps/backend/src/agents/kafka_client.py`
  - Offset 批量提交：`apps/backend/src/agents/offset_manager.py`
  - Redis SSE：`apps/backend/src/services/sse/redis_client.py`
  - 域配置：`apps/backend/src/common/events/config.py`
  - Outbox→Kafka 参照：`apps/backend/src/services/outbox/relay.py`

## 名称与范围

- 文档名：EventBridge（Kafka→SSE 桥接）
- 代码建议：`DomainEventBridgeService` 或 `KafkaSseBridgeService`
- 目录建议：`apps/backend/src/services/eventbridge/`
- 文件建议：`bridge.py`（主循环）、`filter.py`（白名单/校验）、`metrics.py`（可选）

## 架构位置与数据流

1) API/Orchestrator 将领域事实写入 `genesis.session.events` 主题（Outbox→Kafka）
2) EventBridge 订阅领域总线，过滤“可向用户推送”的事实
3) EventBridge 依据 `user_id` 路由，调用 `RedisSSEService.publish_event`
4) 前端通过 `/events/stream`（SSE）接收实时与历史（Last-Event-ID）

## 输入/输出契约

### 输入（Kafka：领域总线）

- Topic：`genesis.session.events`（后续可扩展为 scope→topic 表）
- event_type：点式命名，必须为 `Genesis.Session.*`
- 必填字段（Envelope + Payload）：
  - `event_id`（UUID）
  - `event_type`（dot-notation）
  - `aggregate_id`（会话 ID，等价于 `session_id`）
  - `correlation_id`（全链路追踪）
  - `metadata.trace_id`（若有）
  - `payload.user_id`、`payload.session_id`、`payload.timestamp`
  - 推荐携带：`payload.novel_id`
- 分区与顺序：按 `session_id` 分区，确保同会话内事件有序

### 输出（Redis → SSE）

- `SSEMessage`：
  - `event`：沿用输入 `event_type`（点式）
  - `data`：最小展示集（见下）
  - `id`：由 Redis Streams 生成（支持 Last-Event-ID）
  - `scope`：`user`（按用户维度路由）
- 数据最小集（建议）：
  - `event_id`、`event_type`、`session_id`、`novel_id?`
  - `correlation_id`、`trace_id?`、`timestamp`
  - `payload`（仅 UI 必需字段；避免大对象）

## 过滤与路由规则

- 白名单（仅 Facts 推送）：
  - `Genesis.Session.Started`
  - `Genesis.Session.*.Proposed`
  - `Genesis.Session.*.Confirmed`
  - `Genesis.Session.*.Updated`
  - `Genesis.Session.StageCompleted`
  - `Genesis.Session.Finished`
  - `Genesis.Session.Failed`
- 非法/无关事件：丢弃并记录告警（非法命名、缺失必填字段、非 Genesis 命名空间）
- 路由维度：`user_id`（主），`session_id` 进入 `data`；必要时支持按 session 订阅的扩展

## 组件设计

- `DomainEventBridgeService`
  - 依赖：`KafkaClientManager`（consumer）、`OffsetManager`、`RedisSSEService`
  - 职责：消费→过滤→映射→发布→批量提交偏移→熔断/降级
- `EventFilter`
  - 校验：点式命名 + 白名单 + 必填字段
  - 失败：返回拒绝理由，日志埋点
- `CircuitBreaker`
  - 10s 窗口失败率阈值（默认 50%），状态：`closed`/`open`/`half_open`
  - open：暂停 Kafka 消费；half_open：每 30s 进行一次探测发布
- `Publisher`
  - 将 Envelope→`SSEMessage`（裁剪数据）并调用 `RedisSSEService.publish_event`

## 生命周期与容错

- 启动：初始化日志/配置→创建 Kafka consumer→创建 Redis Pub/Sub 客户端
- 主循环：poll→逐条处理→记录指标→偏移批量提交（阈值/时间）
- 正常停止：flush pending offsets→停止 consumer→关闭 Redis 客户端
- 降级策略（优先）：
  - Redis 推送失败：继续消费 Kafka，丢弃 SSE 推送；累计 `sse_dropped_total`；提交偏移
- 熔断策略：
  - 失败率>50%（10s 窗口）→ open：`consumer.pause(partitions)`
  - 每 30s half-open 探测；成功率恢复后 `consumer.resume(...)`

## 指标与日志

- 指标（Prometheus 语义）：
  - `eventbridge_events_consumed_total`
  - `eventbridge_events_published_total`
  - `eventbridge_sse_dropped_total`
  - `eventbridge_redis_publish_latency_ms`
  - `eventbridge_circuit_state{state="closed|open|half_open"}`
  - `eventbridge_redis_fail_rate`
- 日志键：`event_type`、`user_id`、`session_id`、`correlation_id`、`topic`、`partition`、`offset`、`circuit_state`

## 配置项（建议）

- 主题与消费组：
  - `EVENT_BRIDGE__DOMAIN_TOPIC=genesis.session.events`
  - `EVENT_BRIDGE__GROUP_ID_SUFFIX=event-bridge`
- 熔断：
  - `EVENT_BRIDGE__CB_WINDOW_SECONDS=10`
  - `EVENT_BRIDGE__CB_FAIL_RATE_THRESHOLD=0.5`
  - `EVENT_BRIDGE__CB_HALF_OPEN_INTERVAL_SECONDS=30`
- 提交策略（可复用 agent 默认）：
  - `agent_commit_batch_size`、`agent_commit_interval_ms`

## 运行与联调

- 依赖：`pnpm infra up`（Kafka/Redis）
- 启动（建议）：`pnpm backend run:event-bridge` 或 `make event-bridge`
- 造数：向 `genesis.session.events` 写入示例 Facts（可用 kcat/脚本）
- 前端：打开 SSE 流，观察实时事件与 Last-Event-ID 回放
- 故障演练：临时停掉 Redis→观察降级计数；长时间失败→观察熔断（pause/resume）

## 测试计划

- 单元测试：
  - 事件过滤/白名单/命名校验
  - Envelope→SSEMessage 映射与裁剪
  - 降级与失败率窗口统计
- 轻量集成（无外部依赖）：
  - 用 stub consumer/redis 替代真实依赖验证主循环与偏移提交
- 行为验证：
  - 顺序性（同 user/session 事件顺序一致）
  - 重连回放（Last-Event-ID）
  - 长连接稳定性（心跳/断连检测由 SSE 层负责，此处仅发出事件）

## 验收标准（DoD）

- 过滤/映射/降级/熔断 单元测试通过
- 指标/日志完整，能支持问题排查
- 本地端到端联调成功（Kafka→EventBridge→Redis→前端 SSE）
- 文档与 HLD/LLD 其他章节一致

## 风险与回滚

- 风险：事件缺少 user_id/session_id；外部系统异常导致日志噪音或过度重试
- 降低：严格校验并丢弃无效事件；使用熔断避免失控；所有失败不影响事实一致性
- 回滚：EventBridge 可独立下线；Outbox→Kafka→Orchestrator 链路不受影响

## 示例

### 输入 Envelope（Kafka）

```json
{
  "event_id": "uuid",
  "event_type": "Genesis.Session.Theme.Proposed",
  "aggregate_id": "session-uuid",
  "correlation_id": "corr-uuid",
  "metadata": { "trace_id": "trace-uuid" },
  "payload": {
    "user_id": "user-uuid",
    "session_id": "session-uuid",
    "novel_id": "novel-uuid",
    "timestamp": "2025-09-06T00:00:00Z",
    "content": { "theme": "…", "summary": "…" }
  }
}
```

### 输出（SSEMessage，经 Redis 发布）

```json
{
  "event": "Genesis.Session.Theme.Proposed",
  "data": {
    "event_id": "uuid",
    "event_type": "Genesis.Session.Theme.Proposed",
    "session_id": "session-uuid",
    "novel_id": "novel-uuid",
    "correlation_id": "corr-uuid",
    "trace_id": "trace-uuid",
    "timestamp": "2025-09-06T00:00:00Z",
    "payload": { "theme": "…", "summary": "…" }
  },
  "id": "1693989123456-0",
  "scope": "user",
  "version": "1.0"
}
```

