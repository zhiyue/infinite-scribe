"""Shared pytest configuration for backend tests."""

import os

import pytest


@pytest.fixture
def postgres_service():
    """Provide PostgreSQL service configuration for tests."""
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "user": os.environ.get("POSTGRES_USER", "postgres"),
        "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "database": os.environ.get("POSTGRES_DB", "test_db"),
    }


@pytest.fixture
def neo4j_service():
    """Provide Neo4j service configuration for tests."""
    return {
        "host": os.environ.get("NEO4J_HOST", "localhost"),
        "port": int(os.environ.get("NEO4J_PORT", "7687")),
        "user": os.environ.get("NEO4J_USER", "neo4j"),
        "password": os.environ.get("NEO4J_PASSWORD", "neo4jtest"),
    }


@pytest.fixture
def redis_service():
    """Provide Redis service configuration for tests."""
    return {
        "host": os.environ.get("REDIS_HOST", "localhost"),
        "port": int(os.environ.get("REDIS_PORT", "6379")),
        "password": os.environ.get("REDIS_PASSWORD", ""),
    }

