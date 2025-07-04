# ConceptTemplateModel 实现方案

## 技术方案

### 1. 数据模型设计
ConceptTemplateModel 用于存储抽象的哲学立意模板，包含以下字段：
- `id`: UUID 主键
- `core_idea`: 核心抽象思想（200字符）
- `description`: 立意深层含义（800字符）
- `philosophical_depth`: 哲学思辨深度（1000字符）
- `emotional_core`: 情感核心（500字符）
- `philosophical_category`: 哲学类别
- `thematic_tags`: 主题标签（JSONB数组）
- `complexity_level`: 复杂度级别（simple/medium/complex）
- `universal_appeal`: 是否具有普遍意义
- `cultural_specificity`: 文化特异性
- `is_active`: 是否启用
- `created_by`: 创建者
- `created_at/updated_at`: 时间戳

### 2. 数据库表设计
- 创建 `concept_templates` 表
- 添加必要的检查约束（复杂度级别、字符长度等）
- 创建索引优化查询性能（包括 GIN 索引用于 JSONB 字段）

### 3. 示例数据
准备10个预定义的哲学立意模板，涵盖：
- 存在主义
- 认知哲学
- 道德伦理
- 时间哲学
- 人性本质
- 权力与自由
- 生命意义
- 真理与信仰
- 东方哲学
- 爱与孤独

## 架构设计
```
┌─────────────────────────┐
│   ConceptTemplateModel  │
│   (Python/Pydantic)     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  concept_templates      │
│  (PostgreSQL Table)     │
├─────────────────────────┤
│ - id (UUID)             │
│ - core_idea             │
│ - description           │
│ - philosophical_depth   │
│ - emotional_core        │
│ - thematic_tags (JSONB) │
│ - ...                   │
└─────────────────────────┘
```

## 风险评估
- **风险**：数据库初始化脚本执行顺序错误
- **缓解**：创建 04a-concept-templates.sql 确保在 04-genesis-sessions.sql 之后执行

## 测试计划
1. 验证 Python 模型语法正确性
2. 验证 SQL 脚本语法
3. 确认表创建成功
4. 验证示例数据插入成功
5. 测试模型导入和辅助函数