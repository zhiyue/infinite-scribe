"""
Milvus 集合管理

负责管理 Milvus 数据库的集合创建、验证和统计信息获取。
"""

import logging
from typing import Any, Optional

from .base import (
    COLLECTION_NAME,
    EMBEDDING_DIM,
    BaseMilvusManager,
    Collection,
    CollectionSchema,
    DataType,
    get_novel_embeddings_fields,
    utility,
)

# 获取日志记录器
logger = logging.getLogger(__name__)


class MilvusCollectionManager(BaseMilvusManager):
    """管理Milvus集合操作的类。"""

    async def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在。

        Args:
            collection_name: 集合名称

        Returns:
            True如果集合存在，False如果不存在或检查失败
        """
        try:
            if not await self._ensure_connected():
                return False
            if utility is None:
                return self._handle_error("检查集合存在性", ImportError("Milvus 客户端库不可用"))
            return utility.has_collection(collection_name)
        except Exception as e:
            return self._handle_error("检查集合存在性", e)

    def _create_collection_schema(self, description: str) -> Optional["CollectionSchema"]:
        """创建标准化的集合模式。

        Args:
            description: 集合描述

        Returns:
            配置好的集合模式对象，如果 Milvus 不可用则返回 None
        """
        if CollectionSchema is None:
            return None
        return CollectionSchema(get_novel_embeddings_fields(), description=description)

    def _get_required_fields(self) -> set[str]:
        """获取用于验证的必需字段名称集合。

        Returns:
            包含所有必需字段名称的集合
        """
        return {field.name for field in get_novel_embeddings_fields()}

    def _validate_embedding_field(self, schema) -> bool:
        """验证嵌入字段属性。

        Args:
            schema: 集合模式对象

        Returns:
            True如果嵌入字段配置正确，False如果配置错误
        """
        try:
            embedding_field = next(f for f in schema.fields if f.name == "embedding")
            if DataType is None:
                return False
            return embedding_field.dtype == DataType.FLOAT_VECTOR and embedding_field.params.get("dim") == EMBEDDING_DIM
        except (StopIteration, AttributeError):
            return False

    async def _drop_collection_if_exists(self, collection_name: str) -> None:
        """如果集合存在则删除。

        Args:
            collection_name: 要删除的集合名称
        """
        if utility.has_collection(collection_name):
            utility.drop_collection(collection_name)
            logger.info(f"已删除现有集合: {collection_name}")

    async def create_novel_embeddings_collection(self, collection_name: str = COLLECTION_NAME) -> bool:
        """创建具有标准模式的小说嵌入集合。

        Args:
            collection_name: 集合名称，默认使用COLLECTION_NAME

        Returns:
            True如果创建成功，False如果创建失败
        """
        try:
            if not await self._ensure_connected():
                return False

            await self._drop_collection_if_exists(collection_name)
            schema = self._create_collection_schema("用于语义搜索的小说嵌入集合")
            Collection(collection_name, schema)
            logger.info(f"已创建集合: {collection_name}")
            return True
        except Exception as e:
            return self._handle_error("创建集合", e)

    async def verify_novel_embeddings_schema(self, collection_name: str = COLLECTION_NAME) -> bool:
        """验证集合模式是否正确。

        Args:
            collection_name: 要验证的集合名称

        Returns:
            True如果模式验证通过，False如果验证失败
        """
        try:
            if not await self._ensure_connected():
                return False

            if not await self.collection_exists(collection_name):
                logger.error(f"集合 {collection_name} 不存在")
                return False

            if Collection is None:
                return self._handle_error("verify schema", ImportError("Milvus 客户端库不可用"))
            collection = Collection(collection_name)
            schema = collection.schema

            # 检查必需字段
            field_names = {field.name for field in schema.fields}
            missing_fields = self._get_required_fields() - field_names
            if missing_fields:
                logger.error(f"缺少必需字段: {missing_fields}")
                return False

            # Validate embedding field
            if not self._validate_embedding_field(schema):
                logger.error(f"Invalid embedding field (must be FLOAT_VECTOR with dim={EMBEDDING_DIM})")
                return False

            # Check indexes exist
            if not collection.indexes or not any(idx.field_name == "embedding" for idx in collection.indexes):
                logger.error("No index found on embedding field")
                return False

            logger.info("Schema verification passed")
            return True
        except Exception as e:
            return self._handle_error("verify schema", e)

    async def drop_collection(self, collection_name: str) -> bool:
        """Drop a collection."""
        try:
            if not await self._ensure_connected():
                return False

            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                logger.info(f"Dropped collection: {collection_name}")
            return True
        except Exception as e:
            return self._handle_error(f"drop collection {collection_name}", e)

    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get statistics about a collection."""
        try:
            if not await self._ensure_connected():
                return {"exists": False}

            if not await self.collection_exists(collection_name):
                return {"exists": False}

            if Collection is None:
                return {"exists": False, "error": "Milvus 客户端库不可用"}
            collection = Collection(collection_name)

            # 读取索引信息时个别版本可能抛出 "index not found" 异常，这里做兼容处理
            try:
                indexes = [
                    {"field": idx.field_name, "type": getattr(idx, "index_type", "unknown")}
                    for idx in collection.indexes
                ]
            except Exception:
                indexes = []

            entity_count = getattr(collection, "num_entities", 0)

            return {
                "exists": True,
                "name": collection_name,
                "description": collection.schema.description,
                "num_entities": entity_count,
                "entity_count": entity_count,  # 兼容测试断言
                "row_count": entity_count,  # 兼容测试断言
                "num_fields": len(collection.schema.fields),
                "field_names": [f.name for f in collection.schema.fields],
                "indexes": indexes,
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"exists": False, "error": str(e)}


# 导出的公共接口
__all__ = ["MilvusCollectionManager"]
