"""
SQLAlchemy 会话管理

提供数据库会话的创建和管理
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .engine import engine

# 创建异步会话工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后不使对象过期
    autocommit=False,
    autoflush=False,
)


async def get_sql_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话（用于 FastAPI 依赖注入）

    Yields:
        AsyncSession: 数据库会话
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def create_sql_session() -> AsyncGenerator[AsyncSession, None]:
    """
    创建数据库会话（用于非 FastAPI 场景）

    Usage:
        async with create_sql_session() as session:
            # 使用 session
            pass

    Yields:
        AsyncSession: 数据库会话
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 兼容旧的命名
get_db = get_sql_session

__all__ = [
    "async_session_maker",
    "get_sql_session",
    "create_sql_session",
    "get_db",
]
