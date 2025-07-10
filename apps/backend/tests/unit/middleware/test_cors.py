"""Unit tests for CORS middleware."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.middleware.cors import add_cors_middleware, add_security_headers_middleware


class TestCORSMiddleware:
    """Test cases for CORS middleware configuration."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        return app

    @patch("src.middleware.cors.settings")
    def test_add_cors_middleware_dev_mode(self, mock_settings, app):
        """Test CORS middleware configuration in development mode."""
        # Arrange
        mock_settings.is_dev = True

        # Act
        add_cors_middleware(app)

        # Assert
        # Check that middleware was added
        middlewares = [m for m in app.user_middleware]
        cors_middleware_found = False
        for middleware in middlewares:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware_found = True
                # In dev mode, all origins are allowed (["*"])
                assert middleware.kwargs["allow_origins"] == ["*"]
                assert middleware.kwargs["allow_credentials"] is True
                assert "GET" in middleware.kwargs["allow_methods"]
                assert "POST" in middleware.kwargs["allow_methods"]
                assert "Authorization" in middleware.kwargs["allow_headers"]
                break

        assert cors_middleware_found is True

    @patch("src.middleware.cors.settings")
    def test_add_cors_middleware_prod_mode(self, mock_settings, app):
        """Test CORS middleware configuration in production mode."""
        # Arrange
        mock_settings.is_dev = False

        # Act
        add_cors_middleware(app)

        # Assert
        middlewares = [m for m in app.user_middleware]
        cors_middleware = None
        for middleware in middlewares:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break

        assert cors_middleware is not None
        # In production, specific origins should be allowed
        allowed_origins = cors_middleware.kwargs["allow_origins"]
        assert "http://localhost:3000" in allowed_origins
        assert "https://yourdomain.com" in allowed_origins
        assert "https://www.yourdomain.com" in allowed_origins
        assert cors_middleware.kwargs["max_age"] == 86400  # 24 hours

    @patch("src.middleware.cors.settings")
    def test_cors_headers_in_response(self, mock_settings, app):
        """Test that CORS headers are present in response."""
        # Arrange
        mock_settings.is_dev = True
        add_cors_middleware(app)
        client = TestClient(app)

        # Act
        response = client.options(
            "/test",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Assert
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") is not None
        assert response.headers.get("access-control-allow-methods") is not None


class TestSecurityHeadersMiddleware:
    """Test cases for security headers middleware."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        return app

    @patch("src.middleware.cors.settings")
    @pytest.mark.asyncio
    async def test_add_security_headers_middleware_dev(self, mock_settings, app):
        """Test security headers in development mode."""
        # Arrange
        mock_settings.is_dev = True
        add_security_headers_middleware(app)
        client = TestClient(app)

        # Act
        response = client.get("/test")

        # Assert
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Strict-Transport-Security" not in response.headers  # Not in dev mode
        assert "Content-Security-Policy" in response.headers

    @patch("src.middleware.cors.settings")
    @pytest.mark.asyncio
    async def test_add_security_headers_middleware_prod(self, mock_settings, app):
        """Test security headers in production mode."""
        # Arrange
        mock_settings.is_dev = False
        add_security_headers_middleware(app)
        client = TestClient(app)

        # Act
        response = client.get("/test")

        # Assert
        assert response.status_code == 200
        assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"

    @patch("src.middleware.cors.settings")
    @pytest.mark.asyncio
    async def test_csp_header_content(self, mock_settings, app):
        """Test Content Security Policy header content."""
        # Arrange
        mock_settings.is_dev = True
        add_security_headers_middleware(app)
        client = TestClient(app)

        # Act
        response = client.get("/test")

        # Assert
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "script-src 'self' 'unsafe-inline' 'unsafe-eval'" in csp
        assert "style-src 'self' 'unsafe-inline'" in csp
        assert "img-src 'self' data: https:" in csp
        assert "frame-ancestors 'none'" in csp
