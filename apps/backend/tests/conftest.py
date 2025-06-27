"""Pytest configuration and shared fixtures."""

import asyncio
import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

# Configure remote Docker host if requested
if os.environ.get("USE_REMOTE_DOCKER", "false").lower() == "true":
    remote_docker_host = os.environ.get("REMOTE_DOCKER_HOST", "tcp://192.168.2.202:2375")
    os.environ["DOCKER_HOST"] = remote_docker_host
    # Only disable Ryuk if explicitly requested
    if os.environ.get("DISABLE_RYUK", "false").lower() == "true":
        os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Markers for different test types
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests requiring external services")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Tests that take a long time to run")


# Service configuration fixtures
@pytest.fixture(scope="session")
def use_external_services():
    """Check if we should use external services instead of testcontainers.

    This fixture determines whether to use:
    - External services at 192.168.2.201 (when USE_EXTERNAL_SERVICES=true)
    - Testcontainers with local or remote Docker (when USE_EXTERNAL_SERVICES=false)

    When using testcontainers, you can additionally set:
    - USE_REMOTE_DOCKER=true to use remote Docker host
    - REMOTE_DOCKER_HOST=tcp://192.168.2.202:2375 (or other host)
    - DISABLE_RYUK=true to disable Ryuk if needed (not recommended)
    """
    return os.environ.get("USE_EXTERNAL_SERVICES", "false").lower() == "true"


@pytest.fixture(scope="session")
def postgres_service(use_external_services):
    """Provide PostgreSQL connection configuration."""
    if use_external_services:
        # Use external service configuration from environment
        yield {
            "host": os.environ.get("POSTGRES_HOST", "localhost"),
            "port": int(os.environ.get("POSTGRES_PORT", "5432")),
            "user": os.environ.get("POSTGRES_USER", "postgres"),
            "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
            "database": os.environ.get("POSTGRES_DB", "test_db"),
        }
    else:
        # Use testcontainers for local or remote Docker
        from testcontainers.postgres import PostgresContainer

        postgres = None
        try:
            postgres = PostgresContainer("postgres:16")
            postgres.start()
            yield {
                "host": postgres.get_container_host_ip(),
                "port": postgres.get_exposed_port(5432),
                "user": postgres.username,
                "password": postgres.password,
                "database": postgres.dbname,
            }
        finally:
            # Ensure cleanup even if Ryuk fails
            if postgres:
                try:
                    postgres.stop()
                except Exception as e:
                    print(f"Warning: Failed to stop PostgreSQL container: {e}")


@pytest.fixture(scope="session")
def neo4j_service(use_external_services):
    """Provide Neo4j connection configuration."""
    if use_external_services:
        # Use external service configuration from environment
        yield {
            "host": os.environ.get("NEO4J_HOST", "localhost"),
            "port": int(os.environ.get("NEO4J_PORT", "7687")),
            "user": os.environ.get("NEO4J_USER", "neo4j"),
            "password": os.environ.get("NEO4J_PASSWORD", "neo4jtest"),
        }
    else:
        # Use testcontainers for local or remote Docker
        from testcontainers.neo4j import Neo4jContainer

        neo4j = None
        try:
            neo4j = Neo4jContainer("neo4j:5")
            neo4j.start()
            yield {
                "host": neo4j.get_container_host_ip(),
                "port": neo4j.get_exposed_port(7687),
                "user": "neo4j",
                "password": neo4j.password,
            }
        finally:
            # Ensure cleanup even if Ryuk fails
            if neo4j:
                try:
                    neo4j.stop()
                except Exception as e:
                    print(f"Warning: Failed to stop Neo4j container: {e}")


@pytest.fixture(scope="session")
def redis_service(use_external_services):
    """Provide Redis connection configuration."""
    if use_external_services:
        # Use external service configuration from environment
        yield {
            "host": os.environ.get("REDIS_HOST", "localhost"),
            "port": int(os.environ.get("REDIS_PORT", "6379")),
            "password": os.environ.get("REDIS_PASSWORD", ""),
        }
    else:
        # Use testcontainers for local or remote Docker
        from testcontainers.redis import RedisContainer

        redis = None
        try:
            redis = RedisContainer("redis:7-alpine")
            redis.start()
            yield {
                "host": redis.get_container_host_ip(),
                "port": redis.get_exposed_port(6379),
                "password": "",
            }
        finally:
            # Ensure cleanup even if Ryuk fails
            if redis:
                try:
                    redis.stop()
                except Exception as e:
                    print(f"Warning: Failed to stop Redis container: {e}")
