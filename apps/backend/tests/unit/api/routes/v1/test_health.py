"""Unit tests for health check endpoint."""

from unittest.mock import patch

import pytest
from fastapi import status
from httpx import AsyncClient
from src.api.main import app


@pytest.mark.asyncio
async def test_health_check_success():
    """Test health check endpoint returns success when all services are healthy."""
    # Mock all service connections
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j,
        patch("src.common.services.redis_service.redis_service.check_connection") as mock_redis,
        patch("src.common.services.embedding_service.embedding_service.check_connection") as mock_embedding,
    ):
        mock_pg.return_value = True
        mock_neo4j.return_value = True
        mock_redis.return_value = True
        mock_embedding.return_value = True

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["services"] == {
            "database": "healthy",
            "neo4j": "healthy",
            "redis": "healthy",
            "embedding": "healthy",
        }


@pytest.mark.asyncio
async def test_health_check_postgres_failure():
    """Test health check endpoint returns error when PostgreSQL is down."""
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j,
        patch("src.common.services.redis_service.redis_service.check_connection") as mock_redis,
        patch("src.common.services.embedding_service.embedding_service.check_connection") as mock_embedding,
    ):
        mock_pg.return_value = False
        mock_neo4j.return_value = True
        mock_redis.return_value = True
        mock_embedding.return_value = True

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["services"]["database"] == "unhealthy"
        assert data["services"]["neo4j"] == "healthy"
        assert "failed" in data
        assert "database" in data["failed"]


@pytest.mark.asyncio
async def test_health_check_neo4j_failure():
    """Test health check endpoint returns error when Neo4j is down."""
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j,
        patch("src.common.services.redis_service.redis_service.check_connection") as mock_redis,
        patch("src.common.services.embedding_service.embedding_service.check_connection") as mock_embedding,
    ):
        mock_pg.return_value = True
        mock_neo4j.return_value = False
        mock_redis.return_value = True
        mock_embedding.return_value = True

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["services"]["database"] == "healthy"
        assert data["services"]["neo4j"] == "unhealthy"
        assert "failed" in data
        assert "neo4j" in data["failed"]


@pytest.mark.asyncio
async def test_health_check_all_services_failure():
    """Test health check endpoint when all services are down."""
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j,
        patch("src.common.services.redis_service.redis_service.check_connection") as mock_redis,
        patch("src.common.services.embedding_service.embedding_service.check_connection") as mock_embedding,
    ):
        mock_pg.return_value = False
        mock_neo4j.return_value = False
        mock_redis.return_value = False
        mock_embedding.return_value = False

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["services"]["database"] == "unhealthy"
        assert data["services"]["neo4j"] == "unhealthy"
        assert data["services"]["redis"] == "unhealthy"
        assert data["services"]["embedding"] == "unhealthy"
        assert len(data["failed"]) == 4


@pytest.mark.asyncio
async def test_health_check_exception_handling():
    """Test health check endpoint handles exceptions gracefully."""
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j,
        patch("src.common.services.redis_service.redis_service.check_connection") as mock_redis,
        patch("src.common.services.embedding_service.embedding_service.check_connection") as mock_embedding,
    ):
        mock_pg.side_effect = Exception("Connection failed")
        mock_neo4j.return_value = True
        mock_redis.return_value = True
        mock_embedding.return_value = True

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "detail" in data


@pytest.mark.asyncio
async def test_readiness_check_success():
    """Test readiness check endpoint returns success when all services are ready."""
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg_conn,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j_conn,
        patch("src.common.services.postgres_service.postgres_service.verify_schema") as mock_pg_schema,
        patch("src.common.services.neo4j_service.neo4j_service.verify_constraints") as mock_neo4j_constraints,
    ):
        mock_pg_conn.return_value = True
        mock_neo4j_conn.return_value = True
        mock_pg_schema.return_value = True
        mock_neo4j_constraints.return_value = True

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/ready")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ready", "service": "api-gateway"}


@pytest.mark.asyncio
async def test_readiness_check_connection_failure():
    """Test readiness check when database connections are not established."""
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg_conn,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j_conn,
    ):
        mock_pg_conn.return_value = False
        mock_neo4j_conn.return_value = True

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/ready")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "not ready"
        assert "Database connections not established" in data["reason"]


@pytest.mark.asyncio
async def test_readiness_check_schema_failure():
    """Test readiness check when schema verification fails."""
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg_conn,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j_conn,
        patch("src.common.services.postgres_service.postgres_service.verify_schema") as mock_pg_schema,
        patch("src.common.services.neo4j_service.neo4j_service.verify_constraints") as mock_neo4j_constraints,
    ):
        mock_pg_conn.return_value = True
        mock_neo4j_conn.return_value = True
        mock_pg_schema.return_value = False
        mock_neo4j_constraints.return_value = True

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/ready")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "not ready"
        assert data["postgres_schema"] is False
        assert data["neo4j_constraints"] is True


@pytest.mark.asyncio
async def test_readiness_check_exception():
    """Test readiness check handles exceptions gracefully."""
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg_conn,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j_conn,
    ):
        mock_pg_conn.side_effect = Exception("Database error")
        mock_neo4j_conn.return_value = True

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/ready")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "error"
        assert "Database error" in data["detail"]
