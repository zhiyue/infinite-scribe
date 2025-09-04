# 业务逻辑层实现

## 质量评分计算实现

质量评分采用**多维度加权模型**，整合以下维度：

| 维度           | 权重范围 | 数据源            | 评分标准                   |
| -------------- | -------- | ----------------- | -------------------------- |
| **LLM 评分**   | 0.4-0.6  | GPT-4/Claude 评估 | 内容质量、创意度、连贯性   |
| **规则校验**   | 0.1-0.2  | 硬编码规则引擎    | 格式正确性、必填项完整性   |
| **相似度检测** | 0.1-0.2  | Milvus 向量检索   | 避免重复、保持新颖性       |
| **一致性校验** | 0.2-0.3  | Neo4j 图数据分析  | 角色关系、世界规则、时间线 |

### 阶段特定权重调整

```yaml
Stage_0_创意种子:
  创意性: +10% # 提高创意权重
  一致性: -10% # 降低一致性要求

Stage_1_立意主题:
  语义相似度: +15% # 强调与种子的关联
  规则校验: -15% # 放宽格式要求

Stage_2_世界观:
  一致性: +20% # 强调内部一致性
  创意性: -20% # 降低创意要求

Stage_3_人物:
  完整性: +15% # 8维度完整性
  一致性: +10% # 与世界观一致

Stage_4_情节:
  结构性: +20% # 情节逻辑
  相似度: -20% # 允许创新

Stage_5_细节:
  规则校验: +30% # 格式规范性
  创意性: -30% # 批量生成规范化
```

### 评分计算实现

```python
def calculate_quality_score(stage: str, content: dict, novel_id: str) -> float:
    """计算质量评分"""
    # 获取一致性校验器
    validator = ConsistencyValidator()
    consistency_result = await validator.validate_all(novel_id)

    base_scores = {
        'llm_score': llm_evaluate(content),           # 0-10
        'rule_check': validate_rules(content),        # 0或1
        'similarity': calculate_similarity(content),   # 0-1
        'consistency': consistency_result.score       # 0-10（来自Neo4j校验）
    }

    # 归一化到0-10
    normalized = {
        'llm_score': base_scores['llm_score'],
        'rule_check': base_scores['rule_check'] * 10,
        'similarity': base_scores['similarity'] * 10,
        'consistency': base_scores['consistency']     # 已经是0-10
    }

    # 应用权重
    weights = get_stage_weights(stage)
    final_score = sum(
        normalized[key] * weights[key]
        for key in normalized
    )

    return final_score

def get_stage_weights(stage: str) -> dict:
    """获取阶段特定权重"""
    base_weights = {
        'llm_score': 0.30,
        'rule_check': 0.20,
        'similarity': 0.25,
        'consistency': 0.25
    }

    adjustments = {
        'Stage_0': {'llm_score': +0.10, 'consistency': -0.10},
        'Stage_1': {'similarity': +0.15, 'rule_check': -0.15},
        'Stage_2': {'consistency': +0.20, 'llm_score': -0.20},
        'Stage_3': {'rule_check': +0.15, 'consistency': +0.10, 'similarity': -0.25},
        'Stage_4': {'rule_check': +0.20, 'similarity': -0.20},
        'Stage_5': {'rule_check': +0.30, 'llm_score': -0.30}
    }

    if stage in adjustments:
        for key, adjustment in adjustments[stage].items():
            base_weights[key] += adjustment

    return base_weights
```

### 评分阈值与处理策略

| 分数区间 | 处理策略                 | 事件类型                  |
| -------- | ------------------------ | ------------------------- |
| ≥ 8.0    | 直接通过，推送用户确认   | `*.Proposed`              |
| 6.0-7.9  | 带建议通过，标记可优化点 | `*.Proposed` + 建议       |
| 4.0-5.9  | 需要修正，生成改进建议   | `*.RevisionRequested`     |
| < 4.0    | 重新生成，调整prompt     | `*.RegenerationRequested` |

### 重试与DLT策略

```python
class QualityRetryPolicy:
    """质量重试策略"""

    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 15, 30]  # 秒

    def should_retry(self, score: float, attempt: int) -> bool:
        """判断是否重试"""
        if attempt >= self.MAX_RETRIES:
            return False

        # 分数过低直接DLT
        if score < 2.0:
            return False

        # 逐次提高阈值
        threshold = 4.0 + (attempt * 1.0)
        return score < threshold

    def get_retry_strategy(self, attempt: int) -> dict:
        """获取重试策略"""
        strategies = {
            1: {
                'temperature': 0.9,      # 提高创造性
                'prompt_adjust': 'creative'
            },
            2: {
                'temperature': 0.7,      # 平衡模式
                'prompt_adjust': 'detailed',
                'examples': True         # 添加示例
            },
            3: {
                'temperature': 0.5,      # 保守模式
                'prompt_adjust': 'structured',
                'model': 'gpt-4'        # 切换模型
            }
        }
        return strategies.get(attempt, strategies[3])
```

## 采纳率监控

```yaml
metrics:
  # 实时指标
  acceptance_rate:
    formula: confirmed_events / proposed_events
    window: 1_hour
    alert_threshold: < 0.6

  # 阶段指标
  stage_acceptance:
    stage_0: 0.75 # 创意阶段容忍度高
    stage_1: 0.70 # 主题阶段标准
    stage_2: 0.65 # 世界观复杂度高
    stage_3: 0.70 # 人物设计标准
    stage_4: 0.60 # 情节框架挑战大
    stage_5: 0.80 # 细节生成规范化

  # 改进触发
  improvement_triggers:
    - acceptance_rate < 0.5 for 30_minutes
    - stage_failures > 5 in 1_hour
    - user_rejections > 3 consecutive
```

## 质量反馈循环

1. **即时反馈**：每次生成后立即评分
2. **用户反馈**：记录接受/拒绝/修改行为
3. **模型调优**：基于历史数据调整prompt模板
4. **知识库更新**：高分内容入库作为示例

## 一致性校验规则集（Neo4j实现）

### 校验查询定义

```cypher
-- 1. 角色关系闭包校验
-- 检测关系不一致：A→B→C 但 A与C无关系定义
MATCH (a:Character)-[:RELATES_TO]->(b:Character)-[:RELATES_TO]->(c:Character)
WHERE a.novel_id = $novel_id
  AND NOT EXISTS((a)-[:RELATES_TO]-(c))
  AND a <> c
RETURN a.name as character1, b.name as mediator, c.name as character2,
       "Missing transitive relationship" as violation

-- 2. 世界规则冲突检测
-- 检测矛盾的世界规则
MATCH (r1:WorldRule)-[:CONFLICTS_WITH]-(r2:WorldRule)
WHERE r1.novel_id = $novel_id
  AND EXISTS((r1)-[:GOVERNS]->(:Novel)<-[:GOVERNS]-(r2))
RETURN r1.rule as rule1, r2.rule as rule2,
       "Conflicting rules both govern the same novel" as violation

-- 3. 时间线一致性校验
-- 检测时间悖论：因在果之后
MATCH (e1:Event)-[:CAUSES]->(e2:Event)
WHERE e1.novel_id = $novel_id
  AND e1.timestamp > e2.timestamp
RETURN e1.description as cause_event, e1.timestamp as cause_time,
       e2.description as effect_event, e2.timestamp as effect_time,
       "Cause happens after effect" as violation

-- 4. 人物属性一致性校验
-- 检测不合理的属性突变
MATCH (c:Character)-[:HAS_STATE]->(s1:CharacterState),
      (c)-[:HAS_STATE]->(s2:CharacterState)
WHERE c.novel_id = $novel_id
  AND s2.chapter = s1.chapter + 1
  AND abs(s2.age - s1.age) > 10  -- 年龄突变超过10岁
  AND NOT EXISTS((e:Event {type: 'time_skip'}))
RETURN c.name as character, s1.chapter as chapter1, s1.age as age1,
       s2.chapter as chapter2, s2.age as age2,
       "Unreasonable age change" as violation

-- 5. 地理空间一致性校验
-- 检测不可能的移动速度
MATCH (c:Character)-[:LOCATED_AT]->(l1:Location),
      (c)-[:LOCATED_AT]->(l2:Location)
WHERE c.novel_id = $novel_id
  AND l2.timestamp - l1.timestamp < 3600  -- 1小时内
  AND distance(point({x: l1.x, y: l1.y}),
               point({x: l2.x, y: l2.y})) > 500  -- 超过500公里
  AND NOT EXISTS((c)-[:USES]->(:Transportation {type: 'teleport'}))
RETURN c.name as character, l1.name as from_location, l2.name as to_location,
       duration((l2.timestamp - l1.timestamp)) as travel_time,
       distance(point({x: l1.x, y: l1.y}), point({x: l2.x, y: l2.y})) as distance,
       "Impossible travel speed" as violation
```

### 校验器Python实现

```python
class ConsistencyValidator:
    """一致性校验器"""

    VALIDATION_RULES = {
        'relationship_closure': {
            'query': RELATIONSHIP_CLOSURE_QUERY,
            'severity': 'warning',
            'auto_fix': True
        },
        'world_rule_conflict': {
            'query': WORLD_RULE_CONFLICT_QUERY,
            'severity': 'error',
            'auto_fix': False
        },
        'timeline_consistency': {
            'query': TIMELINE_CONSISTENCY_QUERY,
            'severity': 'error',
            'auto_fix': True
        },
        'character_continuity': {
            'query': CHARACTER_CONTINUITY_QUERY,
            'severity': 'warning',
            'auto_fix': True
        },
        'spatial_consistency': {
            'query': SPATIAL_CONSISTENCY_QUERY,
            'severity': 'warning',
            'auto_fix': True
        }
    }

    async def validate_all(self, novel_id: str) -> ValidationResult:
        """执行所有校验规则"""
        violations = []

        for rule_name, rule_config in self.VALIDATION_RULES.items():
            result = await self.neo4j.run(
                rule_config['query'],
                {'novel_id': novel_id}
            )

            if result:
                violations.append({
                    'rule': rule_name,
                    'severity': rule_config['severity'],
                    'violations': result,
                    'auto_fix_available': rule_config['auto_fix']
                })

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            score=self.calculate_consistency_score(violations)
        )

    def calculate_consistency_score(self, violations: List) -> float:
        """计算一致性分数（0-10）"""
        if not violations:
            return 10.0

        penalties = {
            'error': 3.0,
            'warning': 1.0,
            'info': 0.3
        }

        total_penalty = sum(
            penalties[v['severity']] * len(v['violations'])
            for v in violations
        )

        return max(0, 10.0 - total_penalty)
```

## 自动修复策略

```yaml
auto_fix_strategies:
  relationship_closure:
    action: 'infer_weak_relationship'
    parameters:
      default_strength: 2
      relationship_type: 'knows_of'

  timeline_consistency:
    action: 'adjust_timestamps'
    parameters:
      method: 'shift_forward'
      maintain_relative_order: true

  character_continuity:
    action: 'interpolate_states'
    parameters:
      method: 'linear'
      add_explanation: true

  spatial_consistency:
    action: 'add_transportation'
    parameters:
      infer_type: true
      calculate_min_time: true
```

## 一致性报告示例

```json
{
  "novel_id": "uuid",
  "validation_time": "2025-01-15T10:30:00Z",
  "overall_score": 7.5,
  "violations": [
    {
      "rule": "relationship_closure",
      "severity": "warning",
      "count": 3,
      "examples": [
        {
          "character1": "张三",
          "character2": "王五",
          "issue": "Missing transitive relationship via 李四",
          "suggested_fix": "Add 'knows_of' relationship with strength=2"
        }
      ]
    },
    {
      "rule": "timeline_consistency",
      "severity": "error",
      "count": 1,
      "examples": [
        {
          "event1": "Battle of Dawn",
          "event2": "King's coronation",
          "issue": "Cause happens 10 years after effect",
          "suggested_fix": "Move Battle of Dawn to year 1020"
        }
      ]
    }
  ],
  "auto_fixes_applied": 2,
  "manual_review_required": 1
}
```

## 批量任务调度实现

采用**分阶段实现**的批量处理架构：

| 实现阶段           | 调度方式               | 能力特性                                | 适用场景             |
| ------------------ | ---------------------- | --------------------------------------- | -------------------- |
| **P1: 简单调度**   | 基于 Outbox 的事件驱动 | 任务分发、状态跟踪、基础重试            | MVP阶段、单用户场景  |
| **P2: 工作流编排** | Prefect 流程引擎       | 暂停/恢复、条件分支、并行处理、失败补偿 | 多用户、复杂业务逻辑 |

### 任务生命周期管理

**任务分类**：

- **细节生成任务**：地名、人名、道具等批量创建
- **内容校验任务**：一致性检查、质量评估
- **优化任务**：向量索引更新、缓存刷新

**状态流转**：

```
待调度 → 执行中 → 完成/失败 → 清理
   ↓        ↓        ↓        ↓
  入队 → 分发给Agent → 结果回收 → 资源回收
```

**容错机制**：

- **重试策略**：指数退避，最多3次
- **超时处理**：任务超时自动取消并重新调度
- **死信队列**：多次失败任务进入DLT处理

### P1实现：基于Outbox的简单调度

```python
class BatchDetailGenerator:
    """P1: 批量细节生成（无Prefect）"""

    async def generate_details(self, novel_id: str, categories: List[str], style: str):
        """通过Agent直接处理批量任务"""
        # 发布到Outbox
        await self.publish_to_outbox({
            "event_type": "Genesis.Session.Details.Requested",
            "novel_id": novel_id,
            "categories": categories,
            "style": style
        })

        # Detail Generator Agent会消费任务并处理
        # 完成后发布 Genesis.Session.Details.Generated 事件

class TaskScheduler:
    """任务调度器"""

    async def schedule_batch_tasks(self, tasks: List[dict]) -> str:
        """调度批量任务"""
        batch_id = str(uuid.uuid4())

        # 为每个任务创建Outbox条目
        for task in tasks:
            await self.publish_to_outbox({
                "event_type": f"{task['agent_type']}.Task.Requested",
                "batch_id": batch_id,
                "task_id": task['id'],
                "payload": task['payload']
            })

        return batch_id

    async def track_batch_progress(self, batch_id: str) -> dict:
        """跟踪批量任务进度"""
        # 查询任务状态
        tasks = await self.get_batch_tasks(batch_id)

        completed = sum(1 for t in tasks if t['status'] == 'completed')
        failed = sum(1 for t in tasks if t['status'] == 'failed')

        return {
            "batch_id": batch_id,
            "total": len(tasks),
            "completed": completed,
            "failed": failed,
            "progress": completed / len(tasks) if tasks else 0
        }
```

### P2扩展：Prefect工作流编排

```python
from prefect import flow, task
from prefect.tasks import task_input_hash
from datetime import timedelta

@task(
    retries=3,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1)
)
async def generate_batch_details(
    category: str,
    count: int,
    style: str
) -> List[str]:
    """批量生成细节任务"""
    # 实际的细节生成逻辑
    pass

@flow(name="genesis-detail-generation")
async def detail_generation_flow(
    novel_id: str,
    categories: List[str],
    style: str
):
    """P2: 复杂工作流编排
    - 支持暂停/恢复
    - 支持条件分支
    - 支持并行处理
    - 支持失败补偿
    """

    # 并行生成各类细节
    futures = []
    for category in categories:
        future = await generate_batch_details.submit(
            category=category,
            count=get_count_for_category(category),
            style=style
        )
        futures.append(future)

    # 等待所有任务完成
    results = await gather(*futures)

    # 发布完成事件
    await publish_to_outbox({
        "event_type": "Genesis.Session.Details.Completed",
        "novel_id": novel_id,
        "results": results
    })

class WorkflowOrchestrator:
    """P2工作流编排器"""

    async def start_complex_workflow(self, workflow_type: str, params: dict):
        """启动复杂工作流"""
        if workflow_type == "detail_generation":
            return await detail_generation_flow(
                novel_id=params["novel_id"],
                categories=params["categories"],
                style=params["style"]
            )
        # 其他工作流类型...

    async def pause_workflow(self, flow_run_id: str):
        """暂停工作流"""
        # Prefect API调用暂停
        pass

    async def resume_workflow(self, flow_run_id: str):
        """恢复工作流"""
        # Prefect API调用恢复
        pass
```

### 限流实现

```python
class RateLimiter:
    """限流器实现"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def sliding_window_check(self, key: str, window_size: int, limit: int) -> bool:
        """滑动窗口限流（P1实现）"""
        now = int(time.time())
        window_start = now - window_size

        pipe = self.redis.pipeline()
        # 删除窗口外的记录
        pipe.zremrangebyscore(key, 0, window_start)
        # 添加当前请求
        pipe.zadd(key, {str(now): now})
        # 获取当前窗口内的请求数
        pipe.zcard(key)
        # 设置过期时间
        pipe.expire(key, window_size)

        results = await pipe.execute()
        current_count = results[2]

        return current_count <= limit

    async def token_bucket_check(self, key: str, capacity: int, refill_rate: float) -> bool:
        """令牌桶限流（P2实现，使用Redis Lua脚本）"""
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])

        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now

        -- 计算需要补充的令牌数
        local time_passed = now - last_refill
        local tokens_to_add = time_passed * refill_rate
        tokens = math.min(capacity, tokens + tokens_to_add)

        if tokens >= 1 then
            tokens = tokens - 1
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, 3600)
            return 1
        else
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, 3600)
            return 0
        end
        """

        result = await self.redis.eval(
            lua_script, 1, key, capacity, refill_rate, int(time.time())
        )

        return bool(result)
```