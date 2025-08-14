# CONCEPT_SELECTION 和 STORY_CONCEPTION 阶段数据存储解决方案

## 📋 总结

我们成功为新的创世流程阶段设计了完整的数据存储解决方案，**无需新增数据库表**，通过优化现有的 `genesis_steps` 表和相关索引/约束来支持所有数据存储需求。

## 🎯 核心存储策略

### 使用现有表结构
- **主表**: `genesis_steps` 表存储所有阶段的交互数据
- **JSONB字段**: `ai_output` 存储灵活的结构化数据
- **迭代追踪**: `iteration_count` 字段追踪同一阶段内的迭代过程
- **确认状态**: `is_confirmed` 字段标记最终确认的数据

### 数据组织方式

```
genesis_steps 表数据流:
CONCEPT_SELECTION 阶段:
  iteration_count=1: AI生成10个立意 (step_type: "ai_generation")
  iteration_count=2: 用户选择+反馈 (step_type: "user_selection")  
  iteration_count=3: AI优化立意 (step_type: "concept_refinement")
  iteration_count=4: 用户确认立意 (step_type: "concept_confirmation", is_confirmed=true)

STORY_CONCEPTION 阶段:
  iteration_count=1: AI生成故事构思 (step_type: "story_generation")
  iteration_count=2: 用户反馈+AI优化 (step_type: "story_refinement")
  iteration_count=3: 用户确认构思 (step_type: "story_confirmation", is_confirmed=true)
```

## 🔧 数据库优化内容

### 1. 新增索引（已添加到迁移脚本）
```sql
-- 复合查询优化
CREATE INDEX idx_genesis_steps_session_stage_confirmed 
    ON genesis_steps(session_id, stage, is_confirmed);

-- JSONB字段查询优化  
CREATE INDEX idx_genesis_steps_ai_output_step_type 
    ON genesis_steps USING GIN ((ai_output->'step_type'));

-- 确认数据时间查询
CREATE INDEX idx_genesis_steps_confirmed_created_at 
    ON genesis_steps(created_at) WHERE is_confirmed = true;
```

### 2. 数据验证约束
```sql
-- 确保 CONCEPT_SELECTION 阶段数据完整性
ALTER TABLE genesis_steps ADD CONSTRAINT valid_concept_selection_data 
CHECK (stage != 'CONCEPT_SELECTION' OR (
    ai_output ? 'step_type' AND 
    ai_output->>'step_type' IN ('ai_generation', 'user_selection', 'concept_refinement', 'concept_confirmation')
));

-- 确保 STORY_CONCEPTION 阶段数据完整性
ALTER TABLE genesis_steps ADD CONSTRAINT valid_story_conception_data 
CHECK (stage != 'STORY_CONCEPTION' OR (
    ai_output ? 'step_type' AND 
    ai_output->>'step_type' IN ('story_generation', 'story_refinement', 'story_confirmation')
));

-- 每个阶段只能有一个确认步骤
CREATE UNIQUE INDEX idx_genesis_steps_unique_confirmed_per_stage 
    ON genesis_steps(session_id, stage) WHERE is_confirmed = true;
```

### 3. 辅助函数
```sql
-- 获取确认的立意数据
get_confirmed_concepts(session_uuid UUID) RETURNS JSONB

-- 获取确认的故事构思数据  
get_confirmed_story_concept(session_uuid UUID) RETURNS JSONB

-- 获取阶段迭代历史
get_stage_iteration_history(session_uuid UUID, target_stage genesis_stage) RETURNS TABLE

-- 跨阶段数据查询视图
VIEW genesis_confirmed_data
```

## 📊 典型数据存储示例

### CONCEPT_SELECTION 阶段数据
```json
{
  "step_type": "concept_confirmation",
  "confirmed_concepts": [
    {
      "temp_id": 1,
      "core_idea": "知识与无知的深刻对立",
      "description": "探讨知识如何改变一个人的命运，以及无知所带来的悲剧与痛苦",
      "philosophical_depth": "当个体获得超越同辈的知识时，他将面临孤独与责任的双重考验",
      "emotional_core": "理解与被理解之间的渴望与隔阂，以及在孤独中寻找真挚友情的珍贵"
    }
  ],
  "transition_data": {
    "ready_for_story_conception": true,
    "confirmed_at": "2024-01-01T00:00:00Z"
  }
}
```

### STORY_CONCEPTION 阶段数据
```json
{
  "step_type": "story_confirmation",
  "final_story_concept": {
    "title_suggestions": ["异世界的智者之路", "穿越时空的求知者"],
    "core_concept": "现代大学生穿越到异世界魔法学院，利用现代知识与魔法结合...",
    "main_themes": ["知识的力量", "友情与理解", "成长与自我发现"],
    "target_audience": "成年奇幻爱好者",
    "estimated_length": "长篇（50-80万字）",
    "genre_suggestions": ["奇幻", "穿越", "成长"],
    "emotional_journey": "从迷茫困顿到获得知识，再到在友情中找到归属感"
  },
  "transition_data": {
    "ready_for_worldview": true,
    "confirmed_at": "2024-01-01T00:00:00Z",
    "worldview_seeds": {
      "world_type": "异世界魔法学院",
      "magic_system_hints": "现代知识与魔法结合"
    }
  }
}
```

## 🔍 常用查询操作

### 获取立意选择历史
```sql
SELECT * FROM get_stage_iteration_history('session-uuid', 'CONCEPT_SELECTION');
```

### 获取确认的立意
```sql
SELECT get_confirmed_concepts('session-uuid');
```

### 获取确认的故事构思  
```sql
SELECT get_confirmed_story_concept('session-uuid');
```

### 跨阶段数据概览
```sql
SELECT * FROM genesis_confirmed_data WHERE session_id = 'session-uuid';
```

### 查找特定类型的步骤
```sql
SELECT ai_output FROM genesis_steps 
WHERE session_id = 'session-uuid' 
  AND ai_output->>'step_type' = 'concept_confirmation';
```

## ✅ 解决方案优势

### 1. **简单可靠**
- 复用现有表结构，无需复杂迁移
- 降低系统复杂度和维护成本
- 减少数据一致性问题

### 2. **灵活可扩展**  
- JSONB字段适应数据结构变化
- 支持未来新增字段而无需表结构修改
- step_type机制便于添加新的交互类型

### 3. **查询高效**
- 针对性索引优化常用查询场景
- 辅助函数简化复杂数据获取
- 视图提供跨阶段数据的便捷访问

### 4. **数据完整性**
- 约束确保数据格式正确性
- 唯一索引防止重复确认
- 事务性保证操作原子性

## 🚀 部署步骤

1. **执行迁移脚本**
   ```bash
   psql -d infinite_scribe -f 09-migration-concept-templates.sql
   ```

2. **验证功能**
   ```sql
   -- 检查新索引
   \d genesis_steps
   
   -- 测试辅助函数
   SELECT get_confirmed_concepts('test-uuid');
   
   -- 检查约束
   SELECT conname FROM pg_constraint WHERE conrelid = 'genesis_steps'::regclass;
   ```

3. **API集成**
   - 实现数据存储和查询逻辑
   - 使用辅助函数简化代码
   - 遵循JSON数据结构规范

这个解决方案为新的创世流程提供了完整、高效、可维护的数据存储基础，支持复杂的用户交互和迭代优化流程。