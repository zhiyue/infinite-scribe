"""
Test HNSW Index Configuration for Milvus

Tests Task 3.2: 配置HNSW索引参数（M=32, efConstruction=200, COSINE相似度）
Focused on HNSW index creation, parameter validation, and search optimization.
"""

import pytest


@pytest.mark.asyncio
@pytest.mark.integration
class TestMilvusHNSWIndex:
    """Test HNSW index configuration and optimization."""

    async def test_create_hnsw_index_with_correct_parameters(self, milvus_service):
        """Test creation of HNSW index with M=32, efConstruction=200, COSINE similarity."""
        try:
            from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
            from src.db.vector.milvus import MilvusSchemaManager

            connections.connect(alias="default", host=milvus_service["host"], port=str(milvus_service["port"]))

            schema_manager = MilvusSchemaManager(host=milvus_service["host"], port=str(milvus_service["port"]))
            await schema_manager.connect()

            collection_name = "test_hnsw_index"

            # Clean up if exists
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            # Create test collection
            await schema_manager.create_novel_embeddings_collection(collection_name)

            # Create HNSW index with specific parameters (corrected parameter names)
            hnsw_success = await schema_manager.create_hnsw_index_optimized(
                collection_name, field_name="embedding", m=32, ef_construction=200, metric_type="COSINE"
            )

            assert hnsw_success is True, "HNSW index creation should succeed"

            # Verify index configuration
            collection = Collection(collection_name)
            indexes = collection.indexes
            assert len(indexes) > 0, "Collection should have indexes"

            embedding_index = next((idx for idx in indexes if idx.field_name == "embedding"), None)
            assert embedding_index is not None, "Embedding field should have index"

            # Verify index parameters
            index_params = embedding_index.params
            assert index_params["index_type"] == "HNSW", f"Expected HNSW index, got {index_params.get('index_type')}"
            assert (
                index_params["metric_type"] == "COSINE"
            ), f"Expected COSINE metric, got {index_params.get('metric_type')}"
            assert index_params["params"]["M"] == 32, f"Expected M=32, got {index_params['params'].get('M')}"
            assert (
                index_params["params"]["efConstruction"] == 200
            ), f"Expected efConstruction=200, got {index_params['params'].get('efConstruction')}"

            # Clean up
            utility.drop_collection(collection_name)
            await schema_manager.disconnect()
            connections.disconnect("default")

        except ImportError:
            pytest.skip("Milvus client not available")

    async def test_hnsw_index_parameter_validation(self, milvus_service):
        """Test HNSW index parameter validation and bounds."""
        try:
            from pymilvus import connections, utility
            from src.db.vector.milvus import MilvusSchemaManager

            connections.connect(alias="default", host=milvus_service["host"], port=str(milvus_service["port"]))

            schema_manager = MilvusSchemaManager(host=milvus_service["host"], port=str(milvus_service["port"]))
            await schema_manager.connect()

            collection_name = "test_hnsw_validation"

            # Clean up if exists
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            await schema_manager.create_novel_embeddings_collection(collection_name)

            # Test valid parameter ranges (corrected parameter names)
            valid_configs = [
                {"m": 4, "ef_construction": 8, "metric_type": "COSINE"},  # Minimum values
                {"m": 16, "ef_construction": 40, "metric_type": "COSINE"},  # Default-like values
                {"m": 64, "ef_construction": 512, "metric_type": "COSINE"},  # Maximum values
            ]

            for config in valid_configs:
                # Drop and recreate collection for each test
                utility.drop_collection(collection_name)
                await schema_manager.create_novel_embeddings_collection(collection_name)

                success = await schema_manager.create_hnsw_index_optimized(
                    collection_name,
                    field_name="embedding",
                    m=config["m"],
                    ef_construction=config["ef_construction"],
                    metric_type=config["metric_type"],
                )

                assert (
                    success is True
                ), f"HNSW index should be created with m={config['m']}, ef_construction={config['ef_construction']}"

            # Clean up
            utility.drop_collection(collection_name)
            await schema_manager.disconnect()
            connections.disconnect("default")

        except ImportError:
            pytest.skip("Milvus client not available")

    async def test_hnsw_index_search_performance(self, milvus_service):
        """Test search performance with HNSW index and ef parameter tuning."""
        try:
            import time
            import uuid

            import numpy as np
            from pymilvus import Collection, connections, utility
            from src.db.vector.milvus import MilvusEmbeddingManager, MilvusSchemaManager

            connections.connect(alias="default", host=milvus_service["host"], port=str(milvus_service["port"]))

            schema_manager = MilvusSchemaManager(host=milvus_service["host"], port=str(milvus_service["port"]))
            await schema_manager.connect()

            collection_name = "test_hnsw_search"

            # Clean up and create collection
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            await schema_manager.create_novel_embeddings_collection(collection_name)
            await schema_manager.create_hnsw_index_optimized(
                collection_name, field_name="embedding", m=32, ef_construction=200, metric_type="COSINE"
            )

            # Insert test data
            embedding_manager = MilvusEmbeddingManager(schema_manager)
            test_data = []
            for i in range(100):  # Smaller dataset for focused test
                embedding = np.random.random(768).astype(np.float32).tolist()
                test_data.append(
                    {
                        "novel_id": "novel_hnsw_test",
                        "chunk_id": str(uuid.uuid4()),
                        "content_type": "test",
                        "content": f"HNSW test content {i}",
                        "embedding": embedding,
                        "metadata": {"test_index": i},
                        "created_at": int(time.time()),
                    }
                )

            insert_success = await embedding_manager.batch_insert_embeddings(collection_name, test_data)
            assert insert_success is True, "Test data insertion should succeed"

            # Load collection and test search with different ef values
            collection = Collection(collection_name)
            collection.load()

            query_embedding = np.random.random(768).astype(np.float32).tolist()

            # Test different ef values for performance tuning
            ef_values = [32, 64, 128]
            search_times = {}

            for ef in ef_values:
                start_time = time.time()
                results = await embedding_manager.search_similar_content_optimized(
                    collection_name, query_embedding=query_embedding, novel_id="novel_hnsw_test", limit=10, ef=ef
                )
                search_time = time.time() - start_time

                search_times[ef] = {"time": search_time, "results_count": len(results)}

                # Verify search returns results
                assert len(results) > 0, f"Search with ef={ef} should return results"

                # Verify performance requirement (< 400ms)
                assert search_time < 0.4, f"Search with ef={ef} should complete < 400ms, took {search_time}s"

            # For small datasets, ef parameter differences may be minimal - just verify all searches work
            all_times = [result["time"] for result in search_times.values()]
            max_time = max(all_times)
            assert max_time < 0.1, f"All searches should be fast for small dataset, max time: {max_time*1000:.2f}ms"

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
