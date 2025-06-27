"""Integration tests for database connections using testcontainers."""

import asyncio
import os
from contextlib import suppress
from unittest.mock import patch

import pytest
from src.common.services.neo4j_service import Neo4jService
from src.common.services.postgres_service import PostgreSQLService
from testcontainers.compose import DockerCompose
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="module")
def postgres_container():
    """Fixture to start PostgreSQL container for testing."""
    with PostgresContainer("postgres:16") as postgres:
        postgres.with_env("POSTGRES_DB", "test_infinite_scribe")
        yield postgres


@pytest.fixture(scope="module")
def neo4j_compose():
    """Fixture to start Neo4j using docker-compose for testing."""
    # Use a minimal docker-compose for Neo4j
    compose_content = """
version: '3.8'
services:
  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/testpassword
    ports:
      - "7687:7687"
      - "7474:7474"
"""
    # Write temporary compose file
    with open("test-neo4j-compose.yml", "w") as f:
        f.write(compose_content)

    with DockerCompose(".", compose_file_name="test-neo4j-compose.yml") as compose:
        # Wait for Neo4j to be ready
        import time

        time.sleep(10)  # Give Neo4j time to start
        yield compose

    # Cleanup
    os.remove("test-neo4j-compose.yml")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_postgres_connection_success(postgres_container):
    """Test successful PostgreSQL connection."""
    # Create PostgreSQL URL for test container
    postgres_url = f"postgresql+asyncpg://{postgres_container.username}:{postgres_container.password}@{postgres_container.get_container_host_ip()}:{postgres_container.get_exposed_port(5432)}/{postgres_container.dbname}"

    # Mock settings to use test container
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
async def test_neo4j_connection_success(neo4j_compose):
    """Test successful Neo4j connection."""
    # Mock settings for Neo4j test container
    with patch("src.common.services.neo4j_service.settings") as mock_settings:
        mock_settings.NEO4J_URL = "bolt://localhost:7687"
        mock_settings.NEO4J_USER = "neo4j"
        mock_settings.NEO4J_PASSWORD = "testpassword"

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
async def test_concurrent_database_connections(postgres_container):
    """Test handling multiple concurrent database connections."""
    # Create PostgreSQL URL for test container
    postgres_url = f"postgresql+asyncpg://{postgres_container.username}:{postgres_container.password}@{postgres_container.get_container_host_ip()}:{postgres_container.get_exposed_port(5432)}/{postgres_container.dbname}"

    # Mock settings to use test container
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
async def test_database_transaction_rollback(postgres_container):
    """Test database transaction rollback on error."""
    # Create PostgreSQL URL for test container
    postgres_url = f"postgresql+asyncpg://{postgres_container.username}:{postgres_container.password}@{postgres_container.get_container_host_ip()}:{postgres_container.get_exposed_port(5432)}/{postgres_container.dbname}"

    # Mock settings to use test container
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
