"""Unit tests for rate limiting middleware."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, Request
from src.common.services.rate_limit_service import RateLimitExceededError
from src.middleware.rate_limit import (
    RateLimitMiddleware,
    create_rate_limit_decorator,
    login_rate_limit,
    password_reset_rate_limit,
    register_rate_limit,
)
from starlette.types import ASGIApp


class TestRateLimitMiddleware:
    """Test cases for RateLimitMiddleware."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock ASGI app."""
        app = AsyncMock(spec=ASGIApp)
        return app

    @pytest.fixture
    def middleware(self, mock_app):
        """Create middleware instance."""
        return RateLimitMiddleware(mock_app)

    @pytest.fixture
    def http_scope(self):
        """Create a basic HTTP scope."""
        return {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "query_string": b"",
            "headers": [(b"host", b"localhost:8000")],
        }

    @pytest.mark.asyncio
    async def test_health_check_bypass(self, middleware, mock_app, http_scope):
        """Test that health check endpoints bypass rate limiting."""
        # Arrange
        http_scope["path"] = "/health"
        receive = AsyncMock()
        send = AsyncMock()

        # Act
        await middleware(http_scope, receive, send)

        # Assert
        mock_app.assert_called_once_with(http_scope, receive, send)

    @pytest.mark.asyncio
    async def test_docs_bypass(self, middleware, mock_app, http_scope):
        """Test that docs endpoints bypass rate limiting."""
        # Arrange
        http_scope["path"] = "/docs"
        receive = AsyncMock()
        send = AsyncMock()

        # Act
        await middleware(http_scope, receive, send)

        # Assert
        mock_app.assert_called_once_with(http_scope, receive, send)

    @pytest.mark.asyncio
    @patch("src.middleware.rate_limit.rate_limit_service")
    async def test_rate_limit_check_success(self, mock_rate_limit_service, middleware, mock_app, http_scope):
        """Test successful rate limit check."""
        # Arrange
        receive = AsyncMock()
        send = AsyncMock()
        mock_rate_limit_service.get_client_key.return_value = "test_key"
        mock_rate_limit_service.check_rate_limit.return_value = None

        # Act
        await middleware(http_scope, receive, send)

        # Assert
        mock_app.assert_called_once_with(http_scope, receive, send)
        mock_rate_limit_service.get_client_key.assert_called_once()
        mock_rate_limit_service.check_rate_limit.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.middleware.rate_limit.rate_limit_service")
    async def test_rate_limit_exceeded(self, mock_rate_limit_service, middleware, mock_app, http_scope):
        """Test rate limit exceeded response."""
        # Arrange
        receive = AsyncMock()
        send = AsyncMock()
        mock_rate_limit_service.get_client_key.return_value = "test_key"

        # Simulate rate limit exceeded
        exc = RateLimitExceededError("Rate limit exceeded", retry_after=60)
        mock_rate_limit_service.check_rate_limit.side_effect = exc

        # Act
        await middleware(http_scope, receive, send)

        # Assert
        # The app should not be called
        mock_app.assert_not_called()

        # The send function should be called with error response
        # Check that send was called multiple times (for status, headers, body)
        assert send.call_count > 0

    @pytest.mark.asyncio
    async def test_non_http_scope(self, middleware, mock_app):
        """Test that non-HTTP scope bypasses middleware."""
        # Arrange
        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        # Act
        await middleware(scope, receive, send)

        # Assert
        mock_app.assert_called_once_with(scope, receive, send)

    def test_get_rate_limits_login(self, middleware):
        """Test rate limits for login endpoint."""
        limits = middleware._get_rate_limits("/api/v1/auth/login", "POST")
        assert limits == (5, 60)  # 5 requests per minute

    def test_get_rate_limits_register(self, middleware):
        """Test rate limits for register endpoint."""
        limits = middleware._get_rate_limits("/api/v1/auth/register", "POST")
        assert limits == (10, 300)  # 10 requests per 5 minutes

    def test_get_rate_limits_forgot_password(self, middleware):
        """Test rate limits for forgot password endpoint."""
        limits = middleware._get_rate_limits("/api/v1/auth/forgot-password", "POST")
        assert limits == (3, 3600)  # 3 requests per hour

    def test_get_rate_limits_reset_password(self, middleware):
        """Test rate limits for reset password endpoint."""
        limits = middleware._get_rate_limits("/api/v1/auth/reset-password", "POST")
        assert limits == (5, 3600)  # 5 requests per hour

    def test_get_rate_limits_resend_verification(self, middleware):
        """Test rate limits for resend verification endpoint."""
        limits = middleware._get_rate_limits("/api/v1/auth/resend-verification", "POST")
        assert limits == (3, 300)  # 3 requests per 5 minutes

    def test_get_rate_limits_other_auth(self, middleware):
        """Test rate limits for other auth endpoints."""
        limits = middleware._get_rate_limits("/api/v1/auth/profile", "GET")
        assert limits == (60, 60)  # 60 requests per minute

    def test_get_rate_limits_general_api(self, middleware):
        """Test rate limits for general API endpoints."""
        limits = middleware._get_rate_limits("/api/v1/users", "GET")
        assert limits == (100, 60)  # 100 requests per minute


class TestRateLimitDecorator:
    """Test cases for rate limit decorator."""

    @pytest.mark.asyncio
    @patch("src.middleware.rate_limit.rate_limit_service")
    async def test_create_rate_limit_decorator_success(self, mock_rate_limit_service):
        """Test rate limit decorator when limit is not exceeded."""
        # Arrange
        mock_request = Mock(spec=Request)
        mock_request.state.user_id = "123"
        mock_rate_limit_service.get_client_key.return_value = "test_key"
        mock_rate_limit_service.check_rate_limit.return_value = None

        # Create a test function
        @create_rate_limit_decorator(5, 60)
        async def test_func(request: Request):
            return {"success": True}

        # Act
        result = await test_func(mock_request)

        # Assert
        assert result == {"success": True}
        mock_rate_limit_service.get_client_key.assert_called_once_with(mock_request, "123")
        mock_rate_limit_service.check_rate_limit.assert_called_once_with("test_key", 5, 60, raise_exception=True)

    @pytest.mark.asyncio
    @patch("src.middleware.rate_limit.rate_limit_service")
    async def test_create_rate_limit_decorator_exceeded(self, mock_rate_limit_service):
        """Test rate limit decorator when limit is exceeded."""
        # Arrange
        mock_request = Mock(spec=Request)
        mock_request.state.user_id = None
        mock_rate_limit_service.get_client_key.return_value = "test_key"

        # Simulate rate limit exceeded
        exc = RateLimitExceededError("Rate limit exceeded", retry_after=60)
        mock_rate_limit_service.check_rate_limit.side_effect = exc

        # Create a test function
        @create_rate_limit_decorator(5, 60)
        async def test_func(request: Request):
            return {"success": True}

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await test_func(mock_request)

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail == "Rate limit exceeded"
        assert exc_info.value.headers["Retry-After"] == "60"

    @pytest.mark.asyncio
    async def test_decorator_without_request(self):
        """Test decorator when request is not in arguments."""

        # Create a test function without request parameter
        @create_rate_limit_decorator(5, 60)
        async def test_func(value: str):
            return {"value": value}

        # Act
        result = await test_func("test")

        # Assert
        assert result == {"value": "test"}

    def test_predefined_decorators(self):
        """Test that predefined decorators are created correctly."""
        # These should not raise any errors
        assert login_rate_limit is not None
        assert register_rate_limit is not None
        assert password_reset_rate_limit is not None
