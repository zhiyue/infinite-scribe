"""Unit tests for EmailVerification model."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from src.models.email_verification import EmailVerification, VerificationPurpose


class TestEmailVerification:
    """Test cases for EmailVerification model."""

    def test_generate_token(self):
        """Test token generation."""
        token = EmailVerification.generate_token()

        assert isinstance(token, str)
        assert len(token) > 0

        # Test that each call generates a unique token
        token2 = EmailVerification.generate_token()
        assert token != token2

    def test_create_for_user_with_defaults(self):
        """Test creating verification for user with default parameters."""
        with patch("src.models.email_verification.utc_now") as mock_utc_now:
            mock_now = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)
            mock_utc_now.return_value = mock_now

            verification = EmailVerification.create_for_user(
                user_id=123, email="test@example.com", purpose=VerificationPurpose.EMAIL_VERIFY
            )

            assert verification.user_id == 123
            assert verification.email == "test@example.com"
            assert verification.purpose == VerificationPurpose.EMAIL_VERIFY
            assert verification.expires_at == mock_now + timedelta(hours=24)
            assert verification.requested_from_ip is None
            assert verification.user_agent is None
            assert len(verification.token) > 0

    def test_create_for_user_with_custom_params(self):
        """Test creating verification with custom parameters."""
        with patch("src.models.email_verification.utc_now") as mock_utc_now:
            mock_now = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)
            mock_utc_now.return_value = mock_now

            verification = EmailVerification.create_for_user(
                user_id=456,
                email="reset@example.com",
                purpose=VerificationPurpose.PASSWORD_RESET,
                expires_in_hours=2,
                requested_from_ip="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

            assert verification.user_id == 456
            assert verification.email == "reset@example.com"
            assert verification.purpose == VerificationPurpose.PASSWORD_RESET
            assert verification.expires_at == mock_now + timedelta(hours=2)
            assert verification.requested_from_ip == "192.168.1.1"
            assert verification.user_agent == "Mozilla/5.0"

    def test_is_expired_when_not_expired(self):
        """Test is_expired property when token is not expired."""
        future_time = datetime.now(UTC) + timedelta(hours=1)
        verification = EmailVerification(
            user_id=1,
            email="test@example.com",
            token="test_token",
            purpose=VerificationPurpose.EMAIL_VERIFY,
            expires_at=future_time,
        )

        assert verification.is_expired is False

    def test_is_expired_when_expired(self):
        """Test is_expired property when token is expired."""
        past_time = datetime.now(UTC) - timedelta(hours=1)
        verification = EmailVerification(
            user_id=1,
            email="test@example.com",
            token="test_token",
            purpose=VerificationPurpose.EMAIL_VERIFY,
            expires_at=past_time,
        )

        assert verification.is_expired is True

    def test_is_expired_when_expires_at_is_none(self):
        """Test is_expired property when expires_at is None."""
        verification = EmailVerification(
            user_id=1,
            email="test@example.com",
            token="test_token",
            purpose=VerificationPurpose.EMAIL_VERIFY,
            expires_at=None,
        )

        assert verification.is_expired is True

    def test_is_used_when_not_used(self):
        """Test is_used property when token has not been used."""
        verification = EmailVerification(
            user_id=1,
            email="test@example.com",
            token="test_token",
            purpose=VerificationPurpose.EMAIL_VERIFY,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            used_at=None,
        )

        assert verification.is_used is False

    def test_is_used_when_used(self):
        """Test is_used property when token has been used."""
        verification = EmailVerification(
            user_id=1,
            email="test@example.com",
            token="test_token",
            purpose=VerificationPurpose.EMAIL_VERIFY,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            used_at=datetime.now(UTC),
        )

        assert verification.is_used is True

    def test_is_valid_when_valid(self):
        """Test is_valid property when token is valid."""
        verification = EmailVerification(
            user_id=1,
            email="test@example.com",
            token="test_token",
            purpose=VerificationPurpose.EMAIL_VERIFY,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            used_at=None,
        )

        assert verification.is_valid is True

    def test_is_valid_when_expired(self):
        """Test is_valid property when token is expired."""
        verification = EmailVerification(
            user_id=1,
            email="test@example.com",
            token="test_token",
            purpose=VerificationPurpose.EMAIL_VERIFY,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            used_at=None,
        )

        assert verification.is_valid is False

    def test_is_valid_when_used(self):
        """Test is_valid property when token is used."""
        verification = EmailVerification(
            user_id=1,
            email="test@example.com",
            token="test_token",
            purpose=VerificationPurpose.EMAIL_VERIFY,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            used_at=datetime.now(UTC),
        )

        assert verification.is_valid is False

    def test_mark_as_used(self):
        """Test marking token as used."""
        verification = EmailVerification(
            user_id=1,
            email="test@example.com",
            token="test_token",
            purpose=VerificationPurpose.EMAIL_VERIFY,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            used_at=None,
        )

        assert verification.used_at is None

        with patch("src.models.email_verification.utc_now") as mock_utc_now:
            mock_now = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)
            mock_utc_now.return_value = mock_now

            verification.mark_as_used()

            assert verification.used_at == mock_now

    def test_to_dict(self):
        """Test converting verification to dictionary."""
        created_at = datetime(2021, 1, 1, 10, 0, 0, tzinfo=UTC)
        expires_at = datetime(2021, 1, 1, 14, 0, 0, tzinfo=UTC)
        used_at = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)

        verification = EmailVerification(
            id=123,
            user_id=456,
            email="test@example.com",
            token="test_token",
            purpose=VerificationPurpose.EMAIL_VERIFY,
            expires_at=expires_at,
            used_at=used_at,
            created_at=created_at,
        )

        result = verification.to_dict()

        expected = {
            "id": 123,
            "user_id": 456,
            "purpose": "email_verify",
            "email": "test@example.com",
            "is_valid": False,  # Used token is not valid
            "is_expired": True,  # Past expiry time
            "is_used": True,
            "expires_at": expires_at.isoformat(),
            "used_at": used_at.isoformat(),
            "created_at": created_at.isoformat(),
        }

        assert result == expected

    def test_to_dict_with_none_values(self):
        """Test to_dict with None timestamp values."""
        verification = EmailVerification(
            id=123,
            user_id=456,
            email="test@example.com",
            token="test_token",
            purpose=VerificationPurpose.PASSWORD_RESET,
            expires_at=None,
            used_at=None,
            created_at=None,
        )

        result = verification.to_dict()

        expected = {
            "id": 123,
            "user_id": 456,
            "purpose": "password_reset",
            "email": "test@example.com",
            "is_valid": False,  # expires_at is None, so expired
            "is_expired": True,
            "is_used": False,
            "expires_at": None,
            "used_at": None,
            "created_at": None,
        }

        assert result == expected

    def test_repr(self):
        """Test string representation."""
        verification = EmailVerification(id=123, user_id=456, purpose=VerificationPurpose.EMAIL_VERIFY)

        repr_str = repr(verification)

        assert "EmailVerification" in repr_str
        assert "id=123" in repr_str
        assert "user_id=456" in repr_str
        assert "purpose='VerificationPurpose.EMAIL_VERIFY'" in repr_str
