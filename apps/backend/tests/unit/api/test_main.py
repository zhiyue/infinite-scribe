"""Unit tests for API main module."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.main import app, lifespan


class TestMainApp:
    """Test cases for main app configuration."""

    def test_app_instance(self):
        """Test FastAPI app instance configuration."""
        assert isinstance(app, FastAPI)
        assert app.title == "Infinite Scribe API Gateway"
        assert app.description == "API Gateway for the Infinite Scribe platform"
        assert app.version == "0.1.0"

    def test_cors_middleware_configured(self):
        """Test CORS middleware is properly configured."""
        # 检查中间件是否已配置
        middleware_classes = [m.cls for m in app.user_middleware]
        assert CORSMiddleware in middleware_classes

    def test_routers_included(self):
        """Test all routers are included."""
        # 检查路由是否已包含
        route_paths = [route.path for route in app.routes]

        # 健康检查路由
        assert any("/health" in path for path in route_paths)

        # API v1 路由前缀
        assert any("/api/v1" in path for path in route_paths)


class TestLifespan:
    """Test cases for application lifespan management."""

    @pytest.mark.asyncio
    @patch("src.common.services.postgres_service.postgres_service")
    @patch("src.common.services.neo4j_service.neo4j_service")
    @patch("src.common.services.redis_service.redis_service")
    @patch("logging.getLogger")
    async def test_lifespan_startup_success(self, mock_logger, mock_redis, mock_neo4j, mock_postgres):
        """Test successful startup sequence."""
        # Setup mocks
        mock_log = AsyncMock()
        mock_logger.return_value = mock_log

        # Mock service connections
        mock_postgres.connect = AsyncMock()
        mock_neo4j.connect = AsyncMock()
        mock_redis.connect = AsyncMock()

        # Mock connection checks
        mock_postgres.check_connection = AsyncMock(return_value=True)
        mock_neo4j.check_connection = AsyncMock(return_value=True)
        mock_redis.check_connection = AsyncMock(return_value=True)

        # Mock service disconnections
        mock_postgres.disconnect = AsyncMock()
        mock_neo4j.disconnect = AsyncMock()
        mock_redis.disconnect = AsyncMock()

        # Execute lifespan
        test_app = FastAPI()
        async with lifespan(test_app):
            # Verify startup calls
            mock_postgres.connect.assert_called_once()
            mock_neo4j.connect.assert_called_once()
            mock_redis.connect.assert_called_once()

            mock_postgres.check_connection.assert_called_once()
            mock_neo4j.check_connection.assert_called_once()
            mock_redis.check_connection.assert_called_once()

        # Verify shutdown calls
        mock_postgres.disconnect.assert_called_once()
        mock_neo4j.disconnect.assert_called_once()
        mock_redis.disconnect.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.common.services.postgres_service.postgres_service")
    @patch("src.common.services.neo4j_service.neo4j_service")
    @patch("src.common.services.redis_service.redis_service")
    @patch("logging.getLogger")
    async def test_lifespan_startup_connection_failures(self, mock_logger, mock_redis, mock_neo4j, mock_postgres):
        """Test startup sequence with connection failures."""
        # Setup mocks
        mock_log = AsyncMock()
        mock_logger.return_value = mock_log

        # Mock service connections
        mock_postgres.connect = AsyncMock()
        mock_neo4j.connect = AsyncMock()
        mock_redis.connect = AsyncMock()

        # Mock connection check failures
        mock_postgres.check_connection = AsyncMock(return_value=False)
        mock_neo4j.check_connection = AsyncMock(return_value=False)
        mock_redis.check_connection = AsyncMock(return_value=False)

        # Mock service disconnections
        mock_postgres.disconnect = AsyncMock()
        mock_neo4j.disconnect = AsyncMock()
        mock_redis.disconnect = AsyncMock()

        # Execute lifespan
        test_app = FastAPI()
        async with lifespan(test_app):
            # Verify connections were attempted
            mock_postgres.connect.assert_called_once()
            mock_neo4j.connect.assert_called_once()
            mock_redis.connect.assert_called_once()

            # Verify connection checks were performed
            mock_postgres.check_connection.assert_called_once()
            mock_neo4j.check_connection.assert_called_once()
            mock_redis.check_connection.assert_called_once()

        # Verify shutdown still happens
        mock_postgres.disconnect.assert_called_once()
        mock_neo4j.disconnect.assert_called_once()
        mock_redis.disconnect.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.common.services.postgres_service.postgres_service")
    @patch("src.common.services.neo4j_service.neo4j_service")
    @patch("src.common.services.redis_service.redis_service")
    @patch("logging.getLogger")
    async def test_lifespan_startup_exception(self, mock_logger, mock_redis, mock_neo4j, mock_postgres):
        """Test startup sequence with exception during initialization."""
        # Setup mocks
        mock_log = AsyncMock()
        mock_logger.return_value = mock_log

        # Mock service connection failure
        mock_postgres.connect = AsyncMock(side_effect=Exception("Connection failed"))
        mock_neo4j.connect = AsyncMock()
        mock_redis.connect = AsyncMock()

        # Mock service disconnections
        mock_postgres.disconnect = AsyncMock()
        mock_neo4j.disconnect = AsyncMock()
        mock_redis.disconnect = AsyncMock()

        # Execute lifespan
        test_app = FastAPI()
        async with lifespan(test_app):
            # Verify connection attempt was made
            mock_postgres.connect.assert_called_once()

        # Verify shutdown still happens
        mock_postgres.disconnect.assert_called_once()
        mock_neo4j.disconnect.assert_called_once()
        mock_redis.disconnect.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.common.services.postgres_service.postgres_service")
    @patch("src.common.services.neo4j_service.neo4j_service")
    @patch("src.common.services.redis_service.redis_service")
    @patch("logging.getLogger")
    async def test_lifespan_shutdown_exception(self, mock_logger, mock_redis, mock_neo4j, mock_postgres):
        """Test shutdown sequence with exception during cleanup."""
        # Setup mocks
        mock_log = AsyncMock()
        mock_logger.return_value = mock_log

        # Mock service connections
        mock_postgres.connect = AsyncMock()
        mock_neo4j.connect = AsyncMock()
        mock_redis.connect = AsyncMock()

        # Mock connection checks
        mock_postgres.check_connection = AsyncMock(return_value=True)
        mock_neo4j.check_connection = AsyncMock(return_value=True)
        mock_redis.check_connection = AsyncMock(return_value=True)

        # Mock service disconnection failure
        mock_postgres.disconnect = AsyncMock(side_effect=Exception("Disconnect failed"))
        mock_neo4j.disconnect = AsyncMock()
        mock_redis.disconnect = AsyncMock()

        # Execute lifespan - should not raise exception
        test_app = FastAPI()
        async with lifespan(test_app):
            pass

        # Verify only postgres disconnect was attempted (others not called due to exception)
        mock_postgres.disconnect.assert_called_once()
        mock_neo4j.disconnect.assert_not_called()
        mock_redis.disconnect.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.common.services.postgres_service.postgres_service")
    @patch("src.common.services.neo4j_service.neo4j_service")
    @patch("src.common.services.redis_service.redis_service")
    @patch("logging.getLogger")
    async def test_lifespan_mixed_connection_status(self, mock_logger, mock_redis, mock_neo4j, mock_postgres):
        """Test startup with mixed connection status (some succeed, some fail)."""
        # Setup mocks
        mock_log = AsyncMock()
        mock_logger.return_value = mock_log

        # Mock service connections
        mock_postgres.connect = AsyncMock()
        mock_neo4j.connect = AsyncMock()
        mock_redis.connect = AsyncMock()

        # Mock mixed connection check results
        mock_postgres.check_connection = AsyncMock(return_value=True)
        mock_neo4j.check_connection = AsyncMock(return_value=False)
        mock_redis.check_connection = AsyncMock(return_value=True)

        # Mock service disconnections
        mock_postgres.disconnect = AsyncMock()
        mock_neo4j.disconnect = AsyncMock()
        mock_redis.disconnect = AsyncMock()

        # Execute lifespan
        test_app = FastAPI()
        async with lifespan(test_app):
            # Verify all connections were attempted
            mock_postgres.connect.assert_called_once()
            mock_neo4j.connect.assert_called_once()
            mock_redis.connect.assert_called_once()

            # Verify all connection checks were performed
            mock_postgres.check_connection.assert_called_once()
            mock_neo4j.check_connection.assert_called_once()
            mock_redis.check_connection.assert_called_once()

        # Verify shutdown still happens for all services
        mock_postgres.disconnect.assert_called_once()
        mock_neo4j.disconnect.assert_called_once()
        mock_redis.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_context_manager_protocol(self):
        """Test lifespan follows async context manager protocol."""
        test_app = FastAPI()

        # Test that lifespan can be used as async context manager
        with patch("src.common.services.postgres_service.postgres_service"), \
             patch("src.common.services.neo4j_service.neo4j_service"), \
             patch("src.common.services.redis_service.redis_service"), \
             patch("logging.getLogger"):

            context_manager = lifespan(test_app)

            # Should have __aenter__ and __aexit__ methods
            assert hasattr(context_manager, '__aenter__')
            assert hasattr(context_manager, '__aexit__')

            # Should be able to enter and exit
            async with context_manager:
                pass
