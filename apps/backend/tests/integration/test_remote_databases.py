"""Integration tests for remote database connections."""

import asyncio
from contextlib import suppress

import pytest
from src.common.services.neo4j_service import Neo4jService
from src.common.services.postgres_service import PostgreSQLService
from src.common.services.redis_service import RedisService


@pytest.mark.asyncio
@pytest.mark.integration
async def test_remote_postgres_connection():
    """Test PostgreSQL connection to remote container."""
    service = PostgreSQLService()

    # Test connection
    await service.connect()
    is_healthy = await service.check_connection()
    assert is_healthy is True

    # Test query execution
    async with service.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1

    await service.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_remote_neo4j_connection():
    """Test Neo4j connection to remote container."""
    service = Neo4jService()

    # Test connection
    await service.connect()
    is_healthy = await service.check_connection()
    assert is_healthy is True

    # Test query execution
    result = await service.execute("RETURN 1 as number")
    assert len(result) == 1
    assert result[0]["number"] == 1

    await service.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_remote_redis_connection():
    """Test Redis connection to remote container."""
    service = RedisService()

    # Test connection
    await service.connect()
    is_healthy = await service.check_connection()
    assert is_healthy is True

    # Test basic operations
    await service.set("test_key", "test_value")
    value = await service.get("test_key")
    assert value == "test_value"

    # Cleanup
    await service.delete("test_key")
    await service.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_remote_connections():
    """Test handling multiple concurrent connections to remote databases."""
    postgres_service = PostgreSQLService()
    neo4j_service = Neo4jService()
    redis_service = RedisService()

    # Connect all services
    await postgres_service.connect()
    await neo4j_service.connect()
    await redis_service.connect()

    # Define concurrent operations
    async def postgres_query():
        async with postgres_service.acquire() as conn:
            return await conn.fetchval("SELECT 'postgres' as db")

    async def neo4j_query():
        result = await neo4j_service.execute("RETURN 'neo4j' as db")
        return result[0]["db"]

    async def redis_operation():
        await redis_service.set("concurrent_test", "redis")
        value = await redis_service.get("concurrent_test")
        await redis_service.delete("concurrent_test")
        return value

    # Run concurrent operations
    results = await asyncio.gather(postgres_query(), neo4j_query(), redis_operation())

    assert results == ["postgres", "neo4j", "redis"]

    # Disconnect all services
    await postgres_service.disconnect()
    await neo4j_service.disconnect()
    await redis_service.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_remote_postgres_transaction():
    """Test database transaction with remote PostgreSQL."""
    service = PostgreSQLService()
    await service.connect()

    # Create a test table
    async with service.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS remote_test_table (
                id SERIAL PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        # Clean up any existing data
        await conn.execute("TRUNCATE TABLE remote_test_table")

    # Test successful transaction
    async with service.acquire() as conn, conn.transaction():
        await conn.execute("INSERT INTO remote_test_table (value) VALUES ('test1')")
        await conn.execute("INSERT INTO remote_test_table (value) VALUES ('test2')")

    # Verify data was inserted
    async with service.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM remote_test_table")
        assert count == 2

    # Test transaction rollback
    with suppress(Exception):
        async with service.acquire() as conn, conn.transaction():
            await conn.execute("INSERT INTO remote_test_table (value) VALUES ('test3')")
            # Force an error
            await conn.execute("INVALID SQL")

    # Verify rollback - should still have only 2 records
    async with service.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM remote_test_table")
        assert count == 2

        # Cleanup
        await conn.execute("DROP TABLE IF EXISTS remote_test_table")

    await service.disconnect()
