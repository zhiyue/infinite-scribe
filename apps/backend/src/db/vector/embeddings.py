"""
Milvus 嵌入管理

负责管理 Milvus 中小说嵌入的插入、搜索和批量操作。
"""

import logging
import time
from typing import Any

from .base import COLLECTION_NAME, EMBEDDING_DIM, HNSW_EF_SEARCH, Collection

# 获取日志记录器
logger = logging.getLogger(__name__)


class MilvusEmbeddingManager:
    """用于管理Milvus中小说嵌入的辅助类。"""

    def __init__(self, schema_manager):
        """初始化嵌入管理器。

        Args:
            schema_manager: Milvus模式管理器实例（包含连接管理功能）
        """
        self.schema_manager = schema_manager

    def _validate_embedding_dimension(self, embedding: list[float]) -> None:
        """验证嵌入向量维度。

        Args:
            embedding: 嵌入向量

        Raises:
            ValueError: 如果维度不匹配
        """
        if len(embedding) != EMBEDDING_DIM:
            raise ValueError(f"嵌入向量必须是{EMBEDDING_DIM}维，但得到了{len(embedding)}维")

    def _format_search_results(self, search_results) -> list[dict[str, Any]]:
        """将搜索结果格式化为标准字典格式。

        Args:
            search_results: Milvus搜索结果

        Returns:
            格式化后的搜索结果列表
        """
        results = []
        if search_results and len(search_results[0]) > 0:
            for result in search_results[0]:
                results.append(
                    {
                        "id": result.id,  # 记录ID
                        "score": result.distance,  # 相似度评分
                        "novel_id": result.entity.get("novel_id"),  # 小说ID
                        "chunk_id": result.entity.get("chunk_id"),  # 文本块ID
                        "content_type": result.entity.get("content_type"),  # 内容类型
                        "content": result.entity.get("content"),  # 文本内容
                        "metadata": result.entity.get("metadata"),  # 元数据
                    }
                )
        return results

    def _build_search_filter(self, novel_id: str | None, content_type: str | None) -> str | None:
        """构建搜索过滤表达式。

        Args:
            novel_id: 小说ID（可选）
            content_type: 内容类型（可选）

        Returns:
            过滤表达式字符串，如果没有过滤条件则返回None
        """
        if novel_id and content_type:
            return f'novel_id == "{novel_id}" && content_type == "{content_type}"'
        elif novel_id:
            return f'novel_id == "{novel_id}"'
        elif content_type:
            return f'content_type == "{content_type}"'
        return None

    async def insert_novel_embedding(
        self,
        novel_id: str,
        chunk_id: str,
        content_type: str,
        content: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
        collection_name: str = COLLECTION_NAME,
    ) -> bool:
        """插入单个小说嵌入。

        Args:
            novel_id: 小说ID
            chunk_id: 文本块ID
            content_type: 内容类型
            content: 文本内容
            embedding: 向量嵌入
            metadata: 元数据（可选）
            collection_name: 集合名称

        Returns:
            True如果插入成功，False如果插入失败
        """
        try:
            if not await self.schema_manager._ensure_connected():
                return False

            self._validate_embedding_dimension(embedding)
            if Collection is None:
                return self.schema_manager._handle_error("插入嵌入", ImportError("Milvus 客户端库不可用"))
            collection = Collection(collection_name)

            entities = [
                [novel_id],
                [chunk_id],
                [content_type],
                [content],
                [embedding],
                [metadata or {}],
                [int(time.time())],
            ]

            result = collection.insert(entities)
            logger.info(f"为小说{novel_id}的{content_type}内容插入了嵌入")
            return len(result.primary_keys) > 0
        except Exception as e:
            return self.schema_manager._handle_error("插入嵌入", e)

    async def search_similar_content(
        self,
        query_embedding: list[float],
        novel_id: str | None = None,
        content_type: str | None = None,
        limit: int = 10,
        collection_name: str = COLLECTION_NAME,
    ) -> list[dict[str, Any]]:
        """使用向量相似度搜索相似内容（传统IP方法）。

        Args:
            query_embedding: 查询向量嵌入
            novel_id: 小说ID过滤（可选）
            content_type: 内容类型过滤（可选）
            limit: 返回结果数量限制
            collection_name: 集合名称

        Returns:
            相似内容结果列表
        """
        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        return await self._search_similar_content(
            collection_name, query_embedding, search_params, novel_id, content_type, limit
        )

    async def _search_similar_content(
        self,
        collection_name: str,
        query_embedding: list[float],
        search_params: dict,
        novel_id: str | None,
        content_type: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """IP和COSINE方法的通用搜索实现。

        Args:
            collection_name: 集合名称
            query_embedding: 查询向量嵌入
            search_params: 搜索参数配置
            novel_id: 小说ID过滤（可选）
            content_type: 内容类型过滤（可选）
            limit: 返回结果数量限制

        Returns:
            相似内容结果列表
        """
        try:
            if not await self.schema_manager._ensure_connected():
                return []

            if Collection is None:
                logger.error("搜索相似内容失败: Milvus 客户端库不可用")
                return []
            collection = Collection(collection_name)

            search_results = collection.search(
                data=[query_embedding],
                anns_field="embedding",  # 向量字段名
                param=search_params,  # 搜索参数
                limit=limit,  # 结果数量限制
                output_fields=["novel_id", "chunk_id", "content_type", "content", "metadata"],  # 输出字段
                expr=self._build_search_filter(novel_id, content_type),  # 过滤表达式
            )

            results = self._format_search_results(search_results)
            logger.info(f"找到{len(results)}个相似内容项")
            return results
        except Exception as e:
            logger.error(f"搜索相似内容失败: {e}")
            return []

    async def batch_insert_embeddings(self, collection_name: str, data_list: list[dict]) -> bool:
        """Batch insert embeddings for performance optimization (Task 3.4)."""
        try:
            if not await self.schema_manager._ensure_connected():
                return False

            if Collection is None:
                return self.schema_manager._handle_error(
                    "batch insert embeddings", ImportError("Milvus 客户端库不可用")
                )
            collection = Collection(collection_name)

            # Validate all embeddings first
            for item in data_list:
                self._validate_embedding_dimension(item["embedding"])

            # Prepare batch data by field
            entities = [
                [item["novel_id"] for item in data_list],
                [item["chunk_id"] for item in data_list],
                [item["content_type"] for item in data_list],
                [item["content"] for item in data_list],
                [item["embedding"] for item in data_list],
                [item["metadata"] for item in data_list],
                [item["created_at"] for item in data_list],
            ]

            result = collection.insert(entities)
            logger.info(f"Batch inserted {len(data_list)} embeddings to {collection_name}")
            return len(result.primary_keys) == len(data_list)
        except Exception as e:
            return self.schema_manager._handle_error("batch insert embeddings", e)

    async def search_similar_content_optimized(
        self,
        collection_name: str,
        query_embedding: list[float],
        novel_id: str | None = None,
        content_type: str | None = None,
        limit: int = 10,
        ef: int = HNSW_EF_SEARCH,
    ) -> list[dict[str, Any]]:
        """Optimized vector similarity search with HNSW parameters (Task 3.4)."""
        search_params = {"metric_type": "COSINE", "params": {"ef": ef}}
        return await self._search_similar_content(
            collection_name, query_embedding, search_params, novel_id, content_type, limit
        )


# 导出的公共接口
__all__ = ["MilvusEmbeddingManager"]
