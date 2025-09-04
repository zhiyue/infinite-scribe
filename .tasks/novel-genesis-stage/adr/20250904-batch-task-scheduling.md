---
id: ADR-006-batch-task-scheduling
title: 批量任务调度策略
status: Proposed
date: 2025-09-04
decision_makers: [platform-arch, devops-lead]
related_requirements: [FR-006, NFR-001, NFR-003]
related_stories: [STORY-006]
supersedes: []
superseded_by: null
tags: [architecture, scheduling, performance, scalability]
---

# 批量任务调度策略

## Status
Proposed

## Context

### Business Context
根据PRD中的批量细节生成需求：
- 相关用户故事：STORY-006（AI批量生成细节）
- 业务价值：批量生成地名、人名、物品等细节，大幅提高内容生成效率
- 业务约束：需要在5秒内生成10-50个高质量项目，支持风格控制

### Technical Context
基于现有架构：
- 当前架构：
  - Prefect作为工作流编排器
  - Kafka作为事件总线
  - 多Agent微服务架构
- 现有技术栈：Python、FastAPI、Prefect、Kafka、Redis
- 现有约定：所有任务通过事件驱动，异步执行
- 集成点：需要与Agent服务、LLM调用、结果存储集成

### Requirements Driving This Decision
- FR-006: 批量生成引擎
  - 单批10-50个项目
  - 生成时间<5秒
  - 支持去重（相似度阈值）
- NFR-001: 并发批量任务≥20个
- NFR-003: 系统需要支持水平扩展

### Constraints
- 技术约束：LLM API有速率限制
- 业务约束：需要保证生成质量，避免重复
- 成本约束：需要优化API调用次数，控制成本

## Decision Drivers
- **吞吐量**：支持大批量并发生成
- **响应时间**：满足5秒内完成的要求
- **资源利用**：充分利用计算资源
- **优先级控制**：支持不同优先级的任务
- **容错性**：任务失败不影响其他任务

## Considered Options

### Option 1: Prefect编排 + Kafka分发 + 优先级队列（推荐）
- **描述**：使用Prefect编排批量任务流程，Kafka进行任务分发，Redis实现优先级队列
- **与现有架构的一致性**：高 - 充分利用现有组件
- **实现复杂度**：中
- **优点**：
  - 利用现有基础设施
  - Prefect提供可视化和监控
  - Kafka保证任务不丢失
  - 支持优先级和速率限制
  - 易于水平扩展
- **缺点**：
  - 需要协调多个组件
  - 延迟可能略高
- **风险**：组件间协调复杂

### Option 2: Celery任务队列
- **描述**：使用Celery作为分布式任务队列
- **与现有架构的一致性**：低 - 引入新组件
- **实现复杂度**：低
- **优点**：
  - 成熟的任务队列方案
  - 内置重试和错误处理
  - 支持多种调度策略
- **缺点**：
  - 与现有Prefect重复
  - 需要额外的消息队列（RabbitMQ）
  - 增加运维复杂度
- **风险**：架构不一致

### Option 3: 简单线程池
- **描述**：使用Python的ThreadPoolExecutor
- **与现有架构的一致性**：低 - 不符合分布式架构
- **实现复杂度**：低
- **优点**：
  - 实现简单
  - 无额外依赖
  - 低延迟
- **缺点**：
  - 不支持分布式
  - 缺少监控和管理
  - 单点故障
- **风险**：无法扩展，不适合生产

### Option 4: Kubernetes Job + CronJob
- **描述**：使用K8s原生的任务调度
- **与现有架构的一致性**：中
- **实现复杂度**：高
- **优点**：
  - 云原生方案
  - 自动扩缩容
  - 资源隔离
- **缺点**：
  - 需要K8s环境
  - 调度粒度较粗
  - MVP时间紧张
- **风险**：过度工程化

## Decision
建议采用 **Option 1: Prefect编排 + Kafka分发 + 优先级队列**

理由：
1. 最大化利用现有基础设施
2. 符合事件驱动架构
3. 支持复杂的调度策略
4. 易于监控和调试
5. 可以渐进式优化

## Consequences

### Positive
- 统一的任务管理平台
- 可视化的执行流程
- 可靠的任务分发
- 灵活的优先级控制
- 良好的可扩展性

### Negative
- 系统复杂度增加
- 需要维护多个组件
- 可能有轻微的延迟开销

### Risks
- **风险1：任务堆积**
  - 缓解：实施背压和限流机制
- **风险2：优先级饿死**
  - 缓解：使用公平调度算法

## Implementation Plan

### Integration with Existing Architecture
- **代码位置**：
  - 调度器：`apps/backend/src/core/scheduler/`
  - 任务定义：`apps/backend/src/tasks/batch/`
  - 队列管理：`apps/backend/src/infrastructure/queue/`
- **模块边界**：
  - BatchScheduler: 批量任务调度器
  - TaskQueue: 优先级队列实现
  - RateLimiter: 速率限制器
  - TaskExecutor: 任务执行器
- **依赖管理**：使用现有的Prefect、Kafka、Redis客户端

### Implementation Design
```python
# apps/backend/src/core/scheduler/batch_scheduler.py
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from typing import List, Dict, Any
import asyncio
from datetime import timedelta

class BatchTaskScheduler:
    """批量任务调度器"""
    
    def __init__(
        self,
        kafka_producer,
        redis_client,
        rate_limiter
    ):
        self.kafka = kafka_producer
        self.redis = redis_client
        self.rate_limiter = rate_limiter
        self.logger = get_run_logger()
    
    @flow(name="batch_generation_flow")
    async def schedule_batch_generation(
        self,
        task_type: str,  # 地名、人名、物品等
        count: int,
        style: Dict[str, Any],
        priority: int = 5  # 1-10，10最高
    ) -> List[Dict[str, Any]]:
        """批量生成任务的主流程"""
        
        # 1. 任务分解
        subtasks = await self.decompose_task(task_type, count, style)
        
        # 2. 优先级队列入队
        task_ids = await self.enqueue_tasks(subtasks, priority)
        
        # 3. 分发任务到Kafka
        await self.distribute_tasks(task_ids)
        
        # 4. 等待结果（带超时）
        results = await self.wait_for_results(task_ids, timeout=5)
        
        # 5. 去重和后处理
        final_results = await self.post_process(results, task_type)
        
        return final_results
    
    @task(cache_key_fn=task_input_hash, cache_expiration=timedelta(hours=1))
    async def decompose_task(
        self,
        task_type: str,
        count: int,
        style: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """任务分解策略"""
        
        # 批大小优化（平衡API调用和并发）
        optimal_batch_size = self._calculate_batch_size(task_type, count)
        
        subtasks = []
        for i in range(0, count, optimal_batch_size):
            batch_count = min(optimal_batch_size, count - i)
            subtask = {
                "id": f"{task_type}_{i}_{batch_count}",
                "type": task_type,
                "count": batch_count,
                "style": style,
                "batch_index": i // optimal_batch_size
            }
            subtasks.append(subtask)
        
        return subtasks
    
    def _calculate_batch_size(self, task_type: str, total_count: int) -> int:
        """计算最优批大小"""
        # 基于任务类型的经验值
        batch_sizes = {
            "character_name": 10,  # 人名一次生成10个
            "location_name": 15,    # 地名一次生成15个
            "item": 8,              # 物品一次生成8个
            "skill": 5,             # 技能复杂，一次5个
            "organization": 5       # 组织一次5个
        }
        
        base_size = batch_sizes.get(task_type, 10)
        
        # 根据总数调整
        if total_count < base_size:
            return total_count
        elif total_count > base_size * 10:
            return base_size * 2  # 大批量时增加批大小
        else:
            return base_size
    
    async def enqueue_tasks(
        self,
        subtasks: List[Dict[str, Any]],
        priority: int
    ) -> List[str]:
        """将任务加入优先级队列"""
        
        task_ids = []
        
        for subtask in subtasks:
            task_id = subtask["id"]
            
            # 存储任务详情
            await self.redis.hset(
                f"task:{task_id}",
                mapping={
                    "data": json.dumps(subtask),
                    "status": "pending",
                    "priority": priority,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            # 加入优先级队列（使用sorted set）
            score = self._calculate_priority_score(priority)
            await self.redis.zadd(
                "task:queue:batch_generation",
                {task_id: score}
            )
            
            task_ids.append(task_id)
        
        return task_ids
    
    def _calculate_priority_score(self, priority: int) -> float:
        """计算优先级分数（考虑优先级和时间）"""
        # 分数越小优先级越高
        # 格式：(10-priority)*10000000 + timestamp
        return (10 - priority) * 10000000 + time.time()
    
    async def distribute_tasks(self, task_ids: List[str]):
        """分发任务到Kafka"""
        
        for task_id in task_ids:
            # 速率限制
            await self.rate_limiter.acquire()
            
            # 发送到Kafka
            event = {
                "event_type": "BatchGeneration.Requested",
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.kafka.send_and_wait(
                "generation-tasks",
                value=json.dumps(event).encode('utf-8'),
                key=task_id.encode('utf-8')
            )
            
            # 更新任务状态
            await self.redis.hset(f"task:{task_id}", "status", "dispatched")
    
    @task(retries=3, retry_delay_seconds=1)
    async def wait_for_results(
        self,
        task_ids: List[str],
        timeout: int = 5
    ) -> List[Dict[str, Any]]:
        """等待并收集结果"""
        
        results = []
        start_time = time.time()
        
        while len(results) < len(task_ids):
            # 检查超时
            if time.time() - start_time > timeout:
                self.logger.warning(
                    f"Timeout waiting for results. Got {len(results)}/{len(task_ids)}"
                )
                break
            
            # 批量检查任务状态
            for task_id in task_ids:
                if task_id in [r["task_id"] for r in results]:
                    continue  # 已收集
                
                task_data = await self.redis.hgetall(f"task:{task_id}")
                
                if task_data.get("status") == "completed":
                    result = json.loads(task_data.get("result", "{}"))
                    results.append({
                        "task_id": task_id,
                        "result": result
                    })
                elif task_data.get("status") == "failed":
                    self.logger.error(f"Task {task_id} failed")
                    # 可以选择重试或跳过
            
            await asyncio.sleep(0.1)  # 避免忙等待
        
        return results
    
    @task
    async def post_process(
        self,
        results: List[Dict[str, Any]],
        task_type: str
    ) -> List[Dict[str, Any]]:
        """后处理：去重、验证、格式化"""
        
        all_items = []
        
        # 合并所有结果
        for result in results:
            items = result.get("result", {}).get("items", [])
            all_items.extend(items)
        
        # 去重（基于相似度）
        unique_items = await self._deduplicate(all_items, task_type)
        
        # 验证和格式化
        validated_items = await self._validate_items(unique_items, task_type)
        
        return validated_items
    
    async def _deduplicate(
        self,
        items: List[Dict[str, Any]],
        task_type: str
    ) -> List[Dict[str, Any]]:
        """基于相似度去重"""
        
        # 获取去重阈值
        thresholds = {
            "character_name": 1.0,     # 人名完全不重复
            "location_name": 0.8,      # 地名相似度<0.8
            "item": 0.7,              # 物品相似度<0.7
            "skill": 0.7,
            "organization": 0.6
        }
        
        threshold = thresholds.get(task_type, 0.7)
        
        unique_items = []
        seen_embeddings = []
        
        for item in items:
            # 计算嵌入（假设有嵌入服务）
            embedding = await self.get_embedding(item.get("name", ""))
            
            # 检查相似度
            is_unique = True
            for seen_emb in seen_embeddings:
                similarity = self._cosine_similarity(embedding, seen_emb)
                if similarity > threshold:
                    is_unique = False
                    break
            
            if is_unique:
                unique_items.append(item)
                seen_embeddings.append(embedding)
        
        return unique_items
```

### Task Executor Implementation
```python
# apps/backend/src/tasks/batch/executor.py
from aiokafka import AIOKafkaConsumer
import asyncio

class BatchTaskExecutor:
    """批量任务执行器（Agent端）"""
    
    def __init__(self, llm_client, redis_client):
        self.llm = llm_client
        self.redis = redis_client
        self.consumer = None
    
    async def start(self):
        """启动任务消费者"""
        self.consumer = AIOKafkaConsumer(
            'generation-tasks',
            bootstrap_servers=['localhost:9092'],
            group_id='batch_generation_group'
        )
        
        await self.consumer.start()
        
        try:
            async for msg in self.consumer:
                asyncio.create_task(self.process_task(msg))
        finally:
            await self.consumer.stop()
    
    async def process_task(self, message):
        """处理单个批量生成任务"""
        
        event = json.loads(message.value)
        task_id = event['task_id']
        
        try:
            # 获取任务详情
            task_data = await self.redis.hget(f"task:{task_id}", "data")
            task = json.loads(task_data)
            
            # 更新状态
            await self.redis.hset(f"task:{task_id}", "status", "processing")
            
            # 执行生成
            result = await self.generate_batch(
                task['type'],
                task['count'],
                task['style']
            )
            
            # 存储结果
            await self.redis.hset(
                f"task:{task_id}",
                mapping={
                    "status": "completed",
                    "result": json.dumps(result),
                    "completed_at": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            await self.redis.hset(
                f"task:{task_id}",
                mapping={
                    "status": "failed",
                    "error": str(e)
                }
            )
    
    async def generate_batch(
        self,
        item_type: str,
        count: int,
        style: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用LLM生成批量内容"""
        
        # 构建提示词
        prompt = self._build_prompt(item_type, count, style)
        
        # 调用LLM
        response = await self.llm.generate(
            prompt=prompt,
            temperature=0.8,  # 增加多样性
            max_tokens=count * 100  # 根据数量调整
        )
        
        # 解析结果
        items = self._parse_response(response, item_type)
        
        return {"items": items}
```

### Rate Limiting and Priority Management
```python
# apps/backend/src/infrastructure/queue/rate_limiter.py
import asyncio
from datetime import datetime, timedelta

class TokenBucketRateLimiter:
    """令牌桶速率限制器"""
    
    def __init__(
        self,
        rate: int,  # 每秒生成的令牌数
        capacity: int,  # 桶容量
        redis_client
    ):
        self.rate = rate
        self.capacity = capacity
        self.redis = redis_client
        self.key = "rate_limiter:tokens"
    
    async def acquire(self, tokens: int = 1) -> bool:
        """获取令牌"""
        while True:
            # 更新令牌数
            await self._refill()
            
            # 尝试获取
            current = await self.redis.get(self.key)
            current = float(current) if current else self.capacity
            
            if current >= tokens:
                # 扣除令牌
                await self.redis.set(self.key, current - tokens)
                return True
            
            # 等待令牌
            wait_time = (tokens - current) / self.rate
            await asyncio.sleep(wait_time)
    
    async def _refill(self):
        """补充令牌"""
        last_refill = await self.redis.get(f"{self.key}:last_refill")
        now = datetime.utcnow()
        
        if last_refill:
            last_refill = datetime.fromisoformat(last_refill)
            elapsed = (now - last_refill).total_seconds()
            
            # 计算新增令牌
            new_tokens = elapsed * self.rate
            
            # 更新令牌数（不超过容量）
            current = await self.redis.get(self.key)
            current = float(current) if current else 0
            new_total = min(current + new_tokens, self.capacity)
            
            await self.redis.set(self.key, new_total)
        
        await self.redis.set(
            f"{self.key}:last_refill",
            now.isoformat()
        )

class PriorityQueueManager:
    """优先级队列管理器"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get_next_task(self, queue_name: str) -> Optional[str]:
        """获取下一个任务（最高优先级）"""
        
        # 从sorted set中获取分数最低的（优先级最高）
        result = await self.redis.zpopmin(queue_name, 1)
        
        if result:
            task_id, score = result[0]
            return task_id.decode('utf-8')
        
        return None
    
    async def requeue_task(self, queue_name: str, task_id: str, priority: int):
        """重新入队（用于失败重试）"""
        
        # 降低优先级
        new_priority = max(1, priority - 1)
        score = self._calculate_priority_score(new_priority)
        
        await self.redis.zadd(queue_name, {task_id: score})
```

### Monitoring and Metrics
```python
# 监控指标
class BatchSchedulerMetrics:
    """批量调度器监控"""
    
    def __init__(self, prometheus_client):
        self.prom = prometheus_client
        
        # 定义指标
        self.task_counter = Counter(
            'batch_tasks_total',
            'Total batch tasks',
            ['type', 'status']
        )
        
        self.task_duration = Histogram(
            'batch_task_duration_seconds',
            'Task execution duration',
            ['type']
        )
        
        self.queue_size = Gauge(
            'batch_queue_size',
            'Current queue size',
            ['priority']
        )
    
    async def record_task(self, task_type: str, status: str, duration: float):
        """记录任务指标"""
        self.task_counter.labels(type=task_type, status=status).inc()
        self.task_duration.labels(type=task_type).observe(duration)
```

### Rollback Plan
- **触发条件**：吞吐量不足或系统过于复杂
- **回滚步骤**：
  1. 停止新任务提交
  2. 等待现有任务完成
  3. 切换到简单的线程池模式
  4. 逐步优化后再切换回来
- **数据恢复**：Kafka保证消息不丢失

## Validation

### Alignment with Existing Patterns
- **架构一致性检查**：完全符合事件驱动架构
- **代码审查重点**：
  - 任务分解逻辑
  - 优先级算法
  - 错误处理和重试

### Metrics
- **性能指标**：
  - 任务调度延迟：P95 < 100ms
  - 批量生成时间：P95 < 5秒（10-50项）
  - 任务吞吐量：> 100 tasks/秒
  - 队列延迟：P95 < 500ms
- **可靠性指标**：
  - 任务成功率：> 99%
  - 重试成功率：> 95%

### Test Strategy
- **单元测试**：任务分解、优先级计算
- **集成测试**：端到端的批量生成流程
- **性能测试**：大批量任务的处理能力
- **压力测试**：队列堆积和背压处理
- **故障测试**：Agent故障时的恢复

## References
- [Prefect文档](https://docs.prefect.io/)
- [Kafka最佳实践](https://kafka.apache.org/documentation/#bestpractices)
- [Redis Sorted Sets](https://redis.io/docs/data-types/sorted-sets/)
- [Token Bucket算法](https://en.wikipedia.org/wiki/Token_bucket)

## Changelog
- 2025-09-04: 初始草稿创建