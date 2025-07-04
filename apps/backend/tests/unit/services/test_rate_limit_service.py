"""Unit tests for rate limiting service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.common.services.rate_limit_service import RateLimitService, RateLimitExceeded
from tests.unit.test_mocks import mock_redis


class TestRateLimitService:
    """Test cases for rate limiting service."""
    
    def test_init_service(self):
        """Test rate limit service initialization."""
        # Act
        service = RateLimitService()
        
        # Assert
        assert service is not None
        assert hasattr(service, 'check_rate_limit')
        assert hasattr(service, 'reset_rate_limit')
    
    def test_check_rate_limit_first_request(self):
        """Test rate limit check for first request."""
        # Arrange
        service = RateLimitService()
        key = "test_key"
        limit = 5
        window = 60
        
        # Act
        result = service.check_rate_limit(key, limit, window)
        
        # Assert
        assert result["allowed"] is True
        assert result["remaining"] == 4  # limit - 1
        assert result["reset_time"] > datetime.utcnow()
    
    @patch('src.common.services.rate_limit_service.redis_client', mock_redis)
    def test_check_rate_limit_within_limit(self):
        """Test rate limit check within allowed limit."""
        # Arrange
        service = RateLimitService()
        key = "test_key"
        limit = 5
        window = 60
        
        # Act - Make multiple requests
        for i in range(3):
            result = service.check_rate_limit(key, limit, window)
            assert result["allowed"] is True
        
        # Assert final state
        assert result["remaining"] == 2  # 5 - 3
    
    @patch('src.common.services.rate_limit_service.redis_client', mock_redis)
    def test_check_rate_limit_exceed_limit(self):
        """Test rate limit when limit is exceeded."""
        # Arrange
        service = RateLimitService()
        key = "test_key"
        limit = 3
        window = 60
        
        # Act - Make requests up to limit
        for i in range(3):
            result = service.check_rate_limit(key, limit, window)
            assert result["allowed"] is True
        
        # Act - Exceed limit
        result = service.check_rate_limit(key, limit, window)
        
        # Assert
        assert result["allowed"] is False
        assert result["remaining"] == 0
        assert "retry_after" in result
    
    @patch('src.common.services.rate_limit_service.redis_client', mock_redis)
    def test_check_rate_limit_raise_exception(self):
        """Test rate limit with raise_exception=True."""
        # Arrange
        service = RateLimitService()
        key = "test_key"
        limit = 2
        window = 60
        
        # Act - Make requests up to limit
        for i in range(2):
            service.check_rate_limit(key, limit, window)
        
        # Act & Assert - Should raise exception
        with pytest.raises(RateLimitExceeded) as exc_info:
            service.check_rate_limit(key, limit, window, raise_exception=True)
        
        assert "Rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.retry_after > 0
    
    @patch('src.common.services.rate_limit_service.redis_client', mock_redis)
    def test_check_rate_limit_different_keys(self):
        """Test rate limit with different keys are independent."""
        # Arrange
        service = RateLimitService()
        key1 = "user:123"
        key2 = "user:456"
        limit = 2
        window = 60
        
        # Act - Exhaust limit for key1
        for i in range(2):
            result = service.check_rate_limit(key1, limit, window)
            assert result["allowed"] is True
        
        result = service.check_rate_limit(key1, limit, window)
        assert result["allowed"] is False
        
        # Act - key2 should still be allowed
        result = service.check_rate_limit(key2, limit, window)
        
        # Assert
        assert result["allowed"] is True
        assert result["remaining"] == 1
    
    @patch('src.common.services.rate_limit_service.redis_client', mock_redis)
    def test_reset_rate_limit(self):
        """Test rate limit reset functionality."""
        # Arrange
        service = RateLimitService()
        key = "test_key"
        limit = 2
        window = 60
        
        # Act - Exhaust limit
        for i in range(2):
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
    
    @patch('src.common.services.rate_limit_service.redis_client', mock_redis)
    def test_get_rate_limit_info(self):
        """Test getting rate limit information without incrementing."""
        # Arrange
        service = RateLimitService()
        key = "test_key"
        limit = 5
        window = 60
        
        # Act - Make some requests
        for i in range(2):
            service.check_rate_limit(key, limit, window)
        
        # Act - Get info without incrementing
        info = service.get_rate_limit_info(key, limit, window)
        
        # Assert
        assert info["current"] == 2
        assert info["remaining"] == 3
        assert info["limit"] == 5
        assert "reset_time" in info