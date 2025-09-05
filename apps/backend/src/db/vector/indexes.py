"""
Milvus 索引管理

负责管理 Milvus 数据库的索引创建和优化配置。
"""

import logging

from .base import (
    COLLECTION_NAME,
    HNSW_EF_CONSTRUCTION,
    HNSW_M,
    BaseMilvusManager,
    Collection,
)

# 获取日志记录器
logger = logging.getLogger(__name__)


class MilvusIndexManager(BaseMilvusManager):
    """管理Milvus索引操作的类。"""

    async def _create_index(self, collection_name: str, field_name: str, index_params: dict) -> bool:
        """通用索引创建方法。

        Args:
            collection_name: 集合名称
            field_name: 要创建索引的字段名称
            index_params: 索引参数配置

        Returns:
            True如果索引创建成功，False如果创建失败
        """
        try:
            if not await self._ensure_connected():
                return False

            if Collection is None:
                return self._handle_error("创建索引", ImportError("Milvus 客户端库不可用"))
            collection = Collection(collection_name)
            collection.create_index(field_name, index_params)
            logger.info(f"为{collection_name}创建了{index_params['index_type']}索引")
            return True
        except Exception as e:
            return self._handle_error("创建索引", e)

    async def create_novel_embeddings_index(self, collection_name: str = COLLECTION_NAME) -> bool:
        """为指定集合创建基础向量索引（IVF_FLAT）。

        注意：此前实现错误地固定为默认集合名，导致测试集中创建索引失败。
        现修复为尊重调用方传入的 `collection_name`。

        Args:
            collection_name: 需要创建索引的集合名称

        Returns:
            True如果索引创建成功，False如果创建失败
        """
        try:
            if not await self._ensure_connected():
                return False

            if Collection is None:
                return self._handle_error("创建向量索引", ImportError("Milvus 客户端库不可用"))
            collection = Collection(collection_name)

            index_params = {
                "metric_type": "IP",  # 余弦相似度（通过内积归一化实现）
                "index_type": "IVF_FLAT",  # 基础倒排索引，构建快、兼容性好
                "params": {"nlist": 128},
            }

            collection.create_index("embedding", index_params)
            logger.info(f"为 {collection_name} 创建了 IVF_FLAT 向量索引")
            return True
        except Exception as e:
            return self._handle_error("创建向量索引", e)

    async def create_hnsw_index_optimized(
        self,
        collection_name: str,
        field_name: str = "embedding",
        m: int = HNSW_M,
        ef_construction: int = HNSW_EF_CONSTRUCTION,
        metric_type: str = "COSINE",
    ) -> bool:
        """Create HNSW index with optimized parameters for Task 3.2."""
        index_params = {
            "metric_type": metric_type,
            "index_type": "HNSW",
            "params": {"M": m, "efConstruction": ef_construction},
        }
        return await self._create_index(collection_name, field_name, index_params)


# 导出的公共接口
__all__ = ["MilvusIndexManager"]
