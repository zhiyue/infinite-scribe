"""
Milvus 向量数据库基础配置和连接管理

包含常量定义、字段模式定义和基础连接管理功能。
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
else:
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


def get_novel_embeddings_fields():
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


class BaseMilvusManager:
    """Milvus基础管理器，提供连接和错误处理功能。"""

    def __init__(self, host: str = "localhost", port: str = "19530"):
        """初始化Milvus基础管理器。

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
            if connections is None:
                return self._handle_error("连接", ImportError("Milvus 客户端库不可用"))
            connections.connect(alias=self.connection_alias, host=self.host, port=self.port)
            self._connected = True
            logger.info(f"已连接到Milvus服务器 {self.host}:{self.port}")
            return True
        except Exception as e:
            return self._handle_error("连接", e)

    async def disconnect(self) -> None:
        """断开与Milvus服务器的连接。"""
        try:
            if self._connected and connections is not None:
                connections.disconnect(self.connection_alias)
                self._connected = False
                logger.info("已断开Milvus连接")
        except Exception as e:
            logger.warning(f"断开连接时出错: {e}")


# 导出的公共接口
__all__ = [
    "COLLECTION_NAME",
    "EMBEDDING_DIM",
    "HNSW_M",
    "HNSW_EF_CONSTRUCTION",
    "HNSW_EF_SEARCH",
    "get_novel_embeddings_fields",
    "BaseMilvusManager",
    "Collection",
    "CollectionSchema",
    "DataType",
    "FieldSchema",
    "connections",
    "utility",
]
