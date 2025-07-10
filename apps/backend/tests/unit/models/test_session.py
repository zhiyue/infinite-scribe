"""Unit tests for Session model."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from src.models.session import Session


class TestSession:
    """Test cases for Session model."""

    def test_is_access_token_expired_when_not_expired(self):
        """Test is_access_token_expired property when access token is not expired."""
        future_time = datetime.now(UTC) + timedelta(hours=1)
        session = Session(
            user_id=1,
            jti="test_jti",
            refresh_token="test_refresh_token",
            access_token_expires_at=future_time,
            refresh_token_expires_at=datetime.now(UTC) + timedelta(days=7),
        )

        assert session.is_access_token_expired is False

    def test_is_access_token_expired_when_expired(self):
        """Test is_access_token_expired property when access token is expired."""
        past_time = datetime.now(UTC) - timedelta(hours=1)
        session = Session(
            user_id=1,
            jti="test_jti",
            refresh_token="test_refresh_token",
            access_token_expires_at=past_time,
            refresh_token_expires_at=datetime.now(UTC) + timedelta(days=7),
        )

        assert session.is_access_token_expired is True

    def test_is_refresh_token_expired_when_not_expired(self):
        """Test is_refresh_token_expired property when refresh token is not expired."""
        future_time = datetime.now(UTC) + timedelta(days=7)
        session = Session(
            user_id=1,
            jti="test_jti",
            refresh_token="test_refresh_token",
            access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_token_expires_at=future_time,
        )

        assert session.is_refresh_token_expired is False

    def test_is_refresh_token_expired_when_expired(self):
        """Test is_refresh_token_expired property when refresh token is expired."""
        past_time = datetime.now(UTC) - timedelta(days=1)
        session = Session(
            user_id=1,
            jti="test_jti",
            refresh_token="test_refresh_token",
            access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_token_expires_at=past_time,
        )

        assert session.is_refresh_token_expired is True

    def test_is_valid_when_valid(self):
        """Test is_valid property when session is valid."""
        future_time = datetime.now(UTC) + timedelta(days=7)
        session = Session(
            user_id=1,
            jti="test_jti",
            refresh_token="test_refresh_token",
            access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_token_expires_at=future_time,
            is_active=True,
            revoked_at=None,
        )

        assert session.is_valid is True

    def test_is_valid_when_inactive(self):
        """Test is_valid property when session is inactive."""
        future_time = datetime.now(UTC) + timedelta(days=7)
        session = Session(
            user_id=1,
            jti="test_jti",
            refresh_token="test_refresh_token",
            access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_token_expires_at=future_time,
            is_active=False,
            revoked_at=None,
        )

        assert session.is_valid is False

    def test_is_valid_when_revoked(self):
        """Test is_valid property when session is revoked."""
        future_time = datetime.now(UTC) + timedelta(days=7)
        session = Session(
            user_id=1,
            jti="test_jti",
            refresh_token="test_refresh_token",
            access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_token_expires_at=future_time,
            is_active=True,
            revoked_at=datetime.now(UTC),
        )

        assert session.is_valid is False

    def test_is_valid_when_refresh_token_expired(self):
        """Test is_valid property when refresh token is expired."""
        past_time = datetime.now(UTC) - timedelta(days=1)
        session = Session(
            user_id=1,
            jti="test_jti",
            refresh_token="test_refresh_token",
            access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_token_expires_at=past_time,
            is_active=True,
            revoked_at=None,
        )

        assert session.is_valid is False

    def test_revoke_without_reason(self):
        """Test revoking session without reason."""
        session = Session(
            user_id=1,
            jti="test_jti",
            refresh_token="test_refresh_token",
            access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_token_expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=True,
            revoked_at=None,
            revoke_reason=None,
        )

        assert session.is_active is True
        assert session.revoked_at is None
        assert session.revoke_reason is None

        with patch("src.models.session.utc_now") as mock_utc_now:
            mock_now = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)
            mock_utc_now.return_value = mock_now

            session.revoke()

            assert session.is_active is False
            assert session.revoked_at == mock_now
            assert session.revoke_reason is None

    def test_revoke_with_reason(self):
        """Test revoking session with reason."""
        session = Session(
            user_id=1,
            jti="test_jti",
            refresh_token="test_refresh_token",
            access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_token_expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=True,
            revoked_at=None,
            revoke_reason=None,
        )

        with patch("src.models.session.utc_now") as mock_utc_now:
            mock_now = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)
            mock_utc_now.return_value = mock_now

            session.revoke("User logout")

            assert session.is_active is False
            assert session.revoked_at == mock_now
            assert session.revoke_reason == "User logout"

    def test_to_dict(self):
        """Test converting session to dictionary."""
        created_at = datetime(2021, 1, 1, 10, 0, 0, tzinfo=UTC)
        last_accessed_at = datetime(2021, 1, 1, 11, 0, 0, tzinfo=UTC)
        access_expires_at = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)
        refresh_expires_at = datetime(2021, 1, 8, 10, 0, 0, tzinfo=UTC)
        revoked_at = datetime(2021, 1, 1, 11, 30, 0, tzinfo=UTC)

        session = Session(
            id=123,
            user_id=456,
            jti="test_jti_123",
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
            device_type="desktop",
            device_name="Chrome Browser",
            is_active=False,
            last_accessed_at=last_accessed_at,
            access_token_expires_at=access_expires_at,
            refresh_token_expires_at=refresh_expires_at,
            created_at=created_at,
            revoked_at=revoked_at,
            revoke_reason="Security breach",
        )

        result = session.to_dict()

        expected = {
            "id": 123,
            "user_id": 456,
            "jti": "test_jti_123",
            "user_agent": "Mozilla/5.0",
            "ip_address": "192.168.1.1",
            "device_type": "desktop",
            "device_name": "Chrome Browser",
            "is_active": False,
            "is_valid": False,
            "last_accessed_at": last_accessed_at.isoformat(),
            "access_token_expires_at": access_expires_at.isoformat(),
            "refresh_token_expires_at": refresh_expires_at.isoformat(),
            "created_at": created_at.isoformat(),
            "revoked_at": revoked_at.isoformat(),
            "revoke_reason": "Security breach",
        }

        assert result == expected

    def test_to_dict_with_none_values(self):
        """Test to_dict with None values."""
        session = Session(
            id=123,
            user_id=456,
            jti="test_jti_123",
            user_agent=None,
            ip_address=None,
            device_type=None,
            device_name=None,
            is_active=True,
            last_accessed_at=None,
            access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_token_expires_at=datetime.now(UTC) + timedelta(days=7),
            created_at=None,
            revoked_at=None,
            revoke_reason=None,
        )

        result = session.to_dict()

        # Check that None values are properly handled
        assert result["user_agent"] is None
        assert result["ip_address"] is None
        assert result["device_type"] is None
        assert result["device_name"] is None
        assert result["last_accessed_at"] is None
        assert result["created_at"] is None
        assert result["revoked_at"] is None
        assert result["revoke_reason"] is None
        assert result["is_active"] is True

    def test_repr(self):
        """Test string representation."""
        session = Session(id=123, user_id=456, jti="test_jti_abcdefgh")

        repr_str = repr(session)

        assert "Session" in repr_str
        assert "id=123" in repr_str
        assert "user_id=456" in repr_str
        assert "jti='test_jti" in repr_str  # Should show truncated JTI (first 8 chars)
