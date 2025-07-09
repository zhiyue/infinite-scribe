# SQL与ORM模型对比报告

## 检查时间
2025-07-08

## 检查范围
- SQL文件路径: `/infrastructure/docker/init/postgres/`
- ORM文件路径: `/apps/backend/src/models/orm_models.py`

## 主要发现与修复

### 1. ✅ 已修复的问题

#### 1.1 __table_args__ 重复定义
以下表存在`__table_args__`被重复赋值的语法错误，已全部修复：
- `GenesisSession` - 将索引定义合并到主`__table_args__`元组中
- `CommandInbox` - 将索引定义合并到主`__table_args__`元组中  
- `AsyncTask` - 将索引定义合并到主`__table_args__`元组中
- `EventOutbox` - 将索引定义合并到主`__table_args__`元组中
- `FlowResumeHandle` - 将索引定义合并到主`__table_args__`元组中

### 2. ✅ 验证一致的部分

#### 2.1 表结构
所有表的字段定义与SQL完全一致：
- 字段名称、类型、约束都匹配
- 默认值设置正确
- 外键关系定义正确

#### 2.2 特殊字段处理
- `chapter_versions.metadata` → ORM使用 `Column("metadata", JSONB)` 映射到 `version_metadata` 属性
- `domain_events.metadata` → ORM使用 `Column("metadata", JSONB)` 映射到 `event_metadata` 属性

#### 2.3 枚举类型
所有枚举类型都正确导入和使用：
- `NovelStatus`, `ChapterStatus`, `GenesisStage`, `GenesisStatus`
- `AgentType`, `WorldviewEntryType`, `CommandStatus`
- `TaskStatus`, `OutboxStatus`, `HandleStatus`

#### 2.4 约束定义
- 唯一约束：正确定义在 `__table_args__` 中
- 检查约束：所有业务规则约束都已定义
- 外键约束：级联行为（CASCADE, SET NULL）正确设置

### 3. ⚠️ 需要注意的差异

#### 3.1 SQL中有但ORM中缺少的元素

**触发器（需在应用层实现）：**
- `set_timestamp_*` - 自动更新 `updated_at`（ORM通过`onupdate=func.now()`实现）
- `update_novel_progress_and_status_trigger` - 自动更新小说进度
- `increment_version_*_trigger` - 版本号自动递增
- `prevent_domain_event_modification` - 防止修改领域事件

**函数：**
- `get_pending_outbox_messages()`
- `mark_outbox_message_sent()`
- `mark_outbox_message_failed()`
- `cleanup_sent_outbox_messages()`

**视图：**
- `async_task_statistics`

#### 3.2 索引覆盖
SQL中定义的补充索引（10-indexes.sql）未在ORM中体现，但不影响功能：
- 全文搜索索引
- GIN索引（JSONB字段）
- 部分索引（带WHERE条件）

### 4. 建议

1. **应用层实现触发器逻辑**
   - 使用SQLAlchemy事件监听器实现版本号自增
   - 在服务层实现小说进度统计逻辑
   - 使用数据库级触发器保证领域事件不可变性

2. **考虑添加缺失的索引**
   - 可以在ORM中使用`Index`明确定义所有索引
   - 特别是GIN索引和部分索引对查询性能很重要

3. **数据库函数**
   - 可以通过SQLAlchemy的`text()`或存储过程调用使用SQL函数
   - 或在Python服务层实现等效逻辑

## 结论

ORM模型与SQL定义基本一致，主要的语法错误已修复。剩余的差异主要是：
- 数据库级别的触发器和函数需要在应用层实现
- 补充索引可以根据实际查询性能需求添加

整体上，ORM正确映射了数据库结构，可以正常工作。