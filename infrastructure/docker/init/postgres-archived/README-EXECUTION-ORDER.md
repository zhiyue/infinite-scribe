# PostgreSQL 数据库初始化脚本执行顺序

## ⚠️ 重要提醒：执行顺序至关重要

这些脚本**必须按照严格的顺序执行**，任何顺序错误都可能导致数据库初始化失败。所有脚本已根据 `docs/architecture/database-schema.md` 完全重新设计和实现。

## 🏗️ 架构设计原则

### 核心设计原则
- **统一事件日志**: `domain_events` 表是整个系统所有业务事实的唯一、不可变来源
- **状态快照**: 核心业务表存储实体的当前状态快照，由领域事件驱动更新
- **可靠的异步通信**: `command_inbox`, `event_outbox`, 和 `flow_resume_handles` 构成健壮的异步通信基石
- **混合外键策略**: 核心领域模型表之间保留外键约束，高吞吐量日志表无外键以获得更好性能

## 🔢 标准执行顺序

### 阶段1: 基础设施初始化
```
00-init-databases.sql        # 数据库和扩展初始化
01-init-functions.sql        # 基础函数（如时间戳触发器函数）
02-init-enums.sql           # 所有枚举类型定义
```

### 阶段2: 核心业务实体
```
03-core-entities.sql        # 核心业务实体表（小说、章节、角色等）
04-genesis-sessions.sql     # 创世流程状态快照表
04a-concept-templates.sql   # 立意模板表和初始化数据
```

### 阶段3: 架构机制表
```
05-domain-events.sql        # 统一领域事件日志表
06-command-inbox.sql        # 命令收件箱（幂等性保证）
07-async-tasks.sql          # 异步任务追踪表
08-event-outbox.sql         # 事务性事件发件箱
09-flow-resume-handles.sql  # 工作流恢复句柄存储
```

### 阶段4: 性能优化
```
10-indexes.sql              # 性能关键索引
11-triggers.sql             # 所有触发器
```

## 🚨 关键依赖关系

### 基础依赖链
1. **00** → **01**: 需要 pgcrypto 扩展用于 UUID 生成
2. **01** → **02**: 触发器函数用于后续触发器创建
3. **02** → **03**: 枚举类型用于表字段约束
4. **03** → **04**: 需要 novels 表用于外键关联

### 架构机制依赖
5. **04** → **05**: 事件表可能记录创世会话事件
6. **05** → **06**: 命令处理可能生成领域事件
7. **06** → **07**: 任务可能由命令触发
8. **07** → **08**: 任务完成可能发布事件
9. **08** → **09**: 工作流恢复可能涉及事件处理

### 优化层依赖
10. **09** → **10**: 所有表创建完成后添加索引
11. **10** → **11**: 所有索引创建完成后添加触发器

## 📋 详细脚本说明

### 00-init-databases.sql
- 创建 `infinite_scribe` 和 `prefect` 数据库
- 安装必要扩展：`pgcrypto`, `btree_gin`, `pg_stat_statements`
- 为两个数据库配置扩展

### 01-init-functions.sql
- 创建 `trigger_set_timestamp()` 函数
- 用于自动更新 `updated_at` 字段

### 02-init-enums.sql
创建9个枚举类型：
- `agent_type`: AI智能体类型（10个值）
- `novel_status`: 小说状态（5个值）
- `chapter_status`: 章节状态（4个值）
- `command_status`: 命令状态（4个值）
- `task_status`: 任务状态（5个值）
- `outbox_status`: 发件箱状态（2个值）
- `handle_status`: 句柄状态（4个值）
- `genesis_status`: 创世状态（3个值）
- `genesis_stage`: 创世阶段（6个值）

### 03-core-entities.sql
创建7个核心业务实体表：
- `novels`: 小说主表
- `chapters`: 章节元数据表
- `chapter_versions`: 章节版本表（版本控制）
- `characters`: 角色表
- `worldview_entries`: 世界观条目表
- `story_arcs`: 故事弧表
- `reviews`: 评审记录表

### 04-genesis-sessions.sql
- `genesis_sessions`: 创世流程状态快照表
- 包含检查约束和查询索引

### 04a-concept-templates.sql
- `concept_templates`: 立意模板表
- 存储抽象的哲学立意供用户在创世流程中选择
- 包含10个预定义的立意模板示例数据
- 支持哲学分类、复杂度分级和主题标签查询

### 05-domain-events.sql
- `domain_events`: 统一领域事件日志表
- 事件溯源架构的核心，不可变事件存储
- 包含防篡改触发器和高性能索引

### 06-command-inbox.sql
- `command_inbox`: 命令收件箱表
- 通过唯一索引提供幂等性保证
- 包含自动清理功能

### 07-async-tasks.sql
- `async_tasks`: 异步任务表
- 支持进度追踪和重试机制
- 包含超时检测和统计视图

### 08-event-outbox.sql
- `event_outbox`: 事务性事件发件箱
- 保证数据库写入与消息发布的原子性
- 支持延迟发送和分区键

### 09-flow-resume-handles.sql
- `flow_resume_handles`: 工作流恢复句柄表
- 支持 Prefect 工作流的暂停/恢复机制
- 处理竞态条件和过期管理

### 10-indexes.sql
- 创建性能关键的补充索引
- 包含复合查询、全文搜索、时序分析索引
- 性能监控视图

### 11-triggers.sql
创建多类触发器：
- 时间戳自动更新触发器（9个）
- 业务逻辑触发器（小说进度统计、状态转换等）
- 数据完整性触发器
- 审计和乐观锁触发器

## 🏗️ 部署方式

### Docker 自动部署
Docker 会按文件名字典序自动执行 `/docker-entrypoint-initdb.d/` 中的脚本：

```bash
# Docker 自动执行顺序（推荐）
docker-compose up -d postgres
```

### 手动部署
如需手动执行，必须严格按序：

```bash
cd infrastructure/docker/init/postgres/

psql -d infinite_scribe -f 00-init-databases.sql
psql -d infinite_scribe -f 01-init-functions.sql
psql -d infinite_scribe -f 02-init-enums.sql
psql -d infinite_scribe -f 03-core-entities.sql
psql -d infinite_scribe -f 04-genesis-sessions.sql
psql -d infinite_scribe -f 04a-concept-templates.sql
psql -d infinite_scribe -f 05-domain-events.sql
psql -d infinite_scribe -f 06-command-inbox.sql
psql -d infinite_scribe -f 07-async-tasks.sql
psql -d infinite_scribe -f 08-event-outbox.sql
psql -d infinite_scribe -f 09-flow-resume-handles.sql
psql -d infinite_scribe -f 10-indexes.sql
psql -d infinite_scribe -f 11-triggers.sql
```

### CI/CD 流水线
```yaml
steps:
  - name: Execute Database Initialization Scripts
    run: |
      scripts=(
        "00-init-databases.sql"
        "01-init-functions.sql"
        "02-init-enums.sql"
        "03-core-entities.sql"
        "04-genesis-sessions.sql"
        "04a-concept-templates.sql"
        "05-domain-events.sql"
        "06-command-inbox.sql"
        "07-async-tasks.sql"
        "08-event-outbox.sql"
        "09-flow-resume-handles.sql"
        "10-indexes.sql"
        "11-triggers.sql"
      )
      
      for script in "${scripts[@]}"; do
        echo "Executing $script..."
        psql -d infinite_scribe -f "infrastructure/docker/init/postgres/$script"
        if [ $? -ne 0 ]; then
          echo "❌ Script $script failed!"
          exit 1
        fi
        echo "✅ Script $script completed successfully"
      done
```

## ⚠️ 常见错误和解决方案

### 错误1：扩展不存在
```
ERROR: extension "pgcrypto" is not available
```
**解决**: 确保 PostgreSQL 安装了所需扩展

### 错误2：枚举类型不存在
```
ERROR: type "agent_type" does not exist
```
**解决**: 确保 02-init-enums.sql 先执行

### 错误3：函数不存在
```
ERROR: function trigger_set_timestamp() does not exist
```
**解决**: 确保 01-init-functions.sql 先执行

### 错误4：表不存在的外键错误
```
ERROR: relation "novels" does not exist
```
**解决**: 检查脚本执行顺序，确保依赖表先创建

## 🔄 数据库重置

如需完全重置数据库：

```bash
# 删除所有表（谨慎操作）
psql -d infinite_scribe -c "
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
"

# 重新执行所有脚本
# 然后按顺序重新执行00-11脚本
```

## 📊 验证初始化结果

初始化完成后可执行以下查询验证：

```sql
-- 检查表数量
SELECT COUNT(*) as table_count 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

-- 检查枚举类型
SELECT typname FROM pg_type WHERE typtype = 'e' ORDER BY typname;

-- 检查索引数量
SELECT COUNT(*) as index_count FROM pg_indexes WHERE schemaname = 'public';

-- 检查触发器数量
SELECT COUNT(*) as trigger_count FROM information_schema.triggers WHERE trigger_schema = 'public';

-- 检查函数数量
SELECT COUNT(*) as function_count FROM pg_proc WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public');
```

## 📝 更新日志

- **2024-07**: 完全重写，基于最新的架构设计
- 新增事件溯源架构支持
- 新增异步处理机制
- 新增工作流恢复功能
- 优化索引策略和触发器设计

---

**重要提醒**: 此文档与实际脚本内容保持同步。如修改任何脚本，请同时更新此文档。