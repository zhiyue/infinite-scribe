"""
Milvus 向量数据库模式管理

负责管理 Milvus 数据库的模式创建、集合和索引，
专门用于小说生成系统的向量嵌入存储和检索。
"""

import logging
from typing import Any

from .base import COLLECTION_NAME, BaseMilvusManager
from .collections import MilvusCollectionManager
from .embeddings import MilvusEmbeddingManager
from .indexes import MilvusIndexManager
from .partitions import MilvusPartitionManager

# 获取日志记录器
logger = logging.getLogger(__name__)


class MilvusSchemaManager(BaseMilvusManager):
    """管理Milvus模式创建和验证的类，专门用于小说嵌入。"""

    def __init__(self, host: str = "localhost", port: str = "19530"):
        """初始化Milvus模式管理器。

        Args:
            host: Milvus服务器主机地址
            port: Milvus服务器端口号
        """
        super().__init__(host, port)

        # 初始化专门的管理器，它们共享同样的连接配置
        self._collection_manager = MilvusCollectionManager(host, port)
        self._index_manager = MilvusIndexManager(host, port)
        self._partition_manager = MilvusPartitionManager(host, port)

    async def connect(self) -> bool:
        """连接到Milvus服务器，并同步所有管理器的连接状态。"""
        result = await super().connect()
        if result:
            # 同步连接状态到所有子管理器
            self._collection_manager._connected = True
            self._index_manager._connected = True
            self._partition_manager._connected = True
        return result

    async def disconnect(self) -> None:
        """断开与Milvus服务器的连接，并同步所有管理器的连接状态。"""
        await super().disconnect()
        # 同步连接状态到所有子管理器
        self._collection_manager._connected = False
        self._index_manager._connected = False
        self._partition_manager._connected = False

    # Collection operations - delegate to collection manager
    async def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在。"""
        return await self._collection_manager.collection_exists(collection_name)

    async def create_novel_embeddings_collection(self, collection_name: str = COLLECTION_NAME) -> bool:
        """创建具有标准模式的小说嵌入集合。"""
        return await self._collection_manager.create_novel_embeddings_collection(collection_name)

    async def verify_novel_embeddings_schema(self, collection_name: str = COLLECTION_NAME) -> bool:
        """验证集合模式是否正确。"""
        return await self._collection_manager.verify_novel_embeddings_schema(collection_name)

    async def drop_collection(self, collection_name: str) -> bool:
        """Drop a collection."""
        return await self._collection_manager.drop_collection(collection_name)

    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get statistics about a collection."""
        return await self._collection_manager.get_collection_stats(collection_name)

    # Index operations - delegate to index manager
    async def create_novel_embeddings_index(self, collection_name: str = COLLECTION_NAME) -> bool:
        """为指定集合创建基础向量索引（IVF_FLAT）。"""
        return await self._index_manager.create_novel_embeddings_index(collection_name)

    async def create_hnsw_index_optimized(
        self,
        collection_name: str,
        field_name: str = "embedding",
        m: int = 32,
        ef_construction: int = 200,
        metric_type: str = "COSINE",
    ) -> bool:
        """Create HNSW index with optimized parameters for Task 3.2."""
        return await self._index_manager.create_hnsw_index_optimized(
            collection_name, field_name, m, ef_construction, metric_type
        )

    # Partition operations - delegate to partition manager
    async def create_novel_partitions(self, collection_name: str, novel_ids: list[str]) -> bool:
        """Create partitions for each novel_id for Task 3.3."""
        return await self._partition_manager.create_novel_partitions(collection_name, novel_ids)

    async def insert_to_partition(
        self,
        collection_name: str,
        partition_name: str,
        novel_id: str,
        chunk_id: str,
        content_type: str,
        content: str,
        embedding: list[float],
        metadata: dict[str, Any],
        created_at: int,
    ) -> bool:
        """Insert data to a specific partition."""
        return await self._partition_manager.insert_to_partition(
            collection_name, partition_name, novel_id, chunk_id, content_type, content, embedding, metadata, created_at
        )

    # Coordinated operations
    async def initialize_novel_embeddings(self, collection_name: str = COLLECTION_NAME, use_hnsw: bool = True) -> bool:
        """Initialize complete novel embeddings setup."""
        logger.info("Initializing Milvus novel embeddings schema...")

        try:
            # Setup collection and index
            steps = [
                self.connect(),
                self.create_novel_embeddings_collection(collection_name),
                self.create_hnsw_index_optimized(collection_name)
                if use_hnsw
                else self.create_novel_embeddings_index(collection_name),
                self.verify_novel_embeddings_schema(collection_name),
            ]

            for step in steps:
                if not await step:
                    return False

            logger.info("Milvus initialization completed successfully")
            return True
        except Exception as e:
            return self._handle_error("initialize novel embeddings", e)


# 导出的公共接口
__all__ = ["MilvusSchemaManager", "MilvusEmbeddingManager"]
