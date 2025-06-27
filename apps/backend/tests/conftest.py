"""Pytest configuration and shared fixtures."""

import asyncio
import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

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
    """Check if we should use external services instead of testcontainers."""
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
        # Use testcontainers for local development
        from testcontainers.postgres import PostgresContainer

        with PostgresContainer("postgres:16") as postgres:
            yield {
                "host": postgres.get_container_host_ip(),
                "port": postgres.get_exposed_port(5432),
                "user": postgres.username,
                "password": postgres.password,
                "database": postgres.dbname,
            }


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
        # Use testcontainers for local development
        from testcontainers.neo4j import Neo4jContainer

        with Neo4jContainer("neo4j:5") as neo4j:
            yield {
                "host": neo4j.get_container_host_ip(),
                "port": neo4j.get_exposed_port(7687),
                "user": "neo4j",
                "password": neo4j.password,
            }


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
        # Use testcontainers for local development
        from testcontainers.redis import RedisContainer

        with RedisContainer("redis:7-alpine") as redis:
            yield {
                "host": redis.get_container_host_ip(),
                "port": redis.get_exposed_port(6379),
                "password": "",
            }
