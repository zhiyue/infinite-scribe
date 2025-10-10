# 多Agent协作最佳实践指南

## 核心原则

### 1. 统一correlation_id策略

**推荐**: 使用 `command.id`（UUID）作为整条链路的correlation_id

```python
# ✅ 正确做法
correlation_id = str(command.id)  # UUID格式

# ❌ 避免做法
correlation_id = idempotency_key  # 可能不是UUID格式
```

**理由**:
- 保证UUID格式一致性
- 便于事件系统处理
- 支持跨服务追踪

### 2. Round分层规范

#### 顶层Round（用户可见）
```python
# 每个用户Command创建一个顶层round
round_data = {
    "round_path": str(session.round_sequence + 1),  # "5"
    "role": "user",
    "correlation_id": str(command.id),
    "input": {
        "command_type": command_type,
        "command_id": str(command.id),
        "payload": payload,
        "source": "command_api"
    }
}
```

#### 子Round（Agent阶段性输出）
```python
# Agent的每次"对用户可见"的阶段性输出
agent_round = {
    "round_path": f"{parent_round}.{step_number}",  # "5.1", "5.2"
    "role": "assistant",
    "correlation_id": str(command.id),
    "output": {
        "agent_type": "character_expert",
        "agent_id": agent_instance_id,
        "step": "character_analysis",
        "result": analysis_data,
        "metrics": {
            "execution_time_ms": 1500,
            "tokens_used": 800
        }
    }
}
```

#### 迭代Round（优化过程）
```python
# 迭代优化的每一轮
iteration_round = {
    "round_path": f"{base_round}.{iteration_num}",  # "5.2.1", "5.2.2"
    "role": "assistant",
    "correlation_id": str(command.id),
    "output": {
        "agent_type": "director",
        "iteration_number": iteration_num,
        "iteration_type": "refinement",  # "initial", "refinement", "correction"
        "convergence_score": 0.85,
        "refined_result": improved_data
    }
}
```

### 3. Agent标识最佳实践

#### 在Round中记录Agent信息
```python
agent_metadata = {
    "agent_type": "character_expert",      # Agent类型
    "agent_id": f"expert_{uuid4().hex[:8]}", # Agent实例ID
    "agent_version": "1.2.0",             # Agent版本
    "step": "psychological_analysis",      # 执行步骤
    "capabilities": ["psychology", "dialogue"], # 能力标签
}

# 放入round.output或round.input
round.output.update(agent_metadata)
```

#### AsyncTask中记录执行细节
```python
async_task = {
    "triggered_by_command_id": command.id,
    "task_type": "character_analysis",
    "agent_type": "character_expert",
    "agent_id": agent_instance_id,
    "status": "RUNNING",
    "progress": 60,
    "input_data": {...},
    "intermediate_results": {...},
    "error_details": None
}
```

## 实现模式

### 1. 原子操作模式

```python
async def create_command_with_round(
    db: AsyncSession,
    user_id: int,
    session_id: UUID,
    command_type: str,
    payload: dict,
    idempotency_key: str
) -> dict:
    """原子创建Command和Round"""

    async with transactional(db):
        # 1. 创建Command
        command = await create_command_inbox(...)

        # 2. 创建顶层Round
        round_obj = await create_conversation_round(
            correlation_id=str(command.id),  # 使用command.id
            input_data={
                "command_type": command_type,
                "command_id": str(command.id),
                "payload": payload
            }
        )

        # 3. 创建Domain Events
        event = await create_domain_event(...)

        # 4. 创建EventOutbox
        await create_event_outbox(...)

        return {"command": command, "round": round_obj}
```

### 2. Agent协作模式

```python
async def execute_multi_agent_workflow(
    command_id: UUID,
    workflow_steps: List[AgentStep]
) -> None:
    """执行多Agent协作工作流"""

    correlation_id = str(command_id)
    parent_round = await get_command_round(command_id)

    for i, step in enumerate(workflow_steps, 1):
        # 创建Agent执行任务
        task = await create_async_task(
            command_id=command_id,
            agent_type=step.agent_type,
            task_data=step.input_data
        )

        # 执行Agent任务
        result = await execute_agent_task(task)

        # 创建阶段性Round
        await create_agent_round(
            round_path=f"{parent_round.round_path}.{i}",
            correlation_id=correlation_id,
            agent_result=result
        )

        # 发布进度事件
        await publish_progress_event(
            correlation_id=correlation_id,
            step=i,
            total_steps=len(workflow_steps),
            result=result
        )
```

### 3. 迭代优化模式

```python
async def iterative_refinement(
    base_round_path: str,
    correlation_id: str,
    max_iterations: int = 5
) -> None:
    """迭代优化模式"""

    iteration = 1
    convergence_threshold = 0.9

    while iteration <= max_iterations:
        # 执行迭代
        result = await execute_refinement_iteration(...)

        # 创建迭代Round
        iteration_round = await create_conversation_round(
            round_path=f"{base_round_path}.{iteration}",
            correlation_id=correlation_id,
            output={
                "iteration_number": iteration,
                "convergence_score": result.score,
                "refined_content": result.content,
                "should_continue": result.score < convergence_threshold
            }
        )

        # 检查收敛条件
        if result.score >= convergence_threshold:
            break

        iteration += 1

    # 标记最终迭代
    await mark_final_iteration(iteration_round.round_path)
```

## 前端集成指南

### 1. SSE事件订阅

```typescript
// 前端订阅特定command的进度更新
const eventSource = new EventSource(
    `/api/sse/sessions/${sessionId}/commands/${commandId}`
);

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // 按correlation_id聚合事件
    if (data.correlation_id === commandId) {
        updateWorkflowProgress(data);
    }
};
```

### 2. Round树状展示

```typescript
interface RoundNode {
    roundPath: string;
    role: 'user' | 'assistant';
    agentType?: string;
    content: any;
    children: RoundNode[];
    isIteration: boolean;
    iterationNumber?: number;
}

// 构建Round树
function buildRoundTree(rounds: ConversationRound[]): RoundNode[] {
    const commandRounds = rounds.filter(r =>
        r.correlation_id === commandId
    );

    return constructTree(commandRounds);
}
```

### 3. 进度可视化

```typescript
// 工作流进度条
interface WorkflowProgress {
    commandId: string;
    totalSteps: number;
    completedSteps: number;
    currentAgent: string;
    status: 'running' | 'completed' | 'failed';
    iterations?: IterationProgress[];
}

// 实时更新进度
function updateProgress(eventData: any) {
    if (eventData.event_type.includes('Agent.Started')) {
        setCurrentAgent(eventData.payload.agent_type);
    }

    if (eventData.event_type.includes('Agent.Completed')) {
        incrementCompletedSteps();
    }
}
```

## 监控和排错

### 1. 链路追踪查询

```sql
-- 查询某个command的完整链路
SELECT
    cr.round_path,
    cr.role,
    cr.output->>'agent_type' as agent_type,
    cr.created_at,
    at.status as task_status,
    at.progress
FROM conversation_rounds cr
LEFT JOIN async_tasks at ON at.triggered_by_command_id::text = cr.correlation_id
WHERE cr.correlation_id = 'cmd_uuid_123'
ORDER BY cr.round_path;
```

### 2. 性能监控

```python
# 记录关键指标
metrics = {
    "command_id": str(command.id),
    "total_execution_time_ms": end_time - start_time,
    "agent_count": len(involved_agents),
    "iteration_count": max_iteration,
    "rounds_created": len(created_rounds),
    "events_published": len(domain_events)
}

await publish_metrics(metrics)
```

### 3. 错误恢复

```python
async def recover_failed_workflow(command_id: UUID) -> None:
    """恢复失败的工作流"""

    # 找到失败的任务
    failed_tasks = await get_failed_tasks(command_id)

    for task in failed_tasks:
        # 重新创建任务
        retry_task = await create_retry_task(task)

        # 创建恢复Round
        await create_recovery_round(
            correlation_id=str(command_id),
            recovery_info={"retried_task_id": task.id}
        )
```

## 总结

通过规范化使用现有的分层round + correlation_id机制，我们可以：

1. **完整追踪**：记录多agent协作的每个阶段
2. **实时响应**：通过SSE提供毫秒级进度更新
3. **易于排错**：correlation_id串联整条链路
4. **性能优越**：避免复杂的跨表查询
5. **扩展性强**：JSONB字段支持灵活的元数据

关键是要**统一标准**，确保所有agent都遵循相同的round创建和事件发布规范。