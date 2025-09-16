"""
SQLAlchemy 会话管理

提供数据库会话的创建和管理
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .engine import get_engine

# 创建异步会话工厂（延迟初始化）
async_session_maker = None

def get_session_maker():
    """获取会话工厂，延迟初始化以确保在异步上下文中创建"""
    global async_session_maker
    if async_session_maker is None:
        # 使用延迟加载的引擎
        engine = get_engine()
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # 提交后不使对象过期
            autocommit=False,
            autoflush=False,
        )
    return async_session_maker


async def get_sql_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话（用于 FastAPI 依赖注入）

    Yields:
        AsyncSession: 数据库会话
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
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
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 兼容旧的命名


@asynccontextmanager
async def transactional(db: AsyncSession) -> AsyncGenerator[None, None]:
    """
    事务上下文管理器，自动处理嵌套事务和普通事务

    当会话已经在事务中时，使用嵌套事务(savepoint)
    否则，使用常规事务

    Usage:
        async with transactional(db):
            # 在事务中执行操作
            await repository.create(...)
            await repository.update(...)
            # 自动提交或回滚

    Args:
        db: 数据库会话

    Yields:
        None
    """
    if db.in_transaction():
        # 已在事务中，使用嵌套事务(savepoint)
        async with db.begin_nested():
            yield
    else:
        # 不在事务中，使用常规事务
        async with db.begin():
            yield


get_db = get_sql_session

__all__ = [
    "get_session_maker",
    "get_sql_session",
    "create_sql_session",
    "transactional",
    "get_db",
]
