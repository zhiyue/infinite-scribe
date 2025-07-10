"""
Neo4j 驱动管理

提供 Neo4j 数据库驱动的创建和配置
"""

from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from src.core.config import settings


def create_neo4j_driver(uri: str | None = None, auth: tuple[str, str] | None = None, **kwargs: Any) -> AsyncDriver:
    """
    创建 Neo4j 异步驱动

    Args:
        uri: Neo4j 连接 URI，默认使用配置中的 URI
        auth: 认证信息 (username, password)
        **kwargs: 其他驱动配置参数

    Returns:
        AsyncDriver: Neo4j 异步驱动
    """
    neo4j_uri = uri or settings.database.neo4j_url
    neo4j_auth = auth or (settings.database.neo4j_user, settings.database.neo4j_password)

    # 默认配置
    default_config = {
        "max_connection_lifetime": 3600,  # 1小时
        "max_connection_pool_size": 50,
        "connection_acquisition_timeout": 60,
        "connection_timeout": 30,
        "keep_alive": True,
    }

    # 合并用户提供的配置
    config = {**default_config, **kwargs}

    return AsyncGraphDatabase.driver(neo4j_uri, auth=neo4j_auth, **config)


# 创建默认驱动实例
neo4j_driver: AsyncDriver | None = None

if settings.database.neo4j_uri or settings.database.neo4j_host:
    neo4j_driver = create_neo4j_driver()


async def close_neo4j_driver() -> None:
    """关闭 Neo4j 驱动"""
    global neo4j_driver
    if neo4j_driver:
        await neo4j_driver.close()
        neo4j_driver = None


__all__ = [
    "neo4j_driver",
    "create_neo4j_driver",
    "close_neo4j_driver",
]
