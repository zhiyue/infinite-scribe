"""Unit tests for JWT service Redis fault tolerance."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, PropertyMock, patch

import pytest
from redis.exceptions import ConnectionError, TimeoutError
from src.common.services.user.auth_service import AuthService


class TestAuthServiceRedisFaultTolerance:
    """Test cases for Auth service Redis fault tolerance."""

    @pytest.fixture
    def auth_service(self) -> AuthService:
        """Create JWT service instance."""
        return AuthService()

    @pytest.fixture
    def mock_redis_with_error(self):
        """Mock Redis client that raises errors."""
        mock = Mock()
        mock.get.side_effect = ConnectionError("Connection reset by peer")
        mock.setex.side_effect = ConnectionError("Connection reset by peer")
        return mock

    def test_is_token_blacklisted_with_connection_error(self, auth_service: AuthService):
        """Test checking blacklist when Redis connection fails."""
        # Mock the redis_client property to raise ConnectionError
        with patch.object(AuthService, "redis_client", new_callable=PropertyMock) as mock_redis_prop:
            mock_redis = Mock()
            mock_redis.get.side_effect = ConnectionError("Connection reset by peer")
            mock_redis_prop.return_value = mock_redis

            # Should return False instead of raising exception
            result = auth_service.is_token_blacklisted("test-jti")
            assert result is False

    def test_is_token_blacklisted_with_timeout_error(self, auth_service: AuthService):
        """Test checking blacklist when Redis times out."""
        with patch.object(AuthService, "redis_client", new_callable=PropertyMock) as mock_redis_prop:
            mock_redis = Mock()
            mock_redis.get.side_effect = TimeoutError("Connection timeout")
            mock_redis_prop.return_value = mock_redis

            # Should return False instead of raising exception
            result = auth_service.is_token_blacklisted("test-jti")
            assert result is False

    def test_blacklist_token_with_connection_error(self, auth_service: AuthService, capsys):
        """Test blacklisting token when Redis connection fails."""
        with patch.object(AuthService, "redis_client", new_callable=PropertyMock) as mock_redis_prop:
            mock_redis = Mock()
            mock_redis.setex.side_effect = ConnectionError("Connection reset by peer")
            mock_redis_prop.return_value = mock_redis

            expires_at = datetime.now(UTC) + timedelta(minutes=15)

            # Should not raise exception
            auth_service.blacklist_token("test-jti", expires_at)

            # Should print error message
            captured = capsys.readouterr()
            assert "Redis error while blacklisting token" in captured.out

    def test_blacklist_token_with_timeout_error(self, auth_service: AuthService, capsys):
        """Test blacklisting token when Redis times out."""
        with patch.object(AuthService, "redis_client", new_callable=PropertyMock) as mock_redis_prop:
            mock_redis = Mock()
            mock_redis.setex.side_effect = TimeoutError("Connection timeout")
            mock_redis_prop.return_value = mock_redis

            expires_at = datetime.now(UTC) + timedelta(minutes=15)

            # Should not raise exception
            auth_service.blacklist_token("test-jti", expires_at)

            # Should print error message
            captured = capsys.readouterr()
            assert "Redis error while blacklisting token" in captured.out

    def test_verify_token_with_redis_down(self, auth_service: AuthService):
        """Test verifying access token when Redis is down."""
        # Create a valid token
        user_id = "12345"
        token, jti, _ = auth_service.create_access_token(user_id)

        # Mock Redis to be down
        with patch.object(AuthService, "redis_client", new_callable=PropertyMock) as mock_redis_prop:
            mock_redis = Mock()
            mock_redis.get.side_effect = ConnectionError("Connection reset by peer")
            mock_redis_prop.return_value = mock_redis

            # Should still verify token successfully (assumes not blacklisted)
            payload = auth_service.verify_token(token, "access")
            assert payload["sub"] == user_id
            assert payload["jti"] == jti

    def test_redis_connection_pool_configuration(self, auth_service: AuthService):
        """Test that Redis connection pool is properly configured."""
        # Access redis_client to trigger pool creation
        with (
            patch("src.common.services.auth_service.ConnectionPool") as mock_pool_class,
            patch("src.common.services.auth_service.Redis") as mock_redis_class,
        ):
            # Reset the internal state
            auth_service._redis_pool = None
            auth_service._redis_client = None

            # Access the property to trigger initialization
            _ = auth_service.redis_client

            # Verify ConnectionPool was created with correct parameters
            mock_pool_class.assert_called_once()
            pool_args = mock_pool_class.call_args[1]

            assert pool_args["max_connections"] == 10
            assert pool_args["socket_connect_timeout"] == 5
            assert pool_args["socket_timeout"] == 5
            assert pool_args["retry_on_timeout"] is True
            assert pool_args["decode_responses"] is True

            # Verify Redis client was created with the pool
            mock_redis_class.assert_called_once_with(connection_pool=mock_pool_class.return_value)

    def test_multiple_redis_errors_in_sequence(self, auth_service: AuthService):
        """Test handling multiple Redis errors in sequence."""
        with patch.object(AuthService, "redis_client", new_callable=PropertyMock) as mock_redis_prop:
            mock_redis = Mock()
            # First call raises ConnectionError, second raises TimeoutError
            mock_redis.get.side_effect = [
                ConnectionError("Connection reset"),
                TimeoutError("Timeout"),
                None,  # Third call succeeds
            ]
            mock_redis_prop.return_value = mock_redis

            # All calls should handle errors gracefully
            assert auth_service.is_token_blacklisted("jti1") is False
            assert auth_service.is_token_blacklisted("jti2") is False
            assert auth_service.is_token_blacklisted("jti3") is False

    def test_redis_client_singleton_pattern(self, auth_service: AuthService):
        """Test that Redis client uses singleton pattern."""
        with (
            patch("src.common.services.auth_service.ConnectionPool"),
            patch("src.common.services.auth_service.Redis") as mock_redis_class,
        ):
            # Reset the internal state
            auth_service._redis_pool = None
            auth_service._redis_client = None

            # Multiple accesses should only create one instance
            client1 = auth_service.redis_client
            client2 = auth_service.redis_client
            client3 = auth_service.redis_client

            # Should only create Redis client once
            assert mock_redis_class.call_count == 1
            assert client1 is client2
            assert client2 is client3
