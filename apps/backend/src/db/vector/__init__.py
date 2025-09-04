"""
Vector database module for InfiniteScribe.

Provides vector database abstraction and management for novel embeddings.
"""

from .milvus import MilvusSchemaManager, MilvusEmbeddingManager

__all__ = [
    "MilvusSchemaManager", 
    "MilvusEmbeddingManager",
]