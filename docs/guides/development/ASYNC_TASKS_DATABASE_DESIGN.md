# 异步任务数据库设计

## 📋 问题背景

在更新 REST API 支持异步处理和 SSE 推送后，我们需要调整数据库来支持以下新需求：

### 现有问题
1. **长时间 AI 交互**: 立意生成、故事构思等操作需要几秒到几十秒
2. **任务状态追踪**: 需要实时跟踪任务进度和状态
3. **错误处理**: 任务失败时需要记录详细错误信息
4. **结果关联**: 异步任务完成后需要关联到正确的 `genesis_step`
5. **性能监控**: 需要统计各类任务的执行时间和成功率
6. **用户体验**: 避免界面假死，提供流畅的实时反馈
7. **连接管理**: 管理多个客户端的SSE连接和事件订阅

### 现有表结构限制
- `genesis_steps` 表设计为同步操作，缺乏异步任务管理能力
- 无法跟踪任务的中间状态和进度
- 缺乏任务失败时的错误信息存储
- 无法进行任务性能分析

## 🔧 数据库调整方案

### 1. 新增枚举类型

```sql
-- 任务状态枚举
CREATE TYPE task_status AS ENUM (
    'PENDING',    -- 等待处理
    'RUNNING',    -- 正在运行
    'COMPLETED',  -- 已完成
    'FAILED',     -- 失败
    'CANCELLED'   -- 已取消
);

-- 创世任务类型枚举
CREATE TYPE genesis_task_type AS ENUM (
    'concept_generation',     -- 立意生成
    'concept_refinement',     -- 立意优化
    'story_generation',       -- 故事构思生成
    'story_refinement',       -- 故事构思优化
    'worldview_generation',   -- 世界观生成
    'character_generation',   -- 角色生成
    'plot_generation'         -- 剧情生成
);
```

### 2. 核心表：genesis_tasks

```sql
CREATE TABLE genesis_tasks (
    id UUID PRIMARY KEY,
    
    -- 关联信息
    session_id UUID REFERENCES genesis_sessions(id),
    target_stage genesis_stage NOT NULL,
    task_type genesis_task_type NOT NULL,
    
    -- 任务状态  
    status task_status DEFAULT 'PENDING',
    progress DECIMAL(4,3) DEFAULT 0.000, -- 0.000 到 1.000
    current_stage VARCHAR(100), -- 如 "preference_analysis"
    message TEXT, -- 如 "正在分析用户偏好..."
    
    -- 任务数据
    input_data JSONB NOT NULL,
    result_data JSONB,
    error_data JSONB,
    
    -- 结果关联
    result_step_id UUID REFERENCES genesis_steps(id),
    
    -- 性能监控
    agent_type agent_type,
    estimated_duration_seconds INTEGER,
    actual_duration_seconds INTEGER,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
```

### 3. 数据完整性约束

```sql
-- 进度范围约束
CONSTRAINT progress_range CHECK (progress >= 0.000 AND progress <= 1.000)

-- 完成任务必须有结果数据
CONSTRAINT valid_completed_task CHECK (
    status != 'COMPLETED' OR (result_data IS NOT NULL AND completed_at IS NOT NULL)
)

-- 失败任务必须有错误信息
CONSTRAINT valid_failed_task CHECK (
    status != 'FAILED' OR error_data IS NOT NULL
)

-- 运行中任务必须有开始时间
CONSTRAINT valid_running_task CHECK (
    status != 'RUNNING' OR started_at IS NOT NULL
)
```

## 📊 数据流设计

### 异步任务生命周期

```
1. 创建任务 (PENDING)
   ↓
2. 开始执行 (RUNNING) → 设置 started_at
   ↓ 
3. 更新进度 → progress: 0.1, 0.3, 0.7...
   ↓
4. 完成/失败
   ├─ COMPLETED → 保存 result_data, 创建 genesis_step
   └─ FAILED → 保存 error_data
```

### 典型数据示例

#### 立意生成任务
```json
{
  "input_data": {
    "user_preferences": {
      "complexity": "medium",
      "preferred_genres": ["科幻", "奇幻"],
      "emotional_themes": ["成长", "友情"]
    }
  },
  "result_data": {
    "step_type": "ai_generation",
    "generated_concepts": [
      {
        "temp_id": 1,
        "core_idea": "知识与无知的深刻对立",
        "description": "探讨知识如何改变一个人的命运...",
        "philosophical_depth": "当个体获得超越同辈的知识时...",
        "emotional_core": "理解与被理解之间的渴望与隔阂"
      }
    ]
  }
}
```

#### 立意优化任务
```json
{
  "input_data": {
    "selected_concept_ids": [1, 3, 7],
    "user_feedback": "希望能够更突出主角的孤独感，并且加入一些关于友情的元素"
  },
  "result_data": {
    "step_type": "concept_refinement", 
    "refined_concepts": [...]
  }
}
```

## 🔍 查询操作设计

### 1. 创建异步任务
```sql
SELECT create_genesis_task(
    'session-uuid',
    'CONCEPT_SELECTION',
    'concept_generation',
    '{"user_preferences": {...}}',
    'worldsmith',
    30
);
```

### 2. 更新任务进度
```sql
SELECT update_task_progress(
    'task-uuid',
    0.45,
    'concept_generation',
    '正在生成哲学立意...'
);
```

### 3. 查询任务状态
```sql
SELECT * FROM genesis_task_summary 
WHERE id = 'task-uuid';
```

### 4. 获取会话的活跃任务
```sql
SELECT * FROM genesis_tasks 
WHERE session_id = 'session-uuid' 
  AND status IN ('PENDING', 'RUNNING')
ORDER BY created_at DESC;
```

### 5. 性能统计
```sql
SELECT * FROM get_task_performance_stats(7); -- 最近7天
```

## ⚡ 性能优化

### 索引策略
```sql
-- 常用查询组合索引
CREATE INDEX idx_genesis_tasks_session_status ON genesis_tasks(session_id, status);
CREATE INDEX idx_genesis_tasks_type_status ON genesis_tasks(task_type, status);

-- 活跃任务查询优化
CREATE INDEX idx_genesis_tasks_status ON genesis_tasks(status) 
WHERE status IN ('PENDING', 'RUNNING');

-- JSONB 数据查询优化
CREATE INDEX idx_genesis_tasks_result_data ON genesis_tasks USING GIN(result_data);
```

### 自动清理策略
```sql
-- 定期清理30天前的已完成任务
SELECT cleanup_old_genesis_tasks(30);
```

## 🧩 与现有系统集成

### API 层集成
```python
# 创建异步任务
task_id = await create_genesis_task(
    session_id, 'CONCEPT_SELECTION', 'concept_generation', 
    user_preferences
)

# 更新进度（在 Agent 执行过程中）
await update_task_progress(task_id, 0.3, 'preference_analysis', '正在分析用户偏好...')
await update_task_progress(task_id, 0.7, 'concept_generation', '正在生成哲学立意...')

# 完成任务并创建结果步骤
step_id = await create_genesis_step(session_id, result_data)
await complete_genesis_task(task_id, result_data, step_id)
```

### SSE 事件推送
```python
# 基于任务状态变化推送 SSE 事件
async def on_task_progress_update(task_id, progress, stage, message):
    await sse_manager.send_event(
        event='progress_update',
        data={
            'task_id': task_id,
            'progress': progress,
            'stage': stage,
            'message': message
        }
    )

# SSE连接管理最佳实践
class SSEManager:
    """SSE连接管理器 - 支持按会话和任务订阅"""

    async def add_connection(self, connection_id, session_id=None, task_id=None):
        """添加SSE连接，支持灵活订阅"""
        # 实现连接索引和管理
        pass

    async def broadcast_to_session(self, session_id, event):
        """向特定会话的所有连接广播"""
        pass

    async def broadcast_to_task(self, task_id, event):
        """向特定任务的所有连接广播"""
        pass

# Agent进度报告集成
class BaseAgent:
    async def report_progress(self, task_id, progress, stage, message):
        """Agent执行过程中报告进度"""
        await task_service.update_progress(task_id, progress, stage, message)
        # 自动触发SSE推送
```

## 📈 监控和统计

### 实时监控指标
1. **活跃任务数量**: 当前 PENDING/RUNNING 状态的任务数
2. **平均执行时间**: 各类任务的平均完成时间
3. **成功率**: 任务成功完成的百分比
4. **超时任务**: 执行时间超过预估时间2倍的任务

### 性能分析视图
```sql
CREATE VIEW genesis_task_summary AS
SELECT 
    gt.*,
    -- 计算实际执行时间
    EXTRACT(EPOCH FROM (completed_at - started_at))::INTEGER as duration_seconds,
    -- 检测超时任务
    CASE 
        WHEN status = 'RUNNING' AND estimated_duration_seconds IS NOT NULL
        THEN EXTRACT(EPOCH FROM (NOW() - started_at))::INTEGER > (estimated_duration_seconds * 2)
        ELSE FALSE
    END as is_timeout
FROM genesis_tasks gt
JOIN genesis_sessions gs ON gt.session_id = gs.id;
```

## 🔄 数据迁移策略

### 现有数据兼容性
- 现有 `genesis_steps` 表保持不变
- 新的异步任务通过 `result_step_id` 关联到 `genesis_steps`
- 同步操作继续使用原有流程
- 异步操作使用新的任务管理系统

### 渐进式迁移
1. **阶段1**: 部署新表结构，异步和同步并存
2. **阶段2**: 逐步将长时间操作迁移到异步模式
3. **阶段3**: 优化性能，完善监控

## ✅ 优势总结

### 1. **用户体验提升**
- 实时进度反馈，避免界面假死
- 详细的状态描述，用户了解处理进展
- 支持断线重连，任务状态持久化

### 2. **系统可靠性**
- 完整的错误处理和重试机制
- 任务超时检测和告警
- 数据一致性保证

### 3. **性能监控**
- 详细的任务执行统计
- Agent 性能分析
- 系统瓶颈识别

### 4. **可扩展性**
- 支持新的异步任务类型
- 灵活的任务数据结构 (JSONB)
- 便于水平扩展的设计

这个数据库设计完全支持新的异步 + SSE 架构，为创世流程提供了强大的任务管理和监控能力。