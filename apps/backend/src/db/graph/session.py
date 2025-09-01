"""
Neo4j 会话管理

提供 Neo4j 数据库会话的创建和管理
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from neo4j import AsyncSession, Query

from .driver import neo4j_driver


async def get_neo4j_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取 Neo4j 会话（用于 FastAPI 依赖注入）

    Yields:
        AsyncSession: Neo4j 会话
    """
    if not neo4j_driver:
        raise RuntimeError("Neo4j driver not initialized")

    async with neo4j_driver.session() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def create_neo4j_session(
    database: str | None = None, fetch_size: int = 1000, **kwargs: Any
) -> AsyncGenerator[AsyncSession, None]:
    """
    创建 Neo4j 会话（用于非 FastAPI 场景）

    Args:
        database: 数据库名称，默认使用默认数据库
        fetch_size: 批量获取大小
        **kwargs: 其他会话配置参数

    Usage:
        async with create_neo4j_session() as session:
            result = await session.run("MATCH (n) RETURN n LIMIT 10")
            records = await result.data()

    Yields:
        AsyncSession: Neo4j 会话
    """
    if not neo4j_driver:
        raise RuntimeError("Neo4j driver not initialized")

    session_config = {"database": database, "fetch_size": fetch_size, **kwargs}

    async with neo4j_driver.session(**session_config) as session:
        try:
            yield session
        finally:
            await session.close()


async def execute_query(
    query: str, parameters: dict[str, Any] | None = None, database: str | None = None
) -> list[dict[str, Any]]:
    """
    执行 Neo4j 查询并返回结果

    Args:
        query: Cypher 查询语句
        parameters: 查询参数
        database: 数据库名称

    Returns:
        查询结果列表
    """
    async with create_neo4j_session(database=database) as session:
        # Neo4j type stubs expect LiteralString, but we need dynamic queries
        cypher_query = Query(query, parameters or {})  # pyright: ignore
        result = await session.run(cypher_query)
        return await result.data()


__all__ = [
    "get_neo4j_session",
    "create_neo4j_session",
    "execute_query",
]
