# CONCEPT_SELECTION 和 STORY_CONCEPTION 阶段数据存储设计

## 数据存储需求分析

### CONCEPT_SELECTION 阶段数据类型

#### 1. AI生成立意数据
```json
{
  "step_type": "ai_generation",
  "generation_config": {
    "concept_count": 10,
    "user_preferences": {...},
    "template_sources": ["uuid1", "uuid2"]
  },
  "generated_concepts": [
    {
      "temp_id": 1,
      "core_idea": "知识与无知的深刻对立",
      "description": "探讨知识如何改变一个人的命运...",
      "philosophical_depth": "当个体获得超越同辈的知识时...",
      "emotional_core": "理解与被理解之间的渴望与隔阂",
      "derived_from_template": "uuid-or-null"
    }
  ]
}
```

#### 2. 用户选择数据
```json
{
  "step_type": "user_selection",
  "selected_concept_ids": [1, 3, 7],
  "user_feedback": "希望能够更突出主角的孤独感...",
  "action": "iterate"
}
```

#### 3. 立意迭代优化数据
```json
{
  "step_type": "concept_refinement",
  "refined_concepts": [
    {
      "temp_id": 1,
      "original_concept": {...},
      "refined_concept": {...},
      "adjustments_made": "根据您的反馈，强化了知识带来的孤独感..."
    }
  ]
}
```

#### 4. 立意确认数据
```json
{
  "step_type": "concept_confirmation",
  "confirmed_concepts": [
    {
      "temp_id": 1,
      "final_concept": {...}
    }
  ],
  "transition_data": {
    "ready_for_story_conception": true,
    "confirmed_at": "2024-01-01T00:00:00Z"
  }
}
```

### STORY_CONCEPTION 阶段数据类型

#### 1. 故事构思生成数据
```json
{
  "step_type": "story_generation",
  "source_concepts": [...],
  "generated_story_concept": {
    "title_suggestions": ["异世界的智者之路", "穿越时空的求知者"],
    "core_concept": "现代大学生穿越到异世界魔法学院...",
    "main_themes": ["知识的力量", "友情与理解", "成长与自我发现"],
    "target_audience": "成年奇幻爱好者",
    "estimated_length": "长篇（50-80万字）",
    "genre_suggestions": ["奇幻", "穿越", "成长"],
    "emotional_journey": "从迷茫困顿到获得知识，再到在友情中找到归属感",
    "character_archetypes": ["现代知识型主角", "异世界导师", "理解主角的朋友"],
    "world_setting_hints": ["魔法学院", "现代知识与魔法的融合", "文化差异环境"]
  }
}
```

#### 2. 故事构思优化数据
```json
{
  "step_type": "story_refinement",
  "user_feedback": "希望标题更有诗意一些，目标读者群体更年轻化",
  "specific_adjustments": {
    "title_suggestions": "希望标题更有诗意一些",
    "target_audience": "希望面向更年轻的读者群体"
  },
  "refined_story_concept": {...},
  "adjustments_made": "根据您的反馈，调整了标题风格更具诗意..."
}
```

#### 3. 故事构思确认数据
```json
{
  "step_type": "story_confirmation",
  "final_story_concept": {...},
  "transition_data": {
    "ready_for_worldview": true,
    "confirmed_at": "2024-01-01T00:00:00Z",
    "worldview_seeds": {
      "world_type": "异世界魔法学院",
      "magic_system_hints": "现代知识与魔法结合",
      "social_structure_hints": "学院等级制度",
      "conflict_sources": ["文化冲突", "知识差异", "身份认同"]
    }
  }
}
```

## 数据库存储方案

### 方案一：使用现有 genesis_steps 表（推荐）

#### 优势
- 复用现有结构，无需额外迁移
- JSONB字段提供足够灵活性
- 时间顺序自然保持
- 查询逻辑相对简单

#### 存储示例

```sql
-- CONCEPT_SELECTION 阶段的步骤记录示例
INSERT INTO genesis_steps (
    session_id, 
    stage, 
    iteration_count, 
    ai_prompt,
    ai_output,
    user_feedback,
    is_confirmed
) VALUES (
    'session-uuid',
    'CONCEPT_SELECTION',
    1, -- 第1次迭代
    'Generate 10 philosophical concepts based on user preferences...',
    '{
        "step_type": "ai_generation",
        "generation_config": {...},
        "generated_concepts": [...]
    }',
    NULL,
    false
);

-- 用户选择和反馈
INSERT INTO genesis_steps (
    session_id,
    stage,
    iteration_count,
    ai_output,
    user_feedback,
    is_confirmed
) VALUES (
    'session-uuid',
    'CONCEPT_SELECTION', 
    2, -- 第2次迭代
    '{
        "step_type": "user_selection",
        "selected_concept_ids": [1, 3, 7],
        "action": "iterate"
    }',
    '希望能够更突出主角的孤独感，并且加入一些关于友情的元素',
    false
);

-- AI优化后的立意
INSERT INTO genesis_steps (
    session_id,
    stage, 
    iteration_count,
    ai_output,
    is_confirmed
) VALUES (
    'session-uuid',
    'CONCEPT_SELECTION',
    3, -- 第3次迭代
    '{
        "step_type": "concept_refinement",
        "refined_concepts": [...]
    }',
    false
);

-- 最终确认
INSERT INTO genesis_steps (
    session_id,
    stage,
    iteration_count, 
    ai_output,
    is_confirmed
) VALUES (
    'session-uuid',
    'CONCEPT_SELECTION',
    4, -- 第4次迭代（确认）
    '{
        "step_type": "concept_confirmation",
        "confirmed_concepts": [...],
        "transition_data": {...}
    }',
    true -- 标记为已确认
);
```

#### 查询操作示例

```sql
-- 获取某会话的所有立意选择步骤
SELECT * FROM genesis_steps 
WHERE session_id = 'session-uuid' 
  AND stage = 'CONCEPT_SELECTION'
ORDER BY iteration_count;

-- 获取最终确认的立意
SELECT ai_output 
FROM genesis_steps 
WHERE session_id = 'session-uuid' 
  AND stage = 'CONCEPT_SELECTION' 
  AND is_confirmed = true
  AND ai_output->>'step_type' = 'concept_confirmation';

-- 获取用户在立意阶段的所有反馈
SELECT iteration_count, user_feedback, created_at
FROM genesis_steps 
WHERE session_id = 'session-uuid' 
  AND stage = 'CONCEPT_SELECTION' 
  AND user_feedback IS NOT NULL
ORDER BY iteration_count;

-- 获取故事构思的最终版本
SELECT ai_output->'final_story_concept' as story_concept
FROM genesis_steps 
WHERE session_id = 'session-uuid' 
  AND stage = 'STORY_CONCEPTION' 
  AND is_confirmed = true
  AND ai_output->>'step_type' = 'story_confirmation';
```

### 方案二：增加专门表（备选方案）

如果需要更强的结构化和查询性能，可以考虑增加专门表：

```sql
-- 用户立意选择记录表
CREATE TABLE IF NOT EXISTS user_concept_selections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES genesis_sessions(id) ON DELETE CASCADE,
    step_id UUID NOT NULL REFERENCES genesis_steps(id) ON DELETE CASCADE,
    selected_concept_ids INTEGER[] NOT NULL,
    selection_feedback TEXT,
    is_final_selection BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 确认的创世元素表（跨阶段数据）
CREATE TABLE IF NOT EXISTS confirmed_genesis_elements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES genesis_sessions(id) ON DELETE CASCADE,
    stage genesis_stage NOT NULL,
    element_type VARCHAR(50) NOT NULL, -- 'concepts', 'story_framework', etc.
    element_data JSONB NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_stage_element UNIQUE (session_id, stage, element_type)
);
```

## 数据一致性和完整性

### 跨阶段数据传递

```sql
-- 创建视图简化跨阶段数据查询
CREATE OR REPLACE VIEW genesis_confirmed_data AS
SELECT 
    gs.session_id,
    gs.novel_id,
    -- 提取立意确认数据
    (SELECT ai_output->'confirmed_concepts' 
     FROM genesis_steps 
     WHERE session_id = gs.session_id 
       AND stage = 'CONCEPT_SELECTION' 
       AND is_confirmed = true 
     LIMIT 1) as confirmed_concepts,
    -- 提取故事构思确认数据  
    (SELECT ai_output->'final_story_concept' 
     FROM genesis_steps 
     WHERE session_id = gs.session_id 
       AND stage = 'STORY_CONCEPTION' 
       AND is_confirmed = true 
     LIMIT 1) as confirmed_story_concept
FROM genesis_sessions gs;
```

### 数据验证约束

```sql
-- 添加约束确保数据完整性
ALTER TABLE genesis_steps 
ADD CONSTRAINT valid_concept_selection_data 
CHECK (
    stage != 'CONCEPT_SELECTION' OR (
        ai_output ? 'step_type' AND 
        ai_output->>'step_type' IN ('ai_generation', 'user_selection', 'concept_refinement', 'concept_confirmation')
    )
);

ALTER TABLE genesis_steps 
ADD CONSTRAINT valid_story_conception_data 
CHECK (
    stage != 'STORY_CONCEPTION' OR (
        ai_output ? 'step_type' AND 
        ai_output->>'step_type' IN ('story_generation', 'story_refinement', 'story_confirmation')
    )
);
```

## API 操作示例

### 保存立意生成结果

```python
async def save_concept_generation(session_id: UUID, generated_concepts: List[dict]) -> UUID:
    """保存AI生成的立意选项"""
    
    step_data = {
        "step_type": "ai_generation",
        "generation_config": {
            "concept_count": len(generated_concepts),
            "generated_at": datetime.utcnow().isoformat()
        },
        "generated_concepts": generated_concepts
    }
    
    step_id = await db.execute(
        """
        INSERT INTO genesis_steps (session_id, stage, iteration_count, ai_output)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        session_id,
        "CONCEPT_SELECTION", 
        1,  # 首次生成
        json.dumps(step_data)
    )
    
    return step_id
```

### 保存用户选择和反馈

```python
async def save_user_concept_selection(
    session_id: UUID, 
    selected_ids: List[int], 
    feedback: str, 
    action: str
) -> UUID:
    """保存用户的立意选择和反馈"""
    
    # 获取当前迭代次数
    current_iteration = await db.fetchval(
        """
        SELECT COALESCE(MAX(iteration_count), 0) + 1
        FROM genesis_steps 
        WHERE session_id = $1 AND stage = $2
        """,
        session_id, "CONCEPT_SELECTION"
    )
    
    step_data = {
        "step_type": "user_selection",
        "selected_concept_ids": selected_ids,
        "action": action
    }
    
    step_id = await db.execute(
        """
        INSERT INTO genesis_steps (session_id, stage, iteration_count, ai_output, user_feedback)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        session_id,
        "CONCEPT_SELECTION",
        current_iteration,
        json.dumps(step_data),
        feedback
    )
    
    return step_id
```

### 获取阶段数据

```python
async def get_concept_selection_history(session_id: UUID) -> List[dict]:
    """获取立意选择阶段的完整历史"""
    
    rows = await db.fetch(
        """
        SELECT iteration_count, ai_output, user_feedback, is_confirmed, created_at
        FROM genesis_steps 
        WHERE session_id = $1 AND stage = $2
        ORDER BY iteration_count
        """,
        session_id, "CONCEPT_SELECTION"
    )
    
    return [
        {
            "iteration": row["iteration_count"],
            "data": row["ai_output"],
            "user_feedback": row["user_feedback"],
            "is_confirmed": row["is_confirmed"],
            "timestamp": row["created_at"]
        }
        for row in rows
    ]

async def get_confirmed_concepts(session_id: UUID) -> dict:
    """获取最终确认的立意"""
    
    row = await db.fetchrow(
        """
        SELECT ai_output
        FROM genesis_steps 
        WHERE session_id = $1 
          AND stage = $2 
          AND is_confirmed = true
          AND ai_output->>'step_type' = 'concept_confirmation'
        """,
        session_id, "CONCEPT_SELECTION"
    )
    
    if row:
        return row["ai_output"]["confirmed_concepts"]
    return None
```

## 存储优化建议

### 1. 索引优化

```sql
-- 为常用查询创建复合索引
CREATE INDEX IF NOT EXISTS idx_genesis_steps_session_stage_confirmed 
ON genesis_steps(session_id, stage, is_confirmed);

-- 为JSONB查询创建GIN索引
CREATE INDEX IF NOT EXISTS idx_genesis_steps_ai_output_step_type 
ON genesis_steps USING GIN ((ai_output->'step_type'));

-- 为时间范围查询优化
CREATE INDEX IF NOT EXISTS idx_genesis_steps_created_at 
ON genesis_steps(created_at) WHERE is_confirmed = true;
```

### 2. 数据清理策略

```sql
-- 清理未确认的老旧迭代数据（可选）
DELETE FROM genesis_steps 
WHERE stage IN ('CONCEPT_SELECTION', 'STORY_CONCEPTION')
  AND is_confirmed = false 
  AND created_at < NOW() - INTERVAL '30 days';
```

### 3. 数据压缩

```sql
-- 对于大型JSONB字段，可以考虑压缩存储
ALTER TABLE genesis_steps 
ALTER COLUMN ai_output SET STORAGE EXTENDED;
```

## 总结

**推荐使用方案一**（现有 genesis_steps 表），理由：

1. **简单可靠**: 复用现有结构，降低复杂性
2. **灵活性高**: JSONB字段可以适应数据结构变化  
3. **查询效率**: 配合适当索引，查询性能充足
4. **维护成本低**: 无需额外表结构和迁移

通过合理的数据结构设计和查询优化，现有表结构完全可以支持 CONCEPT_SELECTION 和 STORY_CONCEPTION 阶段的所有数据存储需求。