"""Unit tests for rate limiting service."""

from unittest.mock import patch

import pytest
from src.common.services.rate_limit_service import RateLimitExceededError, RateLimitService


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

    @patch("src.common.services.rate_limit_service.RateLimitService.redis_client")
    def test_check_rate_limit_first_request(self, mock_redis_client):
        """Test rate limit check for first request."""
        # Arrange
        mock_redis_client.get.return_value = None
        mock_redis_client.setex.return_value = True
        service = RateLimitService()
        key = "test_key"
        limit = 5
        window = 60

        # Act
        result = service.check_rate_limit(key, limit, window)

        # Assert
        assert result["allowed"] is True
        assert result["remaining"] == 4  # limit - 1
        assert "reset_time" in result
        mock_redis_client.get.assert_called_once_with("rate_limit:test_key")
        mock_redis_client.setex.assert_called_once()

    @patch("src.common.services.rate_limit_service.RateLimitService.redis_client")
    def test_check_rate_limit_within_limit(self, mock_redis_client):
        """Test rate limit check within allowed limit."""
        import json
        import time

        # Arrange
        current_time = time.time()
        requests_data = [current_time - 30, current_time - 10]  # Two requests in window
        mock_redis_client.get.return_value = json.dumps({"requests": requests_data, "window": 60, "limit": 5})
        mock_redis_client.setex.return_value = True
        service = RateLimitService()
        key = "test_key"
        limit = 5
        window = 60

        # Act
        result = service.check_rate_limit(key, limit, window)

        # Assert
        assert result["allowed"] is True
        assert result["remaining"] == 2  # limit - 3 (2 existing + 1 new request = 3, so 5-3=2 remaining)
        mock_redis_client.get.assert_called_once_with("rate_limit:test_key")

    @patch("src.common.services.rate_limit_service.RateLimitService.redis_client")
    def test_check_rate_limit_exceed_limit(self, mock_redis_client):
        """Test rate limit when limit is exceeded."""
        import json
        import time

        # Arrange
        current_time = time.time()
        requests_data = [current_time - 50, current_time - 40, current_time - 30, current_time - 20, current_time - 10]
        mock_redis_client.get.return_value = json.dumps({"requests": requests_data, "window": 60, "limit": 5})
        service = RateLimitService()
        key = "test_key"
        limit = 5
        window = 60

        # Act
        result = service.check_rate_limit(key, limit, window)

        # Assert
        assert result["allowed"] is False
        assert result["remaining"] == 0
        assert "retry_after" in result
        mock_redis_client.get.assert_called_once_with("rate_limit:test_key")

    @patch("src.common.services.rate_limit_service.RateLimitService.redis_client")
    def test_check_rate_limit_raise_exception(self, mock_redis_client):
        """Test rate limit with raise_exception=True."""
        import json
        import time

        # Arrange
        current_time = time.time()
        requests_data = [current_time - 30, current_time - 10]  # At limit (2 requests)
        mock_redis_client.get.return_value = json.dumps({"requests": requests_data, "window": 60, "limit": 2})
        service = RateLimitService()
        key = "test_key"
        limit = 2
        window = 60

        # Act & Assert
        with pytest.raises(RateLimitExceededError) as exc_info:
            service.check_rate_limit(key, limit, window, raise_exception=True)

        assert "Rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.retry_after > 0

    @patch("src.common.services.rate_limit_service.RateLimitService.redis_client")
    def test_reset_rate_limit(self, mock_redis_client):
        """Test rate limit reset functionality."""
        # Arrange
        mock_redis_client.delete.return_value = 1
        service = RateLimitService()
        key = "test_key"

        # Act
        result = service.reset_rate_limit(key)

        # Assert
        assert result is None  # reset_rate_limit returns None
        mock_redis_client.delete.assert_called_once_with("rate_limit:test_key")

    @patch("src.common.services.rate_limit_service.RateLimitService.redis_client")
    def test_check_rate_limit_different_keys(self, mock_redis_client):
        """Test rate limit with different keys are independent."""
        import json
        import time

        # Arrange
        service = RateLimitService()
        current_time = time.time()

        # Mock responses for different keys
        def mock_get_side_effect(key):
            if key == "rate_limit:user:123":
                # Key1 has 2 requests already (at limit)
                requests_data = [current_time - 30, current_time - 10]
                return json.dumps({"requests": requests_data, "window": 60, "limit": 2})
            elif key == "rate_limit:user:456":
                # Key2 has no requests yet
                return None
            return None

        mock_redis_client.get.side_effect = mock_get_side_effect
        mock_redis_client.setex.return_value = True

        key1 = "user:123"
        key2 = "user:456"
        limit = 2
        window = 60

        # Act - key1 should be at limit
        result1 = service.check_rate_limit(key1, limit, window)

        # Act - key2 should still be allowed
        result2 = service.check_rate_limit(key2, limit, window)

        # Assert
        assert result1["allowed"] is False  # key1 at limit
        assert result2["allowed"] is True  # key2 still available
        assert result2["remaining"] == 1  # key2 has 1 remaining

    @patch("src.common.services.rate_limit_service.RateLimitService.redis_client")
    def test_get_rate_limit_info(self, mock_redis_client):
        """Test getting rate limit information without incrementing."""
        import json
        import time

        # Arrange
        service = RateLimitService()
        current_time = time.time()
        requests_data = [current_time - 30, current_time - 10]  # 2 requests
        mock_redis_client.get.return_value = json.dumps({"requests": requests_data, "window": 60, "limit": 5})

        key = "test_key"
        limit = 5
        window = 60

        # Act
        info = service.get_rate_limit_info(key, limit, window)

        # Assert
        assert info["current"] == 2
        assert info["remaining"] == 3
        assert info["limit"] == 5
        assert "reset_time" in info
        mock_redis_client.get.assert_called_once_with("rate_limit:test_key")

    def test_get_client_key_with_user_id(self):
        """Test client key generation with user ID."""
        from unittest.mock import MagicMock

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
        from unittest.mock import MagicMock

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
        from unittest.mock import MagicMock

        # Arrange
        service = RateLimitService()
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.1"
        mock_request.headers.get.return_value = "203.0.113.1, 70.41.3.18"

        # Act
        key = service.get_client_key(mock_request, None)

        # Assert
        assert key == "ip:203.0.113.1"
