# Alembic Migration 说明

## 初始 Migration - 3b8fe0c17290

创建时间: 2025-07-09

### 包含的表

#### 核心业务表
- `novels` - 小说表
- `chapters` - 章节元数据表
- `chapter_versions` - 章节版本表
- `characters` - 角色表
- `worldview_entries` - 世界观条目表
- `story_arcs` - 故事弧表
- `reviews` - 评审记录表

#### 创世流程表
- `genesis_sessions` - 创世会话表
- `concept_templates` - 立意模板表

#### 架构机制表
- `domain_events` - 领域事件表
- `command_inbox` - 命令收件箱表
- `async_tasks` - 异步任务表
- `event_outbox` - 事件发件箱表
- `flow_resume_handles` - 工作流恢复句柄表

#### 用户认证表
- `users` - 用户表
- `sessions` - 会话表
- `email_verifications` - 邮箱验证表

### 应用 Migration

1. **检查数据库连接**
   ```bash
   cd /home/zhiyue/workspace/mvp/infinite-scribe/apps/backend
   uv run alembic current
   ```

2. **查看待应用的 migrations**
   ```bash
   uv run alembic history
   ```

3. **应用 migration**
   ```bash
   uv run alembic upgrade head
   ```

4. **回滚 migration（如需要）**
   ```bash
   uv run alembic downgrade -1
   ```

### 注意事项

1. **SQL 文件管理的表**
   - 某些表可能已经通过 SQL 初始化脚本创建
   - 如果遇到表已存在的错误，需要检查 `env.py` 中的 `include_object` 函数
   - 可以将已存在的表添加到 `sql_managed_tables` 集合中

2. **触发器和函数**
   - 数据库触发器（如 `updated_at` 自动更新）需要单独通过 SQL 脚本创建
   - ORM 通过 `onupdate=func.now()` 在应用层实现类似功能

3. **枚举类型**
   - PostgreSQL 会创建对应的枚举类型
   - 枚举值的修改需要特殊的 migration 处理

4. **索引**
   - 所有在 ORM 中定义的索引都会被创建
   - 额外的优化索引（如 GIN 索引）需要单独添加