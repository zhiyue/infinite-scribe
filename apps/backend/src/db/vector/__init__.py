"""
Vector database module for InfiniteScribe.

Provides vector database abstraction and management for novel embeddings.
"""

from .milvus import MilvusEmbeddingManager, MilvusSchemaManager

__all__ = [
    "MilvusSchemaManager",
    "MilvusEmbeddingManager",
]
