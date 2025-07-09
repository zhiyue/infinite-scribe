"""
数据库会话管理 - 兼容层

此文件保留用于向后兼容，新代码应该使用 src.db 模块
"""

from src.db.sql import Base, async_session_maker, engine
from src.db.sql.session import get_sql_session as get_db


async def init_db() -> None:
    """初始化数据库（创建表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库连接"""
    await engine.dispose()


# 导出向后兼容的接口
__all__ = [
    "Base",
    "engine",
    "async_session_maker",
    "get_db",
    "init_db",
    "close_db",
]
