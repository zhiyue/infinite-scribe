"""
SQLAlchemy 引擎管理

提供数据库引擎的创建和配置
"""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from src.core.config import settings


def create_engine(
    url: str | None = None,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_pre_ping: bool = True,
    pool_recycle: int = 3600,
) -> AsyncEngine:
    """
    创建异步数据库引擎

    Args:
        url: 数据库连接 URL，默认使用配置中的 URL
        echo: 是否打印 SQL 语句
        pool_size: 连接池大小
        max_overflow: 连接池最大溢出数
        pool_pre_ping: 是否在使用连接前检查连接有效性
        pool_recycle: 连接回收时间（秒）

    Returns:
        AsyncEngine: 异步数据库引擎
    """
    database_url = url or settings.POSTGRES_URL

    # 根据环境选择连接池策略
    if getattr(settings, "ENVIRONMENT", "production") == "test":
        # 测试环境使用 NullPool，避免连接池问题
        return create_async_engine(
            database_url,
            echo=echo,
            poolclass=NullPool,
        )
    else:
        # 生产环境使用连接池
        return create_async_engine(
            database_url,
            echo=echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=pool_pre_ping,
            pool_recycle=pool_recycle,
            poolclass=AsyncAdaptedQueuePool,
        )


# 创建默认引擎实例
engine = create_engine()

__all__ = ["engine", "create_engine"]
