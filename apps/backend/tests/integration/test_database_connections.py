"""Integration tests for database connections using clean architecture."""

import asyncio
from contextlib import suppress
from unittest.mock import patch

import pytest
from src.common.services.neo4j_service import Neo4jService
from src.common.services.postgres_service import PostgreSQLService


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
async def test_concurrent_database_connections(postgres_service):
    """Test handling multiple concurrent database connections."""
    config = postgres_service
    postgres_url = f"postgresql+asyncpg://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

    # Mock settings to use test configuration
    with patch("src.common.services.postgres_service.settings") as mock_settings:
        mock_settings.POSTGRES_URL = postgres_url

        service = PostgreSQLService()
        await service.connect()

        # Create multiple concurrent connections
        async def query_db():
            async with service.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result

        # Run 10 concurrent queries
        tasks = [query_db() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert all(r == 1 for r in results)
        assert len(results) == 10

        await service.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_database_transaction_rollback(postgres_service):
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
                CREATE TABLE IF NOT EXISTS test_table (
                    id SERIAL PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

        # Test transaction rollback
        with suppress(Exception):
            async with service.acquire() as conn, conn.transaction():
                await conn.execute("INSERT INTO test_table (value) VALUES ('test')")
                # Force an error
                await conn.execute("INVALID SQL")

        # Verify no data was inserted
        async with service.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM test_table")
            assert count == 0

        await service.disconnect()
