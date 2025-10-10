---
id: ADR-006-batch-task-scheduling
title: 批量任务调度策略
status: Accepted
date: 2025-09-04
decision_makers: [platform-arch, devops-lead]
related_requirements: [FR-006, NFR-001, NFR-003]
related_stories: [STORY-006]
supersedes: []
superseded_by: null
tags: [architecture, scheduling, performance, scalability]
---

# 批量任务调度策略（与 docs/architecture 对齐）

## Status

Accepted

## Context

### Business Context

根据 PRD 的“批量细节生成”需求：

- 相关用户故事：STORY-006（AI 批量生成细节）
- 业务价值：批量生成地名、人名、物品等细节，大幅提高内容生成效率
- 业务约束：需在 5 秒内返回 10–50 个高质量项目，支持风格控制

### Technical Context（与 docs/architecture 对齐）

- 事件驱动微服务：FastAPI(API 网关) + Prefect(编排) +
  Kafka(事件总线)；业务事实持久化在 PostgreSQL。
- 事务性发件箱（Transactional Outbox）与 Message
  Relay：所有对 Kafka 的发布先写入 `event_outbox`，由 Relay 可靠投递。
- Prefect 暂停/恢复：通过回调句柄（`flow_resume_handles` +
  Redis 缓存），由 Callback Service 基于结果事件唤醒 Flow（无忙等轮询）。
- Agents：统一继承
  `BaseAgent`，采用“至少一次”语义（手动提交 offset、DLT、指数退避重试与错误分类钩子），通过 Registry 以 canonical
  id 注册；生产者默认 `acks=all`、`enable_idempotence=true`。
- Redis：仅用于“优先级与限流”的短暂调度结构及回调句柄缓存；领域事件以数据库为单一真相源。
- LLM：经由 LiteLLM；观测采用 Langfuse/Prometheus；前端通过 SSE 订阅进度与结果。

### Requirements Driving This Decision

- FR-006: 批量生成引擎
  - 单批 10–50 个项目
  - P95 首批可用结果 ≤ 2 秒；全量补齐 ≤ 5 秒
  - 支持去重（相似度阈值）
- NFR-001: 并发批量任务 ≥ 20 个
- NFR-003: 系统支持水平扩展

### Constraints

- 技术约束：LLM API 速率与并发配额（需速率限制与背压）。
- 一致性约束：跨服务通信遵循 Outbox + 事件溯源；消费者“至少一次”。
- 业务约束：生成质量与去重；需“快速首响”（First Response）。
- 成本约束：减少 LLM 调用次数，控制 token 消耗。

## Decision Drivers

- 吞吐量：支持大批量并发生成
- 响应时间：满足“快速首响 + 全量补齐”目标
- 资源利用：充分利用计算与配额
- 优先级控制：支持不同优先级与老化（aging）
- 容错性：失败隔离、DLT 与可观测性

## Considered Options

### Option 1: Prefect 编排 + Outbox→Kafka 分发 + Redis 优先级队列（推荐）

- 描述：使用 Prefect 编排批量流程，子任务入队时写入 PostgreSQL
  `event_outbox`，由 Message
  Relay 发布到 Kafka；Redis 提供“优先级 + 老化(aging)”的短暂队列；Callback
  Service 基于结果事件唤醒 Flow（Pause/Resume），无主动轮询。
- 与现有架构一致性：高（完全对齐 docs/architecture）
- 实现复杂度：中
- 优点：
  - 对齐 Outbox/回调唤醒；消除直连 Kafka 与忙等。
  - Prefect 可视化 + 暂停/恢复；结果由事件触发。
  - Kafka/Agents 路径具备“至少一次”与 DLT 保障。
  - 支持优先级、老化、限流与背压；易水平扩展。
- 缺点：
  - 需协调 DB/Relay/Redis/Kafka/Prefect/Callback 多组件。
  - 首次集成复杂度高于直连实现。
- 风险：组件间协调复杂

### Option 2: Celery 任务队列

- 描述：使用 Celery 作为分布式任务队列
- 与现有架构一致性：低（引入新组件，与 Prefect 重叠）
- 实现复杂度：低
- 优点：成熟方案，内置重试/错误处理
- 缺点：引入 RabbitMQ/Redis；与现有编排重复；运维复杂
- 风险：架构不一致

### Option 3: 简单线程池

- 描述：Python ThreadPoolExecutor
- 一致性：低（不符合分布式）
- 优点：实现简单、低延迟；缺点：无监控、不可扩展、单点

### Option 4: Kubernetes Job + CronJob

- 描述：K8s 原生任务调度
- 一致性：中；实现复杂度：高；风险：过度工程化（MVP 不宜）

## Decision

采用 **Option 1: Prefect 编排 + Outbox→Kafka 分发 + Redis 优先级队列**。

理由：

1. 最大化复用现有基础设施
2. 完全符合 Outbox、暂停/恢复 与 领域事件命名规范
3. 支持优先级、老化、限流与背压等调度策略
4. Prefect + Metrics + SSE 提供端到端可观察性
5. 可按“快速首响 + 增量补齐”策略渐进优化

## Consequences

### Positive

- 统一任务管理与观测（Prefect + Prometheus + SSE）
- 可靠任务分发（Outbox + Kafka）
- 灵活优先级与限流策略
- 水平扩展能力强

### Negative

- 系统组件增多，集成复杂度上升
- 需要维护 Redis 脚本与优先级公平性策略

### Risks

- 风险1：任务堆积
  - 缓解：限流与背压，动态调节并发，分批派发
- 风险2：优先级饿死
  - 缓解：分层队列 + 老化（aging）或加权轮询（WRR）
- 风险3：5 秒内全量完成不可达
  - 缓解：定义“首批可用(First
    Response) + 后台补齐”的交付语义，并以 SSE 实时推送进度

## Implementation Plan

### Integration with Existing Architecture

- 代码位置（建议）：
  - 调度与队列：`apps/backend/src/services/scheduling/`（`batch_scheduler.py`,
    `priority_queue.py`, `rate_limiter.py`）
  - Outbox 访问：`apps/backend/src/services/outbox/`（若无则内聚于 scheduling 模块）
  - 执行侧 Agent：复用 `worldbuilder` 与 `character_expert`（按 Registry/别名映射注册）
- 模块边界：
  - BatchScheduler（Prefect Flow + 调度 API，仅写入 Outbox，不直连 Kafka）
  - PriorityQueue（Redis ZSET + Aging）
  - RateLimiter（Redis + Lua Token Bucket）
  - 执行代理：由 `worldbuilder` 或 `character_expert` 消费请求并产出结果领域事件
- 关键契约：
  - 事件命名与 Envelope 遵循 docs/architecture（见下）
  - Outbox +
    Relay 保障可靠投递，消费者手动提交 offset；DLT 后缀与重试对齐全局配置

### Event Model & Naming（严格遵循事件命名规范）

- 请求事件：`Genesis.Session.DetailBatchGenerationRequested`
  - `aggregate_type=GenesisSession`，`aggregate_id=session_id`
  - `payload`: `{ session_id, task_id, type, count, style, priority }`
  - `correlation_id`: 来自 API 网关命令 ID（因果链路）
- 结果事件：`Genesis.Session.DetailBatchCreated`
  - `payload`: `{ session_id, task_id, items: [...] }`
  - 由 Agent 产出，经 Outbox 发布

### Implementation Design（伪代码：Prefect/Outbox/回调唤醒）

```python
# apps/backend/src/services/scheduling/batch_scheduler.py
from typing import Any, Dict, List
from datetime import timedelta
from prefect import flow, task, get_run_logger

@task(cache_expiration=timedelta(hours=1))
def calculate_batch_size(task_type: str, total_count: int) -> int:
    batch_sizes = {"character_name": 20, "location_name": 20, "item": 16, "skill": 10, "organization": 10}
    base = batch_sizes.get(task_type, 20)
    if total_count <= base: return total_count
    if total_count > base * 8: return min(base * 2, 50)
    return base

@task
def decompose_subtasks(task_type: str, count: int, style: Dict[str, Any]) -> List[Dict[str, Any]]:
    size = calculate_batch_size.fn(task_type, count)
    subs: List[Dict[str, Any]] = []
    for i in range(0, count, size):
        subs.append({"subtask_id": f"{task_type}:{i}:{min(size, count - i)}", "type": task_type, "count": min(size, count - i), "style": style, "batch_index": i // size})
    return subs

@task
def enqueue_priority(redis, subtasks: List[Dict[str, Any]], priority: int) -> List[str]:
    # ZSET 分数：优先级(大权重) + 时间(aging)
    # score = (10 - priority) * 1e12 + current_ms
    import time, json
    now_ms = int(time.time() * 1000)
    ids: List[str] = []
    for s in subtasks:
        tid = s["subtask_id"]; ids.append(tid)
        redis.hset(f"task:{tid}", mapping={"data": json.dumps(s), "status": "pending", "priority": priority})
        score = (10 - priority) * 10**12 + now_ms
        redis.zadd("q:genesis:detail_batch", {tid: score})
    return ids

@task
def dispatch_via_outbox(db, redis, rate_limiter, queue_name: str, correlation_id: str) -> int:
    # 原子 zpopmin 出队（生产实现用 Lua），令牌桶限流，写入 Outbox
    import json
    n = 0
    while True:
        item = redis.execute_command("ZPOPMIN", queue_name, 1)
        if not item: break
        task_id = item[0][0].decode("utf-8") if isinstance(item[0][0], bytes) else item[0][0]
        rate_limiter.acquire(1)  # Lua 令牌桶
        data = json.loads(redis.hget(f"task:{task_id}", "data"))
        db.insert_outbox(
            event_type="Genesis.Session.DetailBatchGenerationRequested",
            aggregate_type="GenesisSession",
            aggregate_id=data.get("session_id"),
            correlation_id=correlation_id,
            payload={"task_id": task_id, **data},
        )
        redis.hset(f"task:{task_id}", "status", "dispatched")
        n += 1
    return n

@task
def register_resume_handle(db, redis, correlation_id: str, expect: List[str]) -> str:
    handle = db.create_resume_handle(correlation_id=correlation_id, expect_types=expect)
    redis.setex(f"resume:{correlation_id}", 3600, handle)
    return handle

@flow(name="genesis_detail_batch_flow")
def schedule_detail_batch(db, redis, rate_limiter, session_id: str, task_type: str, count: int, style: Dict[str, Any], priority: int = 5) -> None:
    log = get_run_logger()
    subtasks = decompose_subtasks(task_type, count, style)
    ids = enqueue_priority(redis, subtasks, priority)
    expect = ["Genesis.Session.DetailBatchCreated"]
    correlation_id = db.current_command_id()  # API 网关命令 ID
    handle = register_resume_handle(db, redis, correlation_id, expect)
    dispatched = dispatch_via_outbox(db, redis, rate_limiter, "q:genesis:detail_batch", correlation_id)
    log.info(f"dispatched={dispatched}, handle={handle}, first_response_target=<=5s")
    # 暂停等待 Callback Service 基于结果事件唤醒
    prefect.runtime.pause(handle=handle)
```

### Post-processing（去重/校验）

```python
def post_process(items: List[dict], task_type: str) -> List[dict]:
    # 1) 精确去重（名称规范化）
    seen, uniq = set(), []
    for x in items:
        key = (x.get("name", "").strip().lower())
        if key and key not in seen:
            seen.add(key); uniq.append(x)
    # 2) 相似度去重（高阈值 0.92–0.97，视类型配置）
    return uniq
```

### Task Executor Implementation（复用既有 Agents）

- 路由策略（按 `task_type`）：
  - `character_name` → 由 `character_expert` 处理
  - `location_name`/`item`/`organization`/`skill` → 由 `worldbuilder` 处理
- Registry/别名：在 `agent_config.AGENT_ALIASES` 中确保 `"character_expert"→"characterexpert"`（已存在）与 `"world_builder"→"worldbuilder"` 映射；按需在各包 `__init__.py` 中注册。
- 事件：
  - 消费 `Genesis.Session.DetailBatchGenerationRequested`
  - 产出 `Genesis.Session.DetailBatchCreated`（保持 `correlation_id` 与 `retries`）

### Rate Limiting and Priority Management（Redis + Lua）

```lua
-- 原子令牌桶（Lua），多进程安全
-- KEYS[1] = bucket key; ARGV = rate, capacity, now_ms, need
local key = KEYS[1]
local rate = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])
local need = tonumber(ARGV[4])

local last_ts = tonumber(redis.call('HGET', key, 'ts') or 0)
local tokens = tonumber(redis.call('HGET', key, 'tokens') or capacity)
if last_ts == 0 then last_ts = now_ms end

local elapsed = math.max(0, now_ms - last_ts) / 1000.0
tokens = math.min(capacity, tokens + elapsed * rate)

if tokens >= need then
  tokens = tokens - need
  redis.call('HSET', key, 'tokens', tokens, 'ts', now_ms)
  redis.call('PEXPIRE', key, 60000)
  return 1
else
  redis.call('HSET', key, 'tokens', tokens, 'ts', now_ms)
  redis.call('PEXPIRE', key, 60000)
  return 0
end
```

备注：优先级 ZSET 采用
`score = (10-priority)*1e12 + current_ms`，保证优先级先于时间；时间提供老化，避免饥饿。

### Monitoring and Metrics

```python
class BatchSchedulerMetrics:
    def __init__(self, prometheus_client):
        self.prom = prometheus_client
        self.task_counter = Counter('batch_tasks_total', 'Total batch tasks', ['type', 'status'])
        self.task_duration = Histogram('batch_task_duration_seconds', 'Task execution duration', ['type'])
        self.queue_size = Gauge('batch_queue_size', 'Current queue size', ['priority'])
        self.first_response = Histogram('batch_first_response_seconds', 'First usable items latency', ['type'])

    async def record_task(self, task_type: str, status: str, duration: float):
        self.task_counter.labels(type=task_type, status=status).inc()
        self.task_duration.labels(type=task_type).observe(duration)
```

### Rollback Plan

- 触发条件：吞吐量不足或集成复杂度不可控
- 回滚步骤：
  1. 冻结新任务入队
  2. Drain 现有队列
  3. 降级为“单次大批量 LLM 调用 + 直接返回首批”的简化路径（减少子任务与分发）
  4. 逐步优化后再切换回来
- 数据恢复：Outbox + Kafka 保证消息不丢失；Redis 队列仅作临时结构（可丢弃）

## Validation

### Alignment with Existing Patterns

- 完全对齐 docs/architecture 的 Outbox、暂停/恢复、事件命名、Agent 语义
- 代码审查重点：
  - 任务分解与批大小策略
  - 优先级权重与老化计算
  - 限流与背压（Lua 令牌桶）
  - 错误处理/重试/DLT 与 Envelope（correlation/causation）

### Metrics

- 性能：
  - 首批可用结果（First Response）：P95 ≤ 2s（10–25 项）
  - 全量补齐：P95 ≤ 5s（10–50 项，视模型/配额）
  - 出队→Outbox 延迟：P95 < 100ms；队列延迟：P95 < 500ms
- 可靠性：
  - 任务成功率：> 99%；重试成功率：> 95%
  - DLT 率：< 0.1%（按天）

### Test Strategy

- 单元：批大小、优先级打分/Lua 令牌桶、去重阈值
- 集成：本地 Redpanda + Redis +
  PostgreSQL，端到端验证 Outbox→Kafka→Callback 恢复
- 性能：并发 20 批规模压测；SLO 验证（首响与全量）
- 压力：队列堆积、限流触发与老化效果
- 故障：Agent 故障/429/超时，DLT 与重试
- 超时：遵循仓库测试超时规范（单测 5–10s、集成 30–60s）

## References

- Prefect 文档: https://docs.prefect.io/
- Kafka 最佳实践: https://kafka.apache.org/documentation/#bestpractices
- Redis Sorted Sets: https://redis.io/docs/data-types/sorted-sets/
- Token Bucket 算法: https://en.wikipedia.org/wiki/Token_bucket
- docs/architecture: High Level Architecture, Components, Core Workflows, Event
  Naming Conventions, Error Handling Strategy, Tech Stack

## Changelog

- 2025-09-04: 初始草稿创建
- 2025-09-04: 修订以对齐 docs/architecture（Outbox、暂停/恢复、BaseAgent、事件命名、Redis 仅作调度）
