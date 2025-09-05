"""
Test Milvus Partitioning Strategy

Tests Task 3.3: 按novel_id设置分区策略
Focused on partition creation, management, and data organization by novel_id.
"""

import time
import uuid

import numpy as np
import pytest


@pytest.mark.asyncio
@pytest.mark.integration
class TestMilvusPartitioning:
    """Test Milvus partitioning strategy by novel_id."""

    async def test_create_partitions_by_novel_id(self):
        """Test creation of partitions organized by novel_id."""
        try:
            from pymilvus import Collection, connections, utility
            from src.db.vector.milvus import MilvusSchemaManager

            connections.connect(alias="default", host="localhost", port="19530")

            schema_manager = MilvusSchemaManager(host="localhost", port="19530")
            await schema_manager.connect()

            collection_name = "test_partitioning"

            # Clean up if exists
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            # Create collection
            await schema_manager.create_novel_embeddings_collection(collection_name)

            # Test partition creation for multiple novels
            test_novel_ids = ["novel_001", "novel_002", "novel_003"]

            partition_success = await schema_manager.create_novel_partitions(collection_name, novel_ids=test_novel_ids)

            assert partition_success is True, "Partition creation should succeed"

            # Verify partitions were created
            collection = Collection(collection_name)
            partitions = collection.partitions
            partition_names = [p.name for p in partitions]

            # Should have default partition plus created partitions
            assert "_default" in partition_names, "Default partition should exist"

            for novel_id in test_novel_ids:
                expected_partition_name = f"partition_{novel_id}"
                assert expected_partition_name in partition_names, f"Partition {expected_partition_name} should exist"

            # Clean up
            utility.drop_collection(collection_name)
            await schema_manager.disconnect()
            connections.disconnect("default")

        except ImportError:
            pytest.skip("Milvus client not available")

    async def test_insert_data_to_specific_partition(self):
        """Test inserting data to specific partitions by novel_id."""
        try:
            from pymilvus import Collection, connections, utility
            from src.db.vector.milvus import MilvusSchemaManager

            connections.connect(alias="default", host="localhost", port="19530")

            schema_manager = MilvusSchemaManager(host="localhost", port="19530")
            await schema_manager.connect()

            collection_name = "test_partition_insert"

            # Clean up and create collection
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            await schema_manager.create_novel_embeddings_collection(collection_name)

            # Create partitions for test novels
            test_novel_ids = ["novel_insert_001", "novel_insert_002"]
            await schema_manager.create_novel_partitions(collection_name, novel_ids=test_novel_ids)

            # Test partition-specific data insertion
            for novel_id in test_novel_ids:
                partition_name = f"partition_{novel_id}"

                # Insert test data to specific partition
                embedding = np.random.random(768).astype(np.float32).tolist()
                current_time = int(time.time())

                insert_success = await schema_manager.insert_to_partition(
                    collection_name,
                    partition_name,
                    novel_id=novel_id,
                    chunk_id=str(uuid.uuid4()),
                    content_type="character",
                    content=f"Test character for {novel_id}",
                    embedding=embedding,
                    metadata={"novel_id": novel_id, "test": True},
                    created_at=current_time,
                )

                assert insert_success is True, f"Partition-specific insertion to {partition_name} should succeed"

            # Verify data was inserted to correct partitions
            collection = Collection(collection_name)

            for novel_id in test_novel_ids:
                partition_name = f"partition_{novel_id}"
                partition = collection.partition(partition_name)

                # Load partition to check entity count
                partition.load()
                assert partition.num_entities > 0, f"Partition {partition_name} should contain data"
                partition.release()

            # Clean up
            utility.drop_collection(collection_name)
            await schema_manager.disconnect()
            connections.disconnect("default")

        except ImportError:
            pytest.skip("Milvus client not available")
        except Exception as e:
            if "numpy" in str(e).lower():
                pytest.skip("NumPy not available")
            else:
                raise

    async def test_partition_isolation(self):
        """Test that partitions properly isolate data by novel_id."""
        try:
            from pymilvus import Collection, connections, utility
            from src.db.vector.milvus import MilvusEmbeddingManager, MilvusSchemaManager

            connections.connect(alias="default", host="localhost", port="19530")

            schema_manager = MilvusSchemaManager(host="localhost", port="19530")
            await schema_manager.connect()

            collection_name = "test_partition_isolation"

            # Clean up and create collection with HNSW index
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            await schema_manager.create_novel_embeddings_collection(collection_name)
            await schema_manager.create_hnsw_index_optimized(collection_name, field_name="embedding")

            # Create partitions for two different novels
            novel_ids = ["novel_isolation_001", "novel_isolation_002"]
            await schema_manager.create_novel_partitions(collection_name, novel_ids=novel_ids)

            embedding_manager = MilvusEmbeddingManager(schema_manager)

            # Insert different data to each partition
            for i, novel_id in enumerate(novel_ids):
                partition_name = f"partition_{novel_id}"

                for j in range(5):  # 5 items per partition
                    embedding = np.random.random(768).astype(np.float32).tolist()

                    await schema_manager.insert_to_partition(
                        collection_name,
                        partition_name,
                        novel_id=novel_id,
                        chunk_id=str(uuid.uuid4()),
                        content_type="test",
                        content=f"Content for {novel_id} item {j}",
                        embedding=embedding,
                        metadata={"novel_id": novel_id, "item": j},
                        created_at=int(time.time()),
                    )

            # Load collection for search
            collection = Collection(collection_name)
            collection.load()

            # Test search isolation - search within specific novel partitions
            query_embedding = np.random.random(768).astype(np.float32).tolist()

            for novel_id in novel_ids:
                # Search specifically within this novel's data
                results = await embedding_manager.search_similar_content_optimized(
                    collection_name,
                    query_embedding=query_embedding,
                    novel_id=novel_id,  # This should restrict to the novel's partition
                    limit=10,
                )

                # Verify all results belong to the correct novel
                for result in results:
                    assert (
                        result["novel_id"] == novel_id
                    ), f"Search result should belong to {novel_id}, got {result['novel_id']}"

            # Clean up
            collection.release()
            utility.drop_collection(collection_name)
            await schema_manager.disconnect()
            connections.disconnect("default")

        except ImportError:
            pytest.skip("Milvus client not available")
        except Exception as e:
            if "numpy" in str(e).lower():
                pytest.skip("NumPy not available")
            else:
                raise

    async def test_partition_management(self):
        """Test partition management operations."""
        try:
            from pymilvus import Collection, connections, utility
            from src.db.vector.milvus import MilvusSchemaManager

            connections.connect(alias="default", host="localhost", port="19530")

            schema_manager = MilvusSchemaManager(host="localhost", port="19530")
            await schema_manager.connect()

            collection_name = "test_partition_management"

            # Clean up and create collection
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            await schema_manager.create_novel_embeddings_collection(collection_name)
            collection = Collection(collection_name)

            # Test creating partitions one by one
            novel_ids = ["novel_mgmt_001", "novel_mgmt_002", "novel_mgmt_003"]

            for novel_id in novel_ids:
                await schema_manager.create_novel_partitions(collection_name, novel_ids=[novel_id])

                partition_name = f"partition_{novel_id}"
                assert collection.has_partition(partition_name), f"Partition {partition_name} should exist"

            # Test duplicate partition creation (should not fail)
            duplicate_success = await schema_manager.create_novel_partitions(
                collection_name,
                novel_ids=["novel_mgmt_001"],  # This already exists
            )
            assert duplicate_success is True, "Creating duplicate partition should succeed (idempotent)"

            # Verify final partition count
            partitions = collection.partitions
            partition_names = [p.name for p in partitions]

            # Should have _default + 3 novel partitions
            expected_count = 1 + len(novel_ids)  # _default + novel partitions
            assert (
                len(partition_names) == expected_count
            ), f"Expected {expected_count} partitions, got {len(partition_names)}"

            # Clean up
            utility.drop_collection(collection_name)
            await schema_manager.disconnect()
            connections.disconnect("default")

        except ImportError:
            pytest.skip("Milvus client not available")
