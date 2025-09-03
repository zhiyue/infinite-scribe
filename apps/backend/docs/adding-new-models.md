# 添加新数据库模型指南

本指南详细说明在 InfiniteScribe 后端如何添加新的 SQLAlchemy 模型和生成数据库迁移。

## 📋 概述

InfiniteScribe 使用 **SQLAlchemy + Alembic** 进行数据库模型管理：
- **SQLAlchemy**: ORM 模型定义
- **Alembic**: 数据库迁移管理
- **统一管理**: 所有模型通过 `src/models/__init__.py` 集中导入

## 🚀 快速步骤

### 1. 创建模型文件
在 `src/models/` 目录下创建新的模型文件：

```python
# src/models/my_model.py
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from src.models.base import BaseModel

class MyModel(BaseModel):
    """我的新模型描述"""
    
    __tablename__ = "my_models"
    __table_args__ = {'comment': '我的新模型表'}

    # 字段定义
    id = Column(Integer, primary_key=True, comment="主键ID")
    name = Column(String(255), nullable=False, comment="名称")
    description = Column(Text, nullable=True, comment="描述")
    
    # 外键关系（如需要）
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    
    # 关系定义（如需要）
    user = relationship("User", back_populates="my_models")

    def __repr__(self):
        return f"<MyModel(id={self.id}, name='{self.name}')>"
```

### 2. 注册到模型包
在 `src/models/__init__.py` 中添加导入：

```python
# src/models/__init__.py

# 添加新模型导入
from src.models.my_model import MyModel  # 添加这行

__all__ = [
    # ... 现有模型
    "MyModel",  # 添加到导出列表
]
```

### 3. 更新相关模型（如有关系）
如果新模型与现有模型有关系，更新现有模型：

```python
# src/models/user.py
class User(BaseModel):
    # ... 现有字段
    
    # 添加反向关系
    my_models = relationship("MyModel", back_populates="user")
```

### 4. 生成数据库迁移
```bash
cd apps/backend

# 生成迁移文件
uv run alembic revision --autogenerate -m "Add MyModel table"

# 检查生成的迁移文件
cat alembic/versions/最新文件.py
```

### 5. 应用迁移
```bash
# 应用迁移到数据库
uv run alembic upgrade head

# 验证迁移状态
uv run alembic current
```

## 📚 详细说明

### 模型定义最佳实践

#### 1. 继承基础模型
```python
from src.models.base import BaseModel

class MyModel(BaseModel):  # 继承 BaseModel
    # BaseModel 提供：id, created_at, updated_at
    pass
```

#### 2. 表名和注释
```python
class MyModel(BaseModel):
    __tablename__ = "my_models"  # 使用复数、下划线命名
    __table_args__ = {'comment': '详细的表描述'}
```

#### 3. 字段定义规范
```python
# 主键（BaseModel 已提供，通常不需要重复定义）
id = Column(Integer, primary_key=True, comment="主键ID")

# 必需字段
name = Column(String(255), nullable=False, comment="名称")

# 可选字段
description = Column(Text, nullable=True, comment="描述")

# 外键
user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")

# 枚举字段
status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.ACTIVE, comment="状态")

# JSON 字段
metadata = Column(JSON, nullable=True, comment="元数据")

# 时间戳（BaseModel 已提供 created_at, updated_at）
published_at = Column(DateTime(timezone=True), nullable=True, comment="发布时间")
```

#### 4. 关系定义
```python
# 一对多关系
class User(BaseModel):
    novels = relationship("Novel", back_populates="author")

class Novel(BaseModel):
    user_id = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="novels")

# 多对多关系
class Novel(BaseModel):
    tags = relationship("Tag", secondary="novel_tags", back_populates="novels")

class Tag(BaseModel):
    novels = relationship("Novel", secondary="novel_tags", back_populates="tags")
```

### 枚举类型处理
```python
from enum import Enum as PyEnum
from sqlalchemy import Enum

class StatusEnum(PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"

class MyModel(BaseModel):
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.ACTIVE)
```

## 🔍 验证新模型

### 1. 检查模型注册
```python
# 在 Python shell 中验证
cd apps/backend
uv run python -c "
from src.models import MyModel
from src.db.sql.base import Base
print('MyModel 表:', MyModel.__table__)
print('所有表:', list(Base.metadata.tables.keys()))
"
```

### 2. 验证迁移生成
```bash
# 生成测试迁移（不应该有变化）
uv run alembic revision --autogenerate -m "Test - should be empty"
# 如果没有变化，删除生成的空迁移文件
```

### 3. 验证数据库表结构
```sql
-- 连接数据库查看表结构
\d my_models
\d+ my_models  -- 包含注释
```

## 📝 Schema 定义（可选）

如果需要 API 序列化，创建对应的 Pydantic schema：

```python
# src/schemas/my_model/read.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MyModelRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# src/schemas/my_model/create.py
class MyModelCreate(BaseModel):
    name: str
    description: Optional[str] = None

# src/schemas/my_model/update.py  
class MyModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
```

## ⚠️ 常见问题与解决

### 问题 1: 模型未被 Alembic 发现
**症状**: 运行 `alembic revision --autogenerate` 没有生成迁移
**解决**: 
1. 检查模型是否在 `src/models/__init__.py` 中导入
2. 检查模型是否继承了 `BaseModel` 或 `Base`
3. 重启 Python 环境

### 问题 2: 外键关系错误
**症状**: 迁移失败或关系查询异常
**解决**:
1. 确保外键表名正确（复数形式）
2. 检查 `relationship` 的 `back_populates` 参数一致
3. 验证外键约束的 `ondelete` 和 `onupdate` 设置

### 问题 3: 字段类型不匹配
**症状**: 数据库字段类型与预期不符
**解决**:
1. 检查 SQLAlchemy 类型定义
2. 查看生成的迁移文件中的字段类型
3. 手动修改迁移文件中的字段类型（如需要）

### 问题 4: 迁移冲突
**症状**: `alembic upgrade` 失败
**解决**:
1. 检查数据库当前状态：`uv run alembic current`
2. 查看迁移历史：`uv run alembic history`
3. 手动解决冲突或回滚到安全状态

## 🔧 高级用法

### 自定义迁移
有时需要手动编写迁移逻辑：

```python
# alembic/versions/xxx_custom_migration.py
def upgrade() -> None:
    """升级数据库"""
    # 自动生成的表结构变更
    op.create_table('my_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        # ...
    )
    
    # 自定义数据迁移逻辑
    connection = op.get_bind()
    connection.execute(text("""
        INSERT INTO my_models (name, description) 
        SELECT title, content FROM old_table;
    """))

def downgrade() -> None:
    """回滚数据库"""
    op.drop_table('my_models')
```

### 索引和约束
```python
class MyModel(BaseModel):
    __tablename__ = "my_models"
    __table_args__ = (
        Index('idx_my_model_name_status', 'name', 'status'),  # 复合索引
        UniqueConstraint('name', 'user_id', name='uq_my_model_name_user'),  # 唯一约束
        CheckConstraint('length(name) > 0', name='ck_my_model_name_not_empty'),  # 检查约束
        {'comment': '我的模型表'}
    )
```

## ✅ 检查清单

新增模型完成后，请确认：

- [ ] 模型文件已创建在 `src/models/`
- [ ] 模型已在 `src/models/__init__.py` 中导入和导出
- [ ] 模型继承了 `BaseModel`
- [ ] 表名使用复数下划线命名
- [ ] 所有字段都有适当的注释
- [ ] 外键关系正确定义
- [ ] 迁移文件已生成并检查
- [ ] 迁移已应用到数据库
- [ ] 相关 Schema 已创建（如需要）
- [ ] 测试了基本的增删改查操作

## 📖 相关文档

- [SQLAlchemy ORM 文档](https://docs.sqlalchemy.org/en/20/orm/)
- [Alembic 迁移文档](https://alembic.sqlalchemy.org/en/latest/)
- [项目后端架构说明](../CLAUDE.md)
- [数据库设计规范](./database-design-guidelines.md)

---

遇到问题？查看 [故障排除指南](../CLAUDE.md#故障排除) 或在项目中提 Issue。