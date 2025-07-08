# Alembic 迁移策略

## 背景

项目的数据库表分为两种管理方式：

1. **现有表**：通过 `infrastructure/docker/init/postgres/` 中的 SQL 文件创建
   - 包括：novels, chapters, characters, domain_events, async_tasks 等核心业务表
   - 这些表在 Docker 容器初始化时自动创建

2. **新表**：通过 Alembic 迁移管理
   - 包括：users, sessions, email_verifications 等认证相关表
   - 以及未来添加的所有新表

## 设置步骤

### 1. 标记基线迁移

基线迁移已创建（`a0b8ded1720f_initial_migration_existing_schema_.py`），需要手动标记为已应用：

```bash
# 在开发数据库中
cd apps/backend

# 创建 alembic_version 表（如果不存在）
uv run alembic stamp head

# 或者直接 SQL（如果上面的命令有问题）
psql -h 192.168.2.201 -U postgres -d infinite_scribe -c "
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version (version_num) VALUES ('a0b8ded1720f');
"
```

### 2. 创建新表的迁移

现在可以为新表创建迁移：

```bash
# 1. 在 src/models/ 中创建新的 SQLAlchemy 模型
# 2. 在 alembic/env.py 中导入新模型
# 3. 生成迁移
uv run alembic revision --autogenerate -m "Add new_table_name"

# 4. 检查生成的迁移文件，确保只包含新表
# 5. 应用迁移
uv run alembic upgrade head
```

## 注意事项

### 避免修改现有表

如果需要修改通过 SQL 文件创建的表：

1. **不推荐**：通过 Alembic 迁移修改
2. **推荐**：更新 SQL 文件并重新初始化数据库

### 处理表冲突

如果 Alembic 检测到现有表的更改：

1. 检查 SQLAlchemy 模型是否意外包含了现有表
2. 确保 env.py 中只导入需要 Alembic 管理的模型
3. 手动编辑迁移文件，删除对现有表的修改

### 配置 Alembic 忽略特定表

可以在 env.py 中配置忽略特定表：

```python
def include_object(object, name, type_, reflected, compare_to):
    """决定是否包含对象在自动生成中"""
    # 忽略通过 SQL 文件创建的表
    if type_ == "table" and name in [
        'novels', 'chapters', 'characters', 'domain_events',
        'async_tasks', 'command_inbox', 'event_outbox',
        # ... 其他现有表
    ]:
        return False
    return True

# 在 context.configure 中添加
context.configure(
    # ... 其他参数
    include_object=include_object,
)
```

## 示例：创建新的评论表

```python
# 1. 创建模型文件 src/models/comment.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from src.models.base import BaseModel

class Comment(BaseModel):
    __tablename__ = "comments"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    novel_id = Column(String(36), nullable=False)
    chapter_id = Column(String(36), nullable=True)
    content = Column(Text, nullable=False)
    
# 2. 在 alembic/env.py 中导入
from src.models.comment import Comment  # noqa: F401

# 3. 生成迁移
uv run alembic revision --autogenerate -m "Add comments table"

# 4. 应用迁移
uv run alembic upgrade head
```

## 常见问题

### Q: 如何查看当前迁移状态？
```bash
uv run alembic current
```

### Q: 如何查看迁移历史？
```bash
uv run alembic history
```

### Q: 如何回滚迁移？
```bash
# 回滚到上一个版本
uv run alembic downgrade -1

# 回滚到特定版本
uv run alembic downgrade <revision>
```

### Q: 如何处理迁移冲突？
如果多个开发者同时创建迁移，可能会有冲突：

```bash
# 1. 合并代码后，检查是否有多个 head
uv run alembic heads

# 2. 如果有多个 head，创建合并迁移
uv run alembic merge -m "Merge migrations"
```

## 最佳实践

1. **总是检查自动生成的迁移**：确保没有意外修改现有表
2. **小步迁移**：每次只做一个逻辑更改
3. **测试迁移**：在开发环境测试后再应用到生产
4. **备份数据**：在应用重要迁移前备份数据库
5. **文档化**：在迁移文件中添加详细注释