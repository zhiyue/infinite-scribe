"""
SQLAlchemy 基础定义

提供 DeclarativeBase 和 metadata 对象
"""

from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base

# 定义命名约定，用于自动生成约束名称
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# 创建 metadata 对象
metadata = MetaData(naming_convention=naming_convention)

# 创建 DeclarativeBase
Base: Any = declarative_base(metadata=metadata)

# 确保所有模型都能被 Alembic 发现
__all__ = ["Base", "metadata"]
