"""
Test Milvus Performance Optimization

Tests Task 3.4: 测试向量插入、检索性能并优化索引参数
Focused on insert/search performance testing and optimization.
"""

import time
import uuid

import numpy as np
import pytest


@pytest.mark.asyncio
@pytest.mark.integration
class TestMilvusPerformance:
    """Test Milvus performance optimization for vector operations."""

    async def test_batch_insert_performance(self):
        """Test batch insertion performance with different batch sizes."""
        try:
            from pymilvus import connections, utility
            from src.db.vector.milvus import MilvusSchemaManager, MilvusEmbeddingManager

            connections.connect(alias="default", host="localhost", port="19530")
            
            schema_manager = MilvusSchemaManager(host="localhost", port="19530")
            await schema_manager.connect()

            collection_name = "test_insert_performance"
            
            # Clean up and create optimized collection
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            await schema_manager.create_novel_embeddings_collection(collection_name)
            
            embedding_manager = MilvusEmbeddingManager(schema_manager)

            # Test different batch sizes
            batch_sizes = [10, 50, 100]
            performance_results = {}

            for batch_size in batch_sizes:
                # Generate test data
                test_data = []
                for i in range(batch_size):
                    embedding = np.random.random(768).astype(np.float32).tolist()
                    test_data.append({
                        "novel_id": f"perf_test_novel",
                        "chunk_id": str(uuid.uuid4()),
                        "content_type": "performance_test",
                        "content": f"Performance test content {i}",
                        "embedding": embedding,
                        "metadata": {"batch": batch_size, "index": i},
                        "created_at": int(time.time())
                    })

                # Measure insertion performance
                start_time = time.time()
                insert_success = await embedding_manager.batch_insert_embeddings(
                    collection_name, 
                    test_data
                )
                end_time = time.time()

                insertion_time = end_time - start_time
                items_per_second = batch_size / insertion_time if insertion_time > 0 else 0
                
                performance_results[batch_size] = {
                    "insertion_time": insertion_time,
                    "items_per_second": items_per_second,
                    "success": insert_success
                }

                assert insert_success is True, f"Batch insertion of {batch_size} items should succeed"
                print(f"Batch size {batch_size}: {items_per_second:.2f} items/second")

            # Performance assertions
            # Larger batch sizes should be more efficient per item
            if 10 in performance_results and 100 in performance_results:
                small_batch_rate = performance_results[10]["items_per_second"]
                large_batch_rate = performance_results[100]["items_per_second"]
                
                # Large batch should be at least 1.5x more efficient per item
                efficiency_ratio = large_batch_rate / small_batch_rate if small_batch_rate > 0 else 0
                assert efficiency_ratio >= 1.5, f"Large batch should be more efficient: {large_batch_rate:.2f} vs {small_batch_rate:.2f} items/sec"

            # Overall performance requirement: should achieve reasonable throughput
            max_rate = max(result["items_per_second"] for result in performance_results.values())
            assert max_rate >= 50, f"Should achieve at least 50 items/second, got {max_rate:.2f}"

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

    async def test_vector_search_performance_optimization(self):
        """Test vector search performance with HNSW optimization."""
        try:
            from pymilvus import Collection, connections, utility
            from src.db.vector.milvus import MilvusSchemaManager, MilvusEmbeddingManager

            connections.connect(alias="default", host="localhost", port="19530")
            
            schema_manager = MilvusSchemaManager(host="localhost", port="19530")
            await schema_manager.connect()

            collection_name = "test_search_performance"
            
            # Clean up and create collection with HNSW index
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            await schema_manager.create_novel_embeddings_collection(collection_name)
            await schema_manager.create_hnsw_index_optimized(
                collection_name, 
                field_name="embedding",
                M=32,
                efConstruction=200,
                metric_type="COSINE"
            )
            
            embedding_manager = MilvusEmbeddingManager(schema_manager)

            # Insert test data for search performance testing
            num_test_vectors = 500  # Reasonable size for test
            test_data = []
            for i in range(num_test_vectors):
                embedding = np.random.random(768).astype(np.float32).tolist()
                test_data.append({
                    "novel_id": "search_perf_test",
                    "chunk_id": str(uuid.uuid4()),
                    "content_type": "search_test",
                    "content": f"Search performance test content {i}",
                    "embedding": embedding,
                    "metadata": {"index": i},
                    "created_at": int(time.time())
                })

            # Insert data
            insert_success = await embedding_manager.batch_insert_embeddings(collection_name, test_data)
            assert insert_success is True, "Test data insertion should succeed"

            # Load collection for search
            collection = Collection(collection_name)
            collection.load()

            # Test different search configurations for performance
            search_configs = [
                {"ef": 32, "limit": 5, "name": "fast_low_accuracy"},
                {"ef": 64, "limit": 10, "name": "standard"},
                {"ef": 128, "limit": 10, "name": "high_accuracy"},
            ]

            performance_results = {}

            for config in search_configs:
                query_embedding = np.random.random(768).astype(np.float32).tolist()
                
                # Run multiple searches to get average performance
                search_times = []
                for _ in range(3):  # 3 runs for average
                    start_time = time.time()
                    search_results = await embedding_manager.search_similar_content_optimized(
                        collection_name,
                        query_embedding=query_embedding,
                        novel_id="search_perf_test",
                        limit=config["limit"],
                        ef=config["ef"]
                    )
                    end_time = time.time()
                    search_times.append(end_time - start_time)

                avg_search_time = sum(search_times) / len(search_times)
                performance_results[config["name"]] = {
                    "avg_search_time": avg_search_time,
                    "results_count": len(search_results) if 'search_results' in locals() else 0,
                    "success": len(search_results) > 0 if 'search_results' in locals() else False
                }

                print(f"Search config {config['name']}: {avg_search_time*1000:.2f}ms avg")

            # Performance requirements (NFR-001: vector search <400ms)
            for config_name, result in performance_results.items():
                assert result["avg_search_time"] < 0.4, f"Search {config_name} should complete < 400ms, took {result['avg_search_time']*1000:.2f}ms"
                assert result["success"] is True, f"Search {config_name} should return results"

            # Performance comparison: fast config should be faster
            if "fast_low_accuracy" in performance_results and "high_accuracy" in performance_results:
                fast_time = performance_results["fast_low_accuracy"]["avg_search_time"]
                high_acc_time = performance_results["high_accuracy"]["avg_search_time"]
                
                # Fast should be at least 10% faster than high accuracy
                assert fast_time < high_acc_time * 0.9, f"Fast search should be faster: {fast_time*1000:.2f}ms vs {high_acc_time*1000:.2f}ms"

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

    async def test_concurrent_operations_performance(self):
        """Test performance under concurrent operations."""
        try:
            import asyncio
            from pymilvus import Collection, connections, utility
            from src.db.vector.milvus import MilvusSchemaManager, MilvusEmbeddingManager

            connections.connect(alias="default", host="localhost", port="19530")
            
            schema_manager = MilvusSchemaManager(host="localhost", port="19530")
            await schema_manager.connect()

            collection_name = "test_concurrent_performance"
            
            # Clean up and create optimized collection
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            await schema_manager.create_novel_embeddings_collection(collection_name)
            await schema_manager.create_hnsw_index_optimized(collection_name, field_name="embedding")
            
            embedding_manager = MilvusEmbeddingManager(schema_manager)

            # Insert initial data
            initial_data = []
            for i in range(100):
                embedding = np.random.random(768).astype(np.float32).tolist()
                initial_data.append({
                    "novel_id": "concurrent_test",
                    "chunk_id": str(uuid.uuid4()),
                    "content_type": "concurrent_test",
                    "content": f"Concurrent test content {i}",
                    "embedding": embedding,
                    "metadata": {"index": i},
                    "created_at": int(time.time())
                })

            await embedding_manager.batch_insert_embeddings(collection_name, initial_data)

            # Load collection
            collection = Collection(collection_name)
            collection.load()

            # Define concurrent search operations
            async def perform_search(search_id: int):
                query_embedding = np.random.random(768).astype(np.float32).tolist()
                start_time = time.time()
                
                results = await embedding_manager.search_similar_content_optimized(
                    collection_name,
                    query_embedding=query_embedding,
                    novel_id="concurrent_test",
                    limit=5
                )
                
                search_time = time.time() - start_time
                return {
                    "search_id": search_id,
                    "search_time": search_time,
                    "results_count": len(results)
                }

            # Run concurrent searches
            num_concurrent_searches = 5
            start_time = time.time()
            
            concurrent_results = await asyncio.gather(*[
                perform_search(i) for i in range(num_concurrent_searches)
            ])
            
            total_time = time.time() - start_time

            # Verify all searches completed successfully
            for result in concurrent_results:
                assert result["results_count"] > 0, f"Concurrent search {result['search_id']} should return results"
                assert result["search_time"] < 0.5, f"Concurrent search {result['search_id']} should complete < 500ms"

            # Overall concurrent performance should be reasonable
            avg_search_time = sum(r["search_time"] for r in concurrent_results) / len(concurrent_results)
            print(f"Concurrent searches: {avg_search_time*1000:.2f}ms average, {total_time:.2f}s total")

            assert avg_search_time < 0.4, f"Average concurrent search time should be < 400ms, got {avg_search_time*1000:.2f}ms"

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

    async def test_memory_usage_optimization(self):
        """Test memory usage during large batch operations."""
        try:
            from pymilvus import connections, utility
            from src.db.vector.milvus import MilvusSchemaManager, MilvusEmbeddingManager

            connections.connect(alias="default", host="localhost", port="19530")
            
            schema_manager = MilvusSchemaManager(host="localhost", port="19530")
            await schema_manager.connect()

            collection_name = "test_memory_optimization"
            
            # Clean up and create collection
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

            await schema_manager.create_novel_embeddings_collection(collection_name)
            
            embedding_manager = MilvusEmbeddingManager(schema_manager)

            # Test chunked insertion to manage memory
            total_items = 200  # Smaller for test efficiency
            chunk_size = 50
            
            for chunk_start in range(0, total_items, chunk_size):
                chunk_end = min(chunk_start + chunk_size, total_items)
                chunk_data = []
                
                for i in range(chunk_start, chunk_end):
                    embedding = np.random.random(768).astype(np.float32).tolist()
                    chunk_data.append({
                        "novel_id": "memory_test",
                        "chunk_id": str(uuid.uuid4()),
                        "content_type": "memory_test",
                        "content": f"Memory test content {i}",
                        "embedding": embedding,
                        "metadata": {"chunk": chunk_start // chunk_size, "index": i},
                        "created_at": int(time.time())
                    })

                # Insert chunk
                start_time = time.time()
                insert_success = await embedding_manager.batch_insert_embeddings(collection_name, chunk_data)
                chunk_time = time.time() - start_time
                
                assert insert_success is True, f"Chunk insertion {chunk_start}-{chunk_end} should succeed"
                
                # Each chunk should complete reasonably quickly
                assert chunk_time < 5.0, f"Chunk insertion should complete < 5s, took {chunk_time:.2f}s"

            print(f"Successfully inserted {total_items} items in chunks of {chunk_size}")

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