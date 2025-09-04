"""
Milvus Vector Database Schema Management

Manages Milvus database schema creation, collections, and indexes
for the novel genesis system vector embeddings.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MilvusSchemaManager:
    """Manages Milvus schema creation and validation for novel embeddings."""

    def __init__(self, host: str = "localhost", port: str = "19530"):
        self.host = host
        self.port = port
        self.connection_alias = "default"
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Milvus server."""
        try:
            from pymilvus import connections

            connections.connect(alias=self.connection_alias, host=self.host, port=self.port)
            self._connected = True
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
            return True

        except ImportError:
            logger.error("Milvus client library not available")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Milvus server."""
        try:
            from pymilvus import connections

            if self._connected:
                connections.disconnect(self.connection_alias)
                self._connected = False
                logger.info("Disconnected from Milvus")

        except Exception as e:
            logger.warning(f"Error during disconnect: {e}")

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists."""
        try:
            from pymilvus import utility

            if not self._connected:
                await self.connect()

            return utility.has_collection(collection_name)

        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False

    async def create_novel_embeddings_collection(self) -> bool:
        """Create the novel_embeddings_v1 collection with proper schema."""
        try:
            from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, utility

            if not self._connected:
                await self.connect()

            collection_name = "novel_embeddings_v1"

            # Drop existing collection if it exists
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                logger.info(f"Dropped existing collection: {collection_name}")

            # Define collection schema for novel embeddings
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="novel_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(
                    name="content_type", dtype=DataType.VARCHAR, max_length=50
                ),  # character, worldrule, event, etc.
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),  # 768-dimensional embeddings
                FieldSchema(name="metadata", dtype=DataType.JSON),
                FieldSchema(name="created_at", dtype=DataType.INT64),  # Unix timestamp
            ]

            schema = CollectionSchema(
                fields, description="Novel embeddings collection for semantic search and content analysis"
            )

            collection = Collection(collection_name, schema)
            logger.info(f"Created collection: {collection_name}")

            return True

        except ImportError:
            logger.error("Milvus client library not available")
            return False
        except Exception as e:
            logger.error(f"Failed to create novel embeddings collection: {e}")
            return False

    async def create_novel_embeddings_index(self) -> bool:
        """Create vector index for novel embeddings collection."""
        try:
            from pymilvus import Collection

            if not self._connected:
                await self.connect()

            collection_name = "novel_embeddings_v1"
            collection = Collection(collection_name)

            # Create IVF_FLAT index for 768-dimensional vectors
            # Using Inner Product metric for cosine similarity search
            index_params = {
                "metric_type": "IP",  # Inner Product for cosine similarity
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128},  # Number of cluster units
            }

            collection.create_index("embedding", index_params)
            logger.info(f"Created vector index for {collection_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")
            return False

    async def verify_novel_embeddings_schema(self) -> bool:
        """Verify the novel embeddings collection schema is correct."""
        try:
            from pymilvus import Collection, DataType

            if not self._connected:
                await self.connect()

            collection_name = "novel_embeddings_v1"

            if not await self.collection_exists(collection_name):
                logger.error(f"Collection {collection_name} does not exist")
                return False

            collection = Collection(collection_name)

            # Verify schema
            schema = collection.schema

            # Check required fields
            field_names = {field.name for field in schema.fields}
            required_fields = {
                "id",
                "novel_id",
                "chunk_id",
                "content_type",
                "content",
                "embedding",
                "metadata",
                "created_at",
            }

            missing_fields = required_fields - field_names
            if missing_fields:
                logger.error(f"Missing required fields: {missing_fields}")
                return False

            # Check embedding field is 768-dimensional
            embedding_field = next(f for f in schema.fields if f.name == "embedding")
            if embedding_field.dtype != DataType.FLOAT_VECTOR:
                logger.error("embedding field is not FLOAT_VECTOR type")
                return False

            if embedding_field.params.get("dim") != 768:
                logger.error("embedding field is not 768-dimensional")
                return False

            # Check indexes exist
            indexes = collection.indexes
            if not indexes:
                logger.error("No indexes found on collection")
                return False

            embedding_index = next((idx for idx in indexes if idx.field_name == "embedding"), None)
            if not embedding_index:
                logger.error("No index found on embedding field")
                return False

            logger.info("Novel embeddings schema verification passed")
            return True

        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            return False

    async def drop_collection(self, collection_name: str) -> bool:
        """Drop a collection."""
        try:
            from pymilvus import utility

            if not self._connected:
                await self.connect()

            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                logger.info(f"Dropped collection: {collection_name}")
                return True

            return True

        except Exception as e:
            logger.error(f"Failed to drop collection {collection_name}: {e}")
            return False

    async def initialize_novel_embeddings(self) -> bool:
        """Initialize complete novel embeddings setup."""
        logger.info("Initializing Milvus novel embeddings schema...")

        try:
            # Connect to Milvus
            if not await self.connect():
                return False

            # Create collection
            if not await self.create_novel_embeddings_collection():
                return False

            # Create index
            if not await self.create_novel_embeddings_index():
                return False

            # Verify schema
            if not await self.verify_novel_embeddings_schema():
                return False

            logger.info("Milvus novel embeddings initialization completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize novel embeddings: {e}")
            return False

    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get statistics about a collection."""
        try:
            from pymilvus import Collection

            if not self._connected:
                await self.connect()

            if not await self.collection_exists(collection_name):
                return {"exists": False}

            collection = Collection(collection_name)

            stats = {
                "exists": True,
                "name": collection_name,
                "description": collection.schema.description,
                "num_entities": collection.num_entities,
                "num_fields": len(collection.schema.fields),
                "field_names": [f.name for f in collection.schema.fields],
                "indexes": [{"field": idx.field_name, "type": idx.index_type} for idx in collection.indexes],
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"exists": False, "error": str(e)}


class MilvusEmbeddingManager:
    """Helper class for managing novel embeddings in Milvus."""

    def __init__(self, schema_manager: MilvusSchemaManager):
        self.schema_manager = schema_manager

    async def insert_novel_embedding(
        self,
        novel_id: str,
        chunk_id: str,
        content_type: str,
        content: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Insert a single novel embedding."""
        try:
            import time

            from pymilvus import Collection

            if not self.schema_manager._connected:
                await self.schema_manager.connect()

            collection = Collection("novel_embeddings_v1")

            if len(embedding) != 768:
                raise ValueError(f"Embedding must be 768-dimensional, got {len(embedding)}")

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
            logger.info(f"Inserted embedding for {content_type} in novel {novel_id}")

            return len(result.primary_keys) > 0

        except Exception as e:
            logger.error(f"Failed to insert embedding: {e}")
            return False

    async def search_similar_content(
        self,
        query_embedding: list[float],
        novel_id: str | None = None,
        content_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for similar content using vector similarity."""
        try:
            from pymilvus import Collection

            if not self.schema_manager._connected:
                await self.schema_manager.connect()

            collection = Collection("novel_embeddings_v1")
            collection.load()  # Load collection into memory for search

            search_params = {"metric_type": "IP", "params": {"nprobe": 10}}

            # Build filter expression
            filter_expr = None
            if novel_id and content_type:
                filter_expr = f'novel_id == "{novel_id}" && content_type == "{content_type}"'
            elif novel_id:
                filter_expr = f'novel_id == "{novel_id}"'
            elif content_type:
                filter_expr = f'content_type == "{content_type}"'

            search_results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=limit,
                output_fields=["novel_id", "chunk_id", "content_type", "content", "metadata"],
                expr=filter_expr,
            )

            results = []
            if search_results and len(search_results[0]) > 0:
                for result in search_results[0]:
                    results.append(
                        {
                            "id": result.id,
                            "score": result.distance,
                            "novel_id": result.entity.get("novel_id"),
                            "chunk_id": result.entity.get("chunk_id"),
                            "content_type": result.entity.get("content_type"),
                            "content": result.entity.get("content"),
                            "metadata": result.entity.get("metadata"),
                        }
                    )

            return results

        except Exception as e:
            logger.error(f"Failed to search similar content: {e}")
            return []


__all__ = ["MilvusSchemaManager", "MilvusEmbeddingManager"]
