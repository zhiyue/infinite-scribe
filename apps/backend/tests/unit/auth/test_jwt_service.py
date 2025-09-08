"""Unit tests for JWT service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from jose import JWTError
from src.common.services.user.auth_service import AuthService


class TestAuthService:
    """Test cases for AuthService."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        with patch.object(AuthService, "redis_client", new_callable=Mock) as mock:
            mock.get.return_value = None  # Default: tokens not blacklisted
            mock.setex.return_value = True
            yield mock

    @pytest.fixture
    def auth_service(self, mock_redis) -> AuthService:
        """Create JWT service instance with mocked Redis."""
        service = AuthService()
        service._redis_client = mock_redis
        return service

    def test_create_access_token_basic(self, auth_service: AuthService):
        """Test creating an access token with basic parameters."""
        user_id = "12345"
        token, jti, expires_at = auth_service.create_access_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
        assert isinstance(jti, str)
        assert len(jti) > 10
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.now(UTC)

    def test_create_access_token_with_claims(self, auth_service: AuthService):
        """Test creating an access token with additional claims."""
        user_id = "12345"
        additional_claims = {"role": "admin", "permissions": ["read", "write"]}

        token, jti, expires_at = auth_service.create_access_token(user_id, additional_claims)

        # Verify token by decoding it
        payload = auth_service.verify_token(token, "access")
        assert payload["sub"] == user_id
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]
        assert payload["token_type"] == "access"

    def test_create_refresh_token(self, auth_service: AuthService):
        """Test creating a refresh token."""
        user_id = "12345"
        token, expires_at = auth_service.create_refresh_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 50
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.now(UTC)

        # Verify refresh token expires later than access token
        access_token, _, access_expires = auth_service.create_access_token(user_id)
        assert expires_at > access_expires

    def test_verify_valid_access_token(self, auth_service: AuthService):
        """Test verifying a valid access token."""
        user_id = "12345"
        token, jti, _ = auth_service.create_access_token(user_id)

        payload = auth_service.verify_token(token, "access")
        assert payload["sub"] == user_id
        assert payload["jti"] == jti
        assert payload["token_type"] == "access"

    def test_verify_valid_refresh_token(self, auth_service: AuthService):
        """Test verifying a valid refresh token."""
        user_id = "12345"
        token, _ = auth_service.create_refresh_token(user_id)

        payload = auth_service.verify_token(token, "refresh")
        assert payload["sub"] == user_id
        assert payload["token_type"] == "refresh"

    def test_verify_token_wrong_type(self, auth_service: AuthService):
        """Test verifying token with wrong expected type."""
        user_id = "12345"
        access_token, _, _ = auth_service.create_access_token(user_id)

        with pytest.raises(JWTError) as exc_info:
            auth_service.verify_token(access_token, "refresh")

        assert "Invalid token type" in str(exc_info.value)

    def test_verify_expired_token(self, auth_service: AuthService):
        """Test verifying an expired token."""
        # Create a token that expires immediately
        user_id = "12345"
        auth_service.access_token_expire_minutes = -1  # Negative to expire immediately

        token, _, _ = auth_service.create_access_token(user_id)

        # Reset to normal expiration
        auth_service.access_token_expire_minutes = 15

        with pytest.raises(JWTError):
            auth_service.verify_token(token, "access")

    def test_verify_invalid_token(self, auth_service: AuthService):
        """Test verifying an invalid token."""
        invalid_token = "invalid.token.here"

        with pytest.raises(JWTError):
            auth_service.verify_token(invalid_token, "access")

    def test_verify_token_wrong_algorithm(self, auth_service: AuthService):
        """Test verifying token signed with different algorithm."""
        # Create token with different algorithm
        from jose import jwt

        payload = {
            "sub": "12345",
            "exp": datetime.now(UTC) + timedelta(minutes=15),
            "token_type": "access",
            "jti": "test-jti",
        }

        # Sign with different algorithm
        wrong_token = jwt.encode(payload, auth_service.secret_key, algorithm="HS512")

        with pytest.raises(JWTError):
            auth_service.verify_token(wrong_token, "access")

    def test_blacklist_token(self, auth_service: AuthService, mock_redis):
        """Test adding a token to blacklist."""
        jti = "test-jti-123"
        expires_at = datetime.now(UTC) + timedelta(minutes=15)

        auth_service.blacklist_token(jti, expires_at)

        # Verify Redis setex was called correctly
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == f"blacklist:{jti}"
        assert call_args[2] == "1"
        assert call_args[1] > 0  # TTL should be positive

    def test_blacklist_token_already_expired(self, auth_service: AuthService, mock_redis):
        """Test blacklisting an already expired token."""
        jti = "expired-jti"
        expires_at = datetime.now(UTC) - timedelta(minutes=1)  # Already expired

        auth_service.blacklist_token(jti, expires_at)

        # Should not call Redis for expired token
        mock_redis.setex.assert_not_called()

    def test_is_token_blacklisted_true(self, auth_service: AuthService, mock_redis):
        """Test checking if a token is blacklisted (true case)."""
        jti = "blacklisted-jti"
        mock_redis.get.return_value = "1"

        assert auth_service.is_token_blacklisted(jti) is True
        mock_redis.get.assert_called_with(f"blacklist:{jti}")

    def test_is_token_blacklisted_false(self, auth_service: AuthService, mock_redis):
        """Test checking if a token is blacklisted (false case)."""
        jti = "valid-jti"
        mock_redis.get.return_value = None

        assert auth_service.is_token_blacklisted(jti) is False
        mock_redis.get.assert_called_with(f"blacklist:{jti}")

    def test_verify_blacklisted_token(self, auth_service: AuthService, mock_redis):
        """Test verifying a blacklisted token."""
        user_id = "12345"
        token, jti, _ = auth_service.create_access_token(user_id)

        # Mock the token as blacklisted
        mock_redis.get.return_value = "1"

        with pytest.raises(JWTError) as exc_info:
            auth_service.verify_token(token, "access")

        assert "revoked" in str(exc_info.value)

    def test_extract_token_from_header_valid(self, auth_service: AuthService):
        """Test extracting token from valid Authorization header."""
        header = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        token = auth_service.extract_token_from_header(header)

        assert token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"

    def test_extract_token_from_header_case_insensitive(self, auth_service: AuthService):
        """Test extracting token with different case Bearer."""
        header = "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        token = auth_service.extract_token_from_header(header)

        assert token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"

    def test_extract_token_from_header_invalid_format(self, auth_service: AuthService):
        """Test extracting token from invalid header formats."""
        invalid_headers = [
            "",
            "Bearer",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "Basic dXNlcjpwYXNz",
            "Bearer token1 token2",
        ]

        for header in invalid_headers:
            assert auth_service.extract_token_from_header(header) is None

    def test_token_expiration_timing(self, auth_service: AuthService):
        """Test that tokens expire at the correct time."""
        user_id = "12345"

        # Create access token
        access_token, _, access_expires = auth_service.create_access_token(user_id)

        # Check expiration is approximately correct
        expected_expire = datetime.now(UTC) + timedelta(minutes=auth_service.access_token_expire_minutes)
        time_diff = abs((access_expires - expected_expire).total_seconds())
        assert time_diff < 5  # Within 5 seconds tolerance

    def test_different_jti_for_each_token(self, auth_service: AuthService):
        """Test that each token gets a unique JTI."""
        user_id = "12345"

        # Create multiple tokens
        tokens_data = [auth_service.create_access_token(user_id) for _ in range(10)]

        # Extract JTIs
        jtis = [data[1] for data in tokens_data]

        # All JTIs should be unique
        assert len(set(jtis)) == 10
