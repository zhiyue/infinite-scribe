# Alembic Migration 日志

## 2025-07-09 - 初始 Migration 应用成功

### Migration ID: 3b8fe0c17290

### 执行结果
✅ **成功** - 所有表已成功创建

### 创建的数据库对象

#### 表 (17个)
**核心业务表:**
- ✓ novels - 小说表
- ✓ chapters - 章节元数据表  
- ✓ chapter_versions - 章节版本表
- ✓ characters - 角色表
- ✓ worldview_entries - 世界观条目表
- ✓ story_arcs - 故事弧表
- ✓ reviews - 评审记录表

**创世流程表:**
- ✓ genesis_sessions - 创世会话表
- ✓ concept_templates - 立意模板表

**架构机制表:**
- ✓ domain_events - 领域事件表
- ✓ command_inbox - 命令收件箱表
- ✓ async_tasks - 异步任务表
- ✓ event_outbox - 事件发件箱表
- ✓ flow_resume_handles - 工作流恢复句柄表

**用户认证表:**
- ✓ users - 用户表
- ✓ sessions - 会话表
- ✓ email_verifications - 邮箱验证表

#### 枚举类型 (11个)
- ✓ agenttype - AI 智能体类型
- ✓ chapterstatus - 章节状态
- ✓ commandstatus - 命令状态
- ✓ genesisstage - 创世阶段
- ✓ genesisstatus - 创世状态
- ✓ handlestatus - 句柄状态
- ✓ novelstatus - 小说状态
- ✓ outboxstatus - 发件箱状态
- ✓ taskstatus - 任务状态
- ✓ verificationpurpose - 验证目的
- ✓ worldviewentrytype - 世界观条目类型

#### 索引
- 创建了 56 个索引，用于优化查询性能

### 下一步工作

1. **应用数据库触发器**
   - updated_at 自动更新触发器
   - 版本号自增触发器
   - 领域事件不可变触发器
   - 小说进度统计触发器

2. **创建数据库函数**
   - get_pending_outbox_messages()
   - mark_outbox_message_sent()
   - mark_outbox_message_failed()
   - cleanup_sent_outbox_messages()

3. **添加补充索引**
   - GIN 索引（用于 JSONB 字段）
   - 部分索引（带 WHERE 条件）
   - 全文搜索索引

### 验证命令

```bash
# 检查当前 migration 状态
uv run alembic current

# 查看 migration 历史
uv run alembic history

# 验证表创建
python scripts/verify_tables.py

# 查看表详细信息（已归档）
# scripts/archived/database-utilities/show_table_info.py
```

## 2025-07-09 - 添加列注释 Migration

### Migration ID: cdbb7c721fea

### 执行结果
✅ **成功** - 所有列注释已成功添加到数据库

### 更新内容

为所有表的列添加了中文注释，提高数据库的可维护性和文档化程度：

**更新的表（14个）：**
- ✓ novels - 添加了 10 个列注释
- ✓ chapters - 添加了 9 个列注释
- ✓ chapter_versions - 添加了 10 个列注释
- ✓ characters - 添加了 11 个列注释
- ✓ worldview_entries - 添加了 9 个列注释
- ✓ story_arcs - 添加了 10 个列注释
- ✓ reviews - 添加了 10 个列注释
- ✓ genesis_sessions - 添加了 9 个列注释
- ✓ concept_templates - 添加了 14 个列注释
- ✓ domain_events - 添加了 11 个列注释
- ✓ command_inbox - 添加了 10 个列注释
- ✓ async_tasks - 添加了 15 个列注释
- ✓ event_outbox - 添加了 13 个列注释
- ✓ flow_resume_handles - 添加了 14 个列注释

### 主要改进

1. **数据库文档化**
   - 每个列都有清晰的中文注释
   - 注释包含字段用途、数据格式、示例等信息
   - 便于开发人员理解数据库结构

2. **迁移生成改进**
   - 未来的迁移将自动包含列注释
   - 提高了数据库的可维护性
   - 便于团队协作和知识传递

### 验证

```bash
# 确认迁移已应用
uv run alembic current
# 输出: cdbb7c721fea (head)

# 查看迁移历史
uv run alembic history
# 显示两个迁移：
# - cdbb7c721fea -> add_column_comments_to_all_tables
# - 3b8fe0c17290 -> initial_migration_for_core_business_
```

## 2025-07-10 - 更新所有 DateTime 字段为 timestamptz

### Migration ID: e63af3b9a311

### 执行结果
✅ **成功** - 迁移已成功应用到数据库

### 更新内容

将所有认证相关表的 DateTime 字段从 TIMESTAMP 更新为 TIMESTAMP WITH TIME ZONE (timestamptz)：

**更新的表和字段：**

1. **users 表（6个字段）：**
   - ✓ locked_until - 账户锁定到期时间
   - ✓ last_login_at - 最后登录时间
   - ✓ email_verified_at - 邮箱验证时间
   - ✓ password_changed_at - 密码修改时间
   - ✓ created_at - 创建时间
   - ✓ updated_at - 更新时间

2. **sessions 表（6个字段）：**
   - ✓ access_token_expires_at - 访问令牌过期时间
   - ✓ refresh_token_expires_at - 刷新令牌过期时间
   - ✓ last_accessed_at - 最后访问时间
   - ✓ revoked_at - 撤销时间
   - ✓ created_at - 创建时间
   - ✓ updated_at - 更新时间

3. **email_verifications 表（4个字段）：**
   - ✓ expires_at - 验证码过期时间
   - ✓ used_at - 验证码使用时间
   - ✓ created_at - 创建时间
   - ✓ updated_at - 更新时间

### 技术改进

1. **时区处理改进**
   - 所有时间戳现在都包含时区信息
   - 数据库自动处理时区转换
   - 避免时区相关的 bug

2. **国际化支持**
   - 更好地支持多时区用户
   - 时间显示更加准确
   - 符合最佳实践

3. **数据完整性**
   - 此迁移不会丢失任何数据
   - 仅改变列的数据类型
   - 支持回滚操作

### 应用迁移

```bash
# 应用迁移到数据库
uv run alembic upgrade head

# 验证迁移状态
uv run alembic current
```