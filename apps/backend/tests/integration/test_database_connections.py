"""Integration tests for database connections using fixtures."""

import asyncio
from contextlib import suppress
from unittest.mock import patch

import pytest
from src.common.services.neo4j_service import Neo4jService
from src.common.services.postgres_service import PostgreSQLService
from src.common.services.redis_service import RedisService


@pytest.mark.asyncio
@pytest.mark.integration
async def test_postgres_connection_success(postgres_service):
    """Test successful PostgreSQL connection."""
    # Create PostgreSQL URL from service config
    config = postgres_service
    postgres_url = f"postgresql+asyncpg://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

    # Mock settings to use test configuration
    with patch("src.common.services.postgres_service.settings") as mock_settings:
        mock_settings.POSTGRES_URL = postgres_url

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
async def test_postgres_connection_failure():
    """Test PostgreSQL connection failure handling."""
    # Mock settings with invalid PostgreSQL URL
    with patch("src.common.services.postgres_service.settings") as mock_settings:
        mock_settings.POSTGRES_URL = (
            "postgresql+asyncpg://invalid:invalid@invalid-host:5432/invalid"
        )

        service = PostgreSQLService()

        # Test that connection fails gracefully
        with suppress(Exception):
            await service.connect()

        # Test health check returns False
        is_healthy = await service.check_connection()
        assert is_healthy is False


@pytest.mark.asyncio
@pytest.mark.integration
async def test_neo4j_connection_success(neo4j_service):
    """Test successful Neo4j connection."""
    config = neo4j_service

    # Mock settings for Neo4j
    with patch("src.common.services.neo4j_service.settings") as mock_settings:
        mock_settings.NEO4J_URL = f"bolt://{config['host']}:{config['port']}"
        mock_settings.NEO4J_USER = config["user"]
        mock_settings.NEO4J_PASSWORD = config["password"]

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
async def test_neo4j_connection_failure():
    """Test Neo4j connection failure handling."""
    # Mock settings with invalid Neo4j URL
    with patch("src.common.services.neo4j_service.settings") as mock_settings:
        mock_settings.NEO4J_URL = "bolt://invalid-host:7687"
        mock_settings.NEO4J_USER = "invalid"
        mock_settings.NEO4J_PASSWORD = "invalid"

        service = Neo4jService()

        # Test that connection fails gracefully
        with suppress(Exception):
            await service.connect()

        # Test health check returns False
        is_healthy = await service.check_connection()
        assert is_healthy is False


@pytest.mark.asyncio
@pytest.mark.integration
async def test_redis_connection_success(redis_service):
    """Test successful Redis connection."""
    config = redis_service

    # Mock settings for Redis
    with patch("src.common.services.redis_service.settings") as mock_settings:
        mock_settings.REDIS_URL = f"redis://{config['host']}:{config['port']}"
        if config.get("password"):
            mock_settings.REDIS_URL = f"redis://:{config['password']}@{config['host']}:{config['port']}"

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
async def test_redis_connection_failure():
    """Test Redis connection failure handling."""
    # Mock settings with invalid Redis URL
    with patch("src.common.services.redis_service.settings") as mock_settings:
        mock_settings.REDIS_URL = "redis://invalid-host:6379"

        service = RedisService()

        # Test that connection fails gracefully
        with suppress(Exception):
            await service.connect()

        # Test health check returns False
        is_healthy = await service.check_connection()
        assert is_healthy is False


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_database_connections(postgres_service, neo4j_service, redis_service):
    """Test handling multiple concurrent connections to all databases."""
    # PostgreSQL configuration
    pg_config = postgres_service
    postgres_url = f"postgresql+asyncpg://{pg_config['user']}:{pg_config['password']}@{pg_config['host']}:{pg_config['port']}/{pg_config['database']}"

    # Neo4j configuration
    neo4j_config = neo4j_service

    # Redis configuration
    redis_config = redis_service
    redis_url = f"redis://{redis_config['host']}:{redis_config['port']}"
    if redis_config.get("password"):
        redis_url = f"redis://:{redis_config['password']}@{redis_config['host']}:{redis_config['port']}"

    # Mock settings for all services
    with (
        patch("src.common.services.postgres_service.settings") as mock_pg_settings,
        patch("src.common.services.neo4j_service.settings") as mock_neo4j_settings,
        patch("src.common.services.redis_service.settings") as mock_redis_settings,
    ):
        # Configure mocked settings
        mock_pg_settings.POSTGRES_URL = postgres_url
        
        mock_neo4j_settings.NEO4J_URL = f"bolt://{neo4j_config['host']}:{neo4j_config['port']}"
        mock_neo4j_settings.NEO4J_USER = neo4j_config["user"]
        mock_neo4j_settings.NEO4J_PASSWORD = neo4j_config["password"]
        
        mock_redis_settings.REDIS_URL = redis_url

        # Create services
        postgres_svc = PostgreSQLService()
        neo4j_svc = Neo4jService()
        redis_svc = RedisService()

        # Connect all services
        await postgres_svc.connect()
        await neo4j_svc.connect()
        await redis_svc.connect()

        # Define concurrent operations
        async def postgres_query():
            async with postgres_svc.acquire() as conn:
                return await conn.fetchval("SELECT 'postgres' as db")

        async def neo4j_query():
            result = await neo4j_svc.execute("RETURN 'neo4j' as db")
            return result[0]["db"]

        async def redis_operation():
            await redis_svc.set("concurrent_test", "redis")
            value = await redis_svc.get("concurrent_test")
            await redis_svc.delete("concurrent_test")
            return value

        # Run concurrent operations
        results = await asyncio.gather(postgres_query(), neo4j_query(), redis_operation())
        assert results == ["postgres", "neo4j", "redis"]

        # Disconnect all services
        await postgres_svc.disconnect()
        await neo4j_svc.disconnect()
        await redis_svc.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_postgres_concurrent_queries(postgres_service):
    """Test handling multiple concurrent PostgreSQL queries."""
    config = postgres_service
    postgres_url = f"postgresql+asyncpg://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

    # Mock settings to use test configuration
    with patch("src.common.services.postgres_service.settings") as mock_settings:
        mock_settings.POSTGRES_URL = postgres_url

        service = PostgreSQLService()
        await service.connect()

        # Create multiple concurrent connections
        async def query_db(n):
            async with service.acquire() as conn:
                result = await conn.fetchval(f"SELECT {n}")
                return result

        # Run 10 concurrent queries
        tasks = [query_db(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert results == list(range(10))
        assert len(results) == 10

        await service.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_postgres_transaction_success(postgres_service):
    """Test successful database transaction with PostgreSQL."""
    config = postgres_service
    postgres_url = f"postgresql+asyncpg://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

    # Mock settings to use test configuration
    with patch("src.common.services.postgres_service.settings") as mock_settings:
        mock_settings.POSTGRES_URL = postgres_url

        service = PostgreSQLService()
        await service.connect()

        # Create a test table
        async with service.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transaction_test_table (
                    id SERIAL PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            # Clean up any existing data
            await conn.execute("TRUNCATE TABLE transaction_test_table")

        # Test successful transaction
        async with service.acquire() as conn, conn.transaction():
            await conn.execute("INSERT INTO transaction_test_table (value) VALUES ('test1')")
            await conn.execute("INSERT INTO transaction_test_table (value) VALUES ('test2')")

        # Verify data was inserted
        async with service.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM transaction_test_table")
            assert count == 2

            # Cleanup
            await conn.execute("DROP TABLE IF EXISTS transaction_test_table")

        await service.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_postgres_transaction_rollback(postgres_service):
    """Test database transaction rollback on error."""
    config = postgres_service
    postgres_url = f"postgresql+asyncpg://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

    # Mock settings to use test configuration
    with patch("src.common.services.postgres_service.settings") as mock_settings:
        mock_settings.POSTGRES_URL = postgres_url

        service = PostgreSQLService()
        await service.connect()

        # Create a test table
        async with service.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rollback_test_table (
                    id SERIAL PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            # Clean up any existing data
            await conn.execute("TRUNCATE TABLE rollback_test_table")

        # Test transaction rollback
        with suppress(Exception):
            async with service.acquire() as conn, conn.transaction():
                await conn.execute("INSERT INTO rollback_test_table (value) VALUES ('test1')")
                # Force an error
                await conn.execute("INVALID SQL")

        # Verify no data was inserted
        async with service.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM rollback_test_table")
            assert count == 0

            # Cleanup
            await conn.execute("DROP TABLE IF EXISTS rollback_test_table")

        await service.disconnect()