"""
Milvus 向量数据库模式管理

负责管理 Milvus 数据库的模式创建、集合和索引，
专门用于小说生成系统的向量嵌入存储和检索。
"""

import logging
import time
from typing import Any

try:
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
except ImportError:
    # 当 Milvus 不可用时的优雅降级处理
    Collection = CollectionSchema = DataType = FieldSchema = connections = utility = None

# 获取日志记录器
logger = logging.getLogger(__name__)

# 常量配置
COLLECTION_NAME = "novel_embeddings_v1"  # 默认集合名称
EMBEDDING_DIM = 768  # 向量嵌入维度（与BERT模型对应）
HNSW_M = 32  # HNSW 索引参数：每个节点的最大连接数
HNSW_EF_CONSTRUCTION = 200  # HNSW 索引构建时的候选列表大小
HNSW_EF_SEARCH = 64  # HNSW 搜索时的候选列表大小


# 模式定义 - 集中管理以避免重复
def _get_novel_embeddings_fields():
    """获取小说嵌入字段模式 - 延迟导入以避免导入错误。"""
    if FieldSchema is None or DataType is None:
        raise ImportError("Milvus 客户端库不可用")

    return [
        # 主键ID字段，自动生成
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        # 小说ID，用于关联特定小说
        FieldSchema(name="novel_id", dtype=DataType.VARCHAR, max_length=100),
        # 文本块ID，用于标识小说中的具体片段
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100),
        # 内容类型，如"plot"、"character"、"scene"等
        FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=50),
        # 实际文本内容，最多8192字符
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
        # 768维浮点向量嵌入
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        # 额外元数据，以JSON格式存储
        FieldSchema(name="metadata", dtype=DataType.JSON),
        # 创建时间戳（Unix时间戳）
        FieldSchema(name="created_at", dtype=DataType.INT64),
    ]


class MilvusSchemaManager:
    """管理Milvus模式创建和验证的类，专门用于小说嵌入。"""

    def __init__(self, host: str = "localhost", port: str = "19530"):
        """初始化Milvus模式管理器。

        Args:
            host: Milvus服务器主机地址
            port: Milvus服务器端口号
        """
        self.host = host
        self.port = port
        self.connection_alias = "default"  # 连接别名
        self._connected = False  # 连接状态标志
        self._check_pymilvus_available()  # 检查pymilvus库可用性

    def _check_pymilvus_available(self) -> None:
        """检查pymilvus库是否可用。"""
        if connections is None:
            raise ImportError("Milvus 客户端库不可用")

    def _handle_error(self, operation: str, error: Exception) -> bool:
        """标准化错误处理。

        Args:
            operation: 操作名称
            error: 异常对象

        Returns:
            始终返回False表示操作失败
        """
        logger.error(f"操作失败 {operation}: {error}")
        return False

    async def _ensure_connected(self) -> bool:
        """确保连接存在，如需要则连接。

        Returns:
            True如果连接成功，False如果连接失败
        """
        if not self._connected:
            return await self.connect()
        return True

    async def connect(self) -> bool:
        """连接到Milvus服务器。

        Returns:
            True如果连接成功，False如果连接失败
        """
        try:
            connections.connect(alias=self.connection_alias, host=self.host, port=self.port)
            self._connected = True
            logger.info(f"已连接到Milvus服务器 {self.host}:{self.port}")
            return True
        except Exception as e:
            return self._handle_error("连接", e)

    async def disconnect(self) -> None:
        """断开与Milvus服务器的连接。"""
        try:
            if self._connected:
                connections.disconnect(self.connection_alias)
                self._connected = False
                logger.info("已断开Milvus连接")
        except Exception as e:
            logger.warning(f"断开连接时出错: {e}")

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
            return utility.has_collection(collection_name)
        except Exception as e:
            return self._handle_error("检查集合存在性", e)

    def _create_collection_schema(self, description: str) -> CollectionSchema:
        """创建标准化的集合模式。

        Args:
            description: 集合描述

        Returns:
            配置好的集合模式对象
        """
        return CollectionSchema(_get_novel_embeddings_fields(), description=description)

    def _get_required_fields(self) -> set[str]:
        """获取用于验证的必需字段名称集合。

        Returns:
            包含所有必需字段名称的集合
        """
        return {field.name for field in _get_novel_embeddings_fields()}

    def _validate_embedding_field(self, schema) -> bool:
        """验证嵌入字段属性。

        Args:
            schema: 集合模式对象

        Returns:
            True如果嵌入字段配置正确，False如果配置错误
        """
        try:
            embedding_field = next(f for f in schema.fields if f.name == "embedding")
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

            collection = Collection(collection_name)
            collection.create_index(field_name, index_params)
            logger.info(f"为{collection_name}创建了{index_params['index_type']}索引")
            return True
        except Exception as e:
            return self._handle_error("创建索引", e)

    async def create_novel_embeddings_index(self, collection_name: str = COLLECTION_NAME) -> bool:
        """为小说嵌入集合创建向量索引。

        Args:
            collection_name: 集合名称

        Returns:
            True如果索引创建成功，False如果创建失败
        """
        try:
            from pymilvus import Collection

            if not self._connected:
                await self.connect()

            collection_name = "novel_embeddings_v1"
            collection = Collection(collection_name)

            # 为768维向量创建IVF_FLAT索引
            # 使用内积（Inner Product）度量进行余弦相似度搜索
            index_params = {
                "metric_type": "IP",  # 内积，用于余弦相似度计算
                "index_type": "IVF_FLAT",  # 倒排文件平坐索引
                "params": {"nlist": 128},  # 聚类单元数量
            }

            collection.create_index("embedding", index_params)
            logger.info(f"为{collection_name}创建了向量索引")

            return True

        except Exception as e:
            logger.error(f"创建向量索引失败: {e}")
            return False

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

    async def create_novel_partitions(self, collection_name: str, novel_ids: list[str]) -> bool:
        """Create partitions for each novel_id for Task 3.3."""
        try:
            if not await self._ensure_connected():
                return False

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

            collection = Collection(collection_name)
            partition = collection.partition(partition_name)

            entities = [[novel_id], [chunk_id], [content_type], [content], [embedding], [metadata], [created_at]]

            result = partition.insert(entities)
            logger.info(f"Inserted data to partition {partition_name}")
            return len(result.primary_keys) > 0
        except Exception as e:
            return self._handle_error("insert to partition", e)


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

    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get statistics about a collection."""
        try:
            if not await self._ensure_connected():
                return {"exists": False}

            if not await self.collection_exists(collection_name):
                return {"exists": False}

            collection = Collection(collection_name)
            return {
                "exists": True,
                "name": collection_name,
                "description": collection.schema.description,
                "num_entities": collection.num_entities,
                "num_fields": len(collection.schema.fields),
                "field_names": [f.name for f in collection.schema.fields],
                "indexes": [
                    {"field": idx.field_name, "type": getattr(idx, "index_type", "unknown")}
                    for idx in collection.indexes
                ],
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"exists": False, "error": str(e)}


class MilvusEmbeddingManager:
    """用于管理Milvus中小说嵌入的辅助类。"""

    def __init__(self, schema_manager: MilvusSchemaManager):
        """初始化嵌入管理器。
        
        Args:
            schema_manager: Milvus模式管理器实例
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
                        "id": result.id,                          # 记录ID
                        "score": result.distance,                  # 相似度评分
                        "novel_id": result.entity.get("novel_id"),     # 小说ID
                        "chunk_id": result.entity.get("chunk_id"),     # 文本块ID
                        "content_type": result.entity.get("content_type"),  # 内容类型
                        "content": result.entity.get("content"),       # 文本内容
                        "metadata": result.entity.get("metadata"),     # 元数据
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

            collection = Collection(collection_name)
            collection.load()  # 加载集合到内存

            search_results = collection.search(
                data=[query_embedding],
                anns_field="embedding",               # 向量字段名
                param=search_params,                  # 搜索参数
                limit=limit,                          # 结果数量限制
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
__all__ = ["MilvusSchemaManager", "MilvusEmbeddingManager"]
