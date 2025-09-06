"""Unit tests for rate limiting service."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from src.common.services.rate_limit_service import RateLimitExceededError, RateLimitService
from tests.unit.test_mocks import mock_redis


class TestRateLimitService:
    """Test cases for rate limiting service."""

    def test_init_service(self):
        """Test rate limit service initialization."""
        # Act
        service = RateLimitService()

        # Assert
        assert service is not None
        assert hasattr(service, "check_rate_limit")
        assert hasattr(service, "reset_rate_limit")

    def test_check_rate_limit_first_request(self):
        """Test rate limit check for first request."""
        # Arrange
        service = RateLimitService()
        service._redis_client = mock_redis
        mock_redis.clear()
        key = "test_key"
        limit = 5
        window = 60

        # Act
        result = service.check_rate_limit(key, limit, window)

        # Assert
        assert result["allowed"] is True
        assert result["remaining"] == 4  # limit - 1
        assert result["reset_time"] > datetime.utcnow()

    def test_check_rate_limit_within_limit(self):
        """Test rate limit check within allowed limit."""
        # Arrange
        service = RateLimitService()
        service._redis_client = mock_redis
        mock_redis.clear()
        key = "test_key"
        limit = 5
        window = 60

        # Act - Make multiple requests
        for _i in range(3):
            result = service.check_rate_limit(key, limit, window)
            assert result["allowed"] is True

        # Assert final state
        assert result["remaining"] == 2  # 5 - 3

    def test_check_rate_limit_exceed_limit(self):
        """Test rate limit when limit is exceeded."""
        # Arrange
        service = RateLimitService()
        service._redis_client = mock_redis
        mock_redis.clear()
        key = "test_key"
        limit = 3
        window = 60

        # Act - Make requests up to limit
        for _i in range(3):
            result = service.check_rate_limit(key, limit, window)
            assert result["allowed"] is True

        # Act - Exceed limit
        result = service.check_rate_limit(key, limit, window)

        # Assert
        assert result["allowed"] is False
        assert result["remaining"] == 0
        assert "retry_after" in result

    def test_check_rate_limit_raise_exception(self):
        """Test rate limit with raise_exception=True."""
        # Arrange
        service = RateLimitService()
        service._redis_client = mock_redis
        mock_redis.clear()
        key = "test_key"
        limit = 2
        window = 60

        # Act - Make requests up to limit
        for _i in range(2):
            service.check_rate_limit(key, limit, window)

        # Act & Assert - Should raise exception
        with pytest.raises(RateLimitExceededError) as exc_info:
            service.check_rate_limit(key, limit, window, raise_exception=True)

        assert "Rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.retry_after > 0

    def test_check_rate_limit_different_keys(self):
        """Test rate limit with different keys are independent."""
        # Arrange
        service = RateLimitService()
        service._redis_client = mock_redis
        mock_redis.clear()
        key1 = "user:123"
        key2 = "user:456"
        limit = 2
        window = 60

        # Act - Exhaust limit for key1
        for _i in range(2):
            result = service.check_rate_limit(key1, limit, window)
            assert result["allowed"] is True

        result = service.check_rate_limit(key1, limit, window)
        assert result["allowed"] is False

        # Act - key2 should still be allowed
        result = service.check_rate_limit(key2, limit, window)

        # Assert
        assert result["allowed"] is True
        assert result["remaining"] == 1

    def test_reset_rate_limit(self):
        """Test rate limit reset functionality."""
        # Arrange
        service = RateLimitService()
        service._redis_client = mock_redis
        mock_redis.clear()
        key = "test_key"
        limit = 2
        window = 60

        # Act - Exhaust limit
        for _i in range(2):
            service.check_rate_limit(key, limit, window)

        result = service.check_rate_limit(key, limit, window)
        assert result["allowed"] is False

        # Act - Reset limit
        service.reset_rate_limit(key)

        # Act - Should be allowed again
        result = service.check_rate_limit(key, limit, window)

        # Assert
        assert result["allowed"] is True
        assert result["remaining"] == 1

    def test_get_rate_limit_info(self):
        """Test getting rate limit information without incrementing."""
        # Arrange
        service = RateLimitService()
        service._redis_client = mock_redis
        mock_redis.clear()
        key = "test_key"
        limit = 5
        window = 60

        # Act - Make some requests
        for _i in range(2):
            service.check_rate_limit(key, limit, window)

        # Act - Get info without incrementing
        info = service.get_rate_limit_info(key, limit, window)

        # Assert
        assert info["current"] == 2
        assert info["remaining"] == 3
        assert info["limit"] == 5
        assert "reset_time" in info

    def test_get_client_key_with_user_id(self):
        """Test client key generation with user ID."""
        # Arrange
        service = RateLimitService()
        mock_request = MagicMock()
        user_id = "user123"

        # Act
        key = service.get_client_key(mock_request, user_id)

        # Assert
        assert key == "user:user123"

    def test_get_client_key_with_ip(self):
        """Test client key generation with IP address."""
        # Arrange
        service = RateLimitService()
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.1"
        mock_request.headers.get.return_value = None

        # Act
        key = service.get_client_key(mock_request, None)

        # Assert
        assert key == "ip:192.168.1.1"

    def test_get_client_key_with_forwarded_for(self):
        """Test client key generation with X-Forwarded-For header."""
        # Arrange
        service = RateLimitService()
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.1"
        mock_request.headers.get.return_value = "203.0.113.1, 70.41.3.18"

        # Act
        key = service.get_client_key(mock_request, None)

        # Assert
        assert key == "ip:203.0.113.1"
