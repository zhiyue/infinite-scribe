"""Unit tests for configuration management."""

import os
from unittest.mock import patch

import pytest
from src.core.config import Settings


@pytest.fixture(autouse=True)
def clean_environment():
    """Clear database-related environment variables for tests."""
    env_vars_to_clear = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "NEO4J_HOST",
        "NEO4J_PORT",
        "NEO4J_USER",
        "NEO4J_PASSWORD",
        "NEO4J_URI",
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_PASSWORD",
        "USE_EXTERNAL_SERVICES",
    ]

    # Store original values
    original_values = {var: os.environ.get(var) for var in env_vars_to_clear}

    # Clear the variables
    for var in env_vars_to_clear:
        if var in os.environ:
            del os.environ[var]

    yield

    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value


def test_default_settings():
    """Test default settings are loaded correctly."""
    settings = Settings()

    assert settings.SERVICE_NAME == "infinite-scribe-backend"
    assert settings.SERVICE_TYPE == "api-gateway"
    assert settings.API_HOST == "0.0.0.0"
    assert settings.API_PORT == 8000
    assert settings.POSTGRES_HOST == "postgres"
    assert settings.POSTGRES_PORT == 5432
    assert settings.POSTGRES_USER == "postgres"
    assert settings.POSTGRES_DB == "infinite_scribe"


def test_postgres_url_generation():
    """Test PostgreSQL URL is generated correctly."""
    settings = Settings()
    expected_url = "postgresql+asyncpg://postgres:postgres@postgres:5432/infinite_scribe"
    assert expected_url == settings.POSTGRES_URL


def test_neo4j_url_generation():
    """Test Neo4j URL is generated correctly."""
    settings = Settings()
    expected_url = "bolt://neo4j:7687"
    assert expected_url == settings.NEO4J_URL


def test_neo4j_url_with_uri_override():
    """Test Neo4j URL uses NEO4J_URI if provided."""
    with patch.dict(os.environ, {"NEO4J_URI": "bolt://custom-neo4j:7688"}):
        settings = Settings()
        assert settings.NEO4J_URL == "bolt://custom-neo4j:7688"


def test_redis_url_generation():
    """Test Redis URL is generated correctly."""
    settings = Settings()
    expected_url = "redis://:redis@redis:6379/0"
    assert expected_url == settings.REDIS_URL


def test_environment_variable_override():
    """Test environment variables override default settings."""
    env_vars = {
        "SERVICE_NAME": "test-service",
        "API_PORT": "9000",
        "POSTGRES_HOST": "test-postgres",
        "POSTGRES_PASSWORD": "test-password",
        "NEO4J_USER": "test-neo4j-user",
        "KAFKA_BOOTSTRAP_SERVERS": "test-kafka:9092",
    }

    with patch.dict(os.environ, env_vars):
        settings = Settings()

        assert settings.SERVICE_NAME == "test-service"
        assert settings.API_PORT == 9000
        assert settings.POSTGRES_HOST == "test-postgres"
        assert settings.POSTGRES_PASSWORD == "test-password"
        assert settings.NEO4J_USER == "test-neo4j-user"
        assert settings.KAFKA_BOOTSTRAP_SERVERS == "test-kafka:9092"


def test_allowed_origins_list():
    """Test ALLOWED_ORIGINS is properly parsed as a list."""
    settings = Settings()
    assert isinstance(settings.ALLOWED_ORIGINS, list)
    assert settings.ALLOWED_ORIGINS == ["*"]


def test_case_sensitive_environment_variables():
    """Test that environment variables are case sensitive."""
    with patch.dict(os.environ, {"api_port": "9000", "API_PORT": "8080"}):
        settings = Settings()
        # Should use API_PORT (uppercase) due to case_sensitive=True
        assert settings.API_PORT == 8080
