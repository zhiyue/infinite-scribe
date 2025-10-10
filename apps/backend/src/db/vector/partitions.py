"""
Milvus 分区管理

负责管理 Milvus 数据库的分区创建和数据插入操作。
"""

import logging
from typing import Any

from .base import BaseMilvusManager, Collection

# 获取日志记录器
logger = logging.getLogger(__name__)


class MilvusPartitionManager(BaseMilvusManager):
    """管理Milvus分区操作的类。"""

    async def create_novel_partitions(self, collection_name: str, novel_ids: list[str]) -> bool:
        """Create partitions for each novel_id for Task 3.3."""
        try:
            if not await self._ensure_connected():
                return False

            if Collection is None:
                return self._handle_error("create partitions", ImportError("Milvus 客户端库不可用"))
            collection = Collection(collection_name)

            for novel_id in novel_ids:
                partition_name = f"partition_{novel_id}"
                if not collection.has_partition(partition_name):
                    collection.create_partition(partition_name)
                    logger.info(f"Created partition {partition_name}")
            return True
        except Exception as e:
            return self._handle_error("create partitions", e)

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
        try:
            if not await self._ensure_connected():
                return False

            if Collection is None:
                return self._handle_error("insert to partition", ImportError("Milvus 客户端库不可用"))
            collection = Collection(collection_name)
            partition = collection.partition(partition_name)

            entities = [[novel_id], [chunk_id], [content_type], [content], [embedding], [metadata], [created_at]]

            result = partition.insert(entities)
            logger.info(f"Inserted data to partition {partition_name}")
            return len(result.primary_keys) > 0
        except Exception as e:
            return self._handle_error("insert to partition", e)


# 导出的公共接口
__all__ = ["MilvusPartitionManager"]
