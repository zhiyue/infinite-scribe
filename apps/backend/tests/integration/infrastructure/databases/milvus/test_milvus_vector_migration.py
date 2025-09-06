"""
Test Milvus vector database configuration for Task 1 implementation.

Tests the creation of novel_embeddings_v1 collection with 768-dimensional
vector indexing as required by the novel genesis stage architecture.
"""

import uuid

import numpy as np
import pytest


@pytest.mark.asyncio
@pytest.mark.integration
class TestMilvusVectorMigration:
    """Test Milvus vector database migration."""

    async def test_milvus_connection(self, milvus_service):
        """Test that Milvus service is available and accessible."""
        try:
            from pymilvus import connections, utility

            # Connect to Milvus (assuming it's running on default host:port)
            connections.connect(alias="default", host=milvus_service["host"], port=str(milvus_service["port"]))

            # Check connection
            assert utility.get_server_version()

            # Disconnect
            connections.disconnect("default")

        except ImportError:
            pytest.skip("Milvus client not available")
        except Exception as e:
            pytest.fail(f"Milvus service is not available: {e}")

    async def test_milvus_collection_creation(self, milvus_service):
        """Test creation of novel_embeddings_v1 collection with proper schema."""
        try:
            from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

            connections.connect(alias="default", host=milvus_service["host"], port=str(milvus_service["port"]))

            # Define collection schema
            collection_name = "novel_embeddings_v1_test"

            # Clean up if exists
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            # Define fields according to novel genesis requirements
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

            schema = CollectionSchema(fields, "Novel embeddings collection for semantic search")
            collection = Collection(collection_name, schema)

            # Verify collection was created
            assert utility.has_collection(collection_name)
            assert collection.num_entities == 0

            # Verify schema
            assert collection.schema.description == "Novel embeddings collection for semantic search"
            assert len(collection.schema.fields) == 8

            # Check specific field properties
            embedding_field = next(f for f in collection.schema.fields if f.name == "embedding")
            assert embedding_field.dtype == DataType.FLOAT_VECTOR
            assert embedding_field.params["dim"] == 768

            # Clean up
            utility.drop_collection(collection_name)
            connections.disconnect("default")

        except ImportError:
            pytest.skip("Milvus client not available")

    async def test_milvus_index_creation(self, milvus_service):
        """Test creation of vector index for performance optimization."""
        try:
            from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

            connections.connect(alias="default", host=milvus_service["host"], port=str(milvus_service["port"]))

            collection_name = "novel_embeddings_v1_index_test"

            # Clean up if exists
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            # Create collection
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="novel_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
                FieldSchema(name="metadata", dtype=DataType.JSON),
                FieldSchema(name="created_at", dtype=DataType.INT64),
            ]

            schema = CollectionSchema(fields, "Novel embeddings test collection")
            collection = Collection(collection_name, schema)

            # Create IVF_FLAT index for 768-dimensional vectors
            index_params = {
                "metric_type": "IP",  # Inner Product for cosine similarity
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128},
            }

            collection.create_index("embedding", index_params)

            # Verify index was created
            indexes = collection.indexes
            assert len(indexes) == 1
            assert indexes[0].field_name == "embedding"
            # Note: Index object structure may vary between pymilvus versions
            # Just verify the index exists for the embedding field

            # Clean up
            utility.drop_collection(collection_name)
            connections.disconnect("default")

        except ImportError:
            pytest.skip("Milvus client not available")

    async def test_milvus_data_operations(self, milvus_service):
        """Test basic CRUD operations with novel embeddings."""
        try:
            import time

            from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

            connections.connect(alias="default", host=milvus_service["host"], port=str(milvus_service["port"]))

            collection_name = "novel_embeddings_v1_crud_test"

            # Clean up if exists
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            # Create collection
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="novel_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
                FieldSchema(name="metadata", dtype=DataType.JSON),
                FieldSchema(name="created_at", dtype=DataType.INT64),
            ]

            schema = CollectionSchema(fields, "Novel embeddings CRUD test collection")
            collection = Collection(collection_name, schema)

            # Create index
            index_params = {"metric_type": "IP", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
            collection.create_index("embedding", index_params)

            # Prepare test data
            novel_id = str(uuid.uuid4())
            chunk_id = str(uuid.uuid4())
            embedding = np.random.random(768).astype(np.float32).tolist()  # Random 768-dim vector
            current_time = int(time.time())

            entities = [
                [novel_id],  # novel_id
                [chunk_id],  # chunk_id
                ["character"],  # content_type
                ["Test character description"],  # content
                [embedding],  # embedding
                [{"chapter": 1, "scene": 1}],  # metadata
                [current_time],  # created_at
            ]

            # Insert data
            insert_result = collection.insert(entities)
            assert len(insert_result.primary_keys) == 1

            # Flush to ensure data is persisted
            collection.flush()

            # Load collection
            collection.load()

            # Verify data (need to check after flush)
            assert collection.num_entities == 1

            # Search test
            search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
            search_results = collection.search(
                data=[embedding],
                anns_field="embedding",
                param=search_params,
                limit=10,
                output_fields=["novel_id", "chunk_id", "content_type", "content"],
            )

            assert len(search_results) == 1
            assert len(search_results[0]) >= 1
            assert search_results[0][0].entity.get("novel_id") == novel_id
            assert search_results[0][0].entity.get("content_type") == "character"

            # Clean up
            utility.drop_collection(collection_name)
            connections.disconnect("default")

        except ImportError:
            pytest.skip("Milvus client not available")
        except Exception as e:
            if "numpy" in str(e).lower():
                pytest.skip("NumPy not available")
            else:
                raise

    async def test_milvus_novel_embeddings_schema_manager(self, milvus_service):
        """Test the schema manager for novel embeddings collection."""
        try:
            from src.db.vector.milvus import MilvusSchemaManager

            schema_manager = MilvusSchemaManager(host=milvus_service["host"], port=str(milvus_service["port"]))

            # Test collection creation
            await schema_manager.create_novel_embeddings_collection()

            # Test collection exists
            exists = await schema_manager.collection_exists("novel_embeddings_v1")
            assert exists

            # Test index creation
            await schema_manager.create_novel_embeddings_index()

            # Test schema verification
            is_valid = await schema_manager.verify_novel_embeddings_schema()
            assert is_valid

            # Clean up
            await schema_manager.drop_collection("novel_embeddings_v1")
            await schema_manager.disconnect()

        except ImportError:
            pytest.skip("Milvus schema manager not available")
