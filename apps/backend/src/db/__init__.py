"""
统一数据层 - 提供多种数据存储的访问接口

支持的数据存储:
- SQL (PostgreSQL) - 关系型数据
- Graph (Neo4j) - 图数据
- Vector (Milvus/Qdrant) - 向量数据
"""

# SQL 数据库
from .graph.driver import neo4j_driver

# Graph 数据库 (Neo4j)
from .graph.session import get_neo4j_session
from .sql.base import Base, metadata
from .sql.engine import create_engine, engine
from .sql.session import async_session_maker, get_sql_session

# Vector 数据库 (预留接口)
# from .vector.client import get_vector_client

__all__ = [
    # SQL
    "get_sql_session",
    "async_session_maker",
    "Base",
    "metadata",
    "engine",
    "create_engine",
    # Graph
    "get_neo4j_session",
    "neo4j_driver",
]
