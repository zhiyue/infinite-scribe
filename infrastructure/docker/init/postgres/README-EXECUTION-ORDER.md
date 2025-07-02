# PostgreSQL 初始化脚本执行顺序

## ⚠️ 重要提醒：执行顺序至关重要

这些脚本**必须按照严格的顺序执行**，任何顺序错误都可能导致数据库初始化失败或需要回滚。

## 🔢 标准执行顺序

### 1. 基础设置阶段
```
00-init-databases.sql       # 创建数据库和扩展
01-init-schema.sql         # 创建基础表结构
02-init-functions.sql      # 创建基础函数
```

### 2. 迁移脚本阶段（必须严格按序）
```
03-migration-enums.sql              # ⚠️ 必须最先执行 - 创建所有ENUM类型
04-migration-core-entities.sql     # 更新核心表并创建新表（依赖ENUM）
05-migration-genesis-tracking.sql  # 创世流程表（依赖ENUM）
06-migration-tracking-logging.sql  # 追踪日志表（依赖ENUM）
07-migration-indexes-constraints.sql # 索引和约束
08-migration-triggers.sql          # 触发器（依赖所有前面的表）
```

## 🚨 关键依赖关系

### ENUM 类型依赖
- **03-migration-enums.sql** 定义了以下ENUM类型：
  - `agent_type`
  - `activity_status` 
  - `workflow_status`
  - `event_status`
  - `novel_status`
  - `chapter_status`
  - `genesis_status`
  - `genesis_stage`

- **所有后续脚本** 都依赖这些ENUM类型，特别是：
  - 04-migration-core-entities.sql 中的 `ALTER COLUMN status TYPE novel_status`
  - 各种表中的 `agent_type` 字段定义

### 表依赖关系
- **chapter_versions** 表必须在 **chapters** 表更新之前创建
- **触发器** 必须在所有相关表创建完成后创建
- **外键约束** 在所有表创建完成后添加

## 🏗️ 部署流水线要求

### Docker 初始化
Docker 会按照文件名的字典序自动执行 `/docker-entrypoint-initdb.d/` 中的脚本，因此文件命名已经确保正确顺序。

### 手动部署
如果手动执行这些脚本，必须严格按照上述顺序：

```bash
# 正确的执行方式
psql -d infinite_scribe -f 00-init-databases.sql
psql -d infinite_scribe -f 01-init-schema.sql  
psql -d infinite_scribe -f 02-init-functions.sql
psql -d infinite_scribe -f 03-migration-enums.sql
psql -d infinite_scribe -f 04-migration-core-entities.sql
psql -d infinite_scribe -f 05-migration-genesis-tracking.sql
psql -d infinite_scribe -f 06-migration-tracking-logging.sql
psql -d infinite_scribe -f 07-migration-indexes-constraints.sql
psql -d infinite_scribe -f 08-migration-triggers.sql
```

### CI/CD 流水线配置
```yaml
# 示例：GitHub Actions 或类似CI工具
steps:
  - name: Execute DB Migration Scripts
    run: |
      # 必须串行执行，不能并行
      for script in \
        00-init-databases.sql \
        01-init-schema.sql \
        02-init-functions.sql \
        03-migration-enums.sql \
        04-migration-core-entities.sql \
        05-migration-genesis-tracking.sql \
        06-migration-tracking-logging.sql \
        07-migration-indexes-constraints.sql \
        08-migration-triggers.sql
      do
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

### 错误1：ENUM类型不存在
```
ERROR: type "agent_type" does not exist
```
**原因**: 03-migration-enums.sql 没有先执行
**解决**: 必须先执行 03-migration-enums.sql

### 错误2：表不存在
```
ERROR: relation "chapter_versions" does not exist
```
**原因**: 试图添加外键约束时表还没创建
**解决**: 检查脚本执行顺序

### 错误3：函数已存在冲突
```
ERROR: function already exists
```
**原因**: 重复执行或脚本顺序错误
**解决**: 脚本中已使用 `CREATE OR REPLACE`，检查是否有语法错误

## 🔄 回滚策略

如果迁移失败，回滚顺序应该与执行顺序相反：

1. 删除触发器
2. 删除约束和索引
3. 删除新增表
4. 恢复原表结构
5. 删除ENUM类型

**建议**: 在生产环境执行前，先在测试环境完整验证整个迁移过程。

## 📋 执行检查清单

- [ ] 确认当前数据库版本和兼容性
- [ ] 备份现有数据
- [ ] 按顺序执行所有脚本
- [ ] 验证每个脚本执行成功
- [ ] 测试关键功能
- [ ] 验证数据完整性