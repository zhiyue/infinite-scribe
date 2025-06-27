"""Unit tests for health check endpoint."""

from unittest.mock import patch

import pytest
from fastapi import status
from httpx import AsyncClient
from src.api.main import app


@pytest.mark.asyncio
async def test_health_check_success():
    """Test health check endpoint returns success when all services are healthy."""
    # Mock successful database connections
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j,
    ):
        mock_pg.return_value = True
        mock_neo4j.return_value = True

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_check_postgres_failure():
    """Test health check endpoint returns error when PostgreSQL is down."""
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j,
    ):
        mock_pg.return_value = False
        mock_neo4j.return_value = True

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["postgres"] is False
        assert data["neo4j"] is True


@pytest.mark.asyncio
async def test_health_check_neo4j_failure():
    """Test health check endpoint returns error when Neo4j is down."""
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j,
    ):
        mock_pg.return_value = True
        mock_neo4j.return_value = False

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["postgres"] is True
        assert data["neo4j"] is False


@pytest.mark.asyncio
async def test_health_check_all_services_failure():
    """Test health check endpoint when all services are down."""
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j,
    ):
        mock_pg.return_value = False
        mock_neo4j.return_value = False

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["postgres"] is False
        assert data["neo4j"] is False


@pytest.mark.asyncio
async def test_health_check_exception_handling():
    """Test health check endpoint handles exceptions gracefully."""
    with (
        patch("src.common.services.postgres_service.postgres_service.check_connection") as mock_pg,
        patch("src.common.services.neo4j_service.neo4j_service.check_connection") as mock_neo4j,
    ):
        mock_pg.side_effect = Exception("Connection failed")
        mock_neo4j.return_value = True

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "detail" in data
