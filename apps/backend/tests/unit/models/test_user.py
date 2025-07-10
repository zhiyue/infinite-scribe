"""Unit tests for User model."""

from datetime import timedelta
from uuid import uuid4

from src.common.utils.datetime_utils import utc_now
from src.models.user import User


class TestUserModel:
    """Test cases for User model."""

    def test_user_repr(self):
        """Test User __repr__ method."""
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            first_name="Test",
            last_name="User",
        )

        repr_str = repr(user)
        assert "User" in repr_str
        assert "testuser" in repr_str
        assert "test@example.com" in repr_str

    def test_full_name_with_both_names(self):
        """Test full_name property with both first and last names."""
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            first_name="John",
            last_name="Doe",
        )

        assert user.full_name == "John Doe"

    def test_full_name_with_first_name_only(self):
        """Test full_name property with first name only."""
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            first_name="John",
            last_name=None,
        )

        assert user.full_name == "John"

    def test_full_name_with_last_name_only(self):
        """Test full_name property with last name only."""
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            first_name=None,
            last_name="Doe",
        )

        assert user.full_name == "Doe"

    def test_full_name_with_no_names(self):
        """Test full_name property with no names, should return username."""
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            first_name=None,
            last_name=None,
        )

        assert user.full_name == "testuser"

    def test_is_locked_when_not_locked(self):
        """Test is_locked property when user is not locked."""
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            locked_until=None,
        )

        assert user.is_locked is False

    def test_is_locked_when_lock_expired(self):
        """Test is_locked property when lock has expired."""
        past_time = utc_now() - timedelta(hours=1)

        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            locked_until=past_time,
        )

        assert user.is_locked is False

    def test_is_locked_when_currently_locked(self):
        """Test is_locked property when user is currently locked."""
        future_time = utc_now() + timedelta(hours=1)

        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            locked_until=future_time,
        )

        assert user.is_locked is True

    def test_is_email_verified_when_verified(self):
        """Test is_email_verified property when email is verified."""
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            email_verified_at=utc_now(),
        )

        assert user.is_email_verified is True

    def test_is_email_verified_when_not_verified(self):
        """Test is_email_verified property when email is not verified."""
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            email_verified_at=None,
        )

        assert user.is_email_verified is False

    def test_to_dict_basic(self):
        """Test to_dict method with basic data."""
        user_id = uuid4()
        created_at = utc_now()
        updated_at = utc_now()

        user = User(
            id=user_id,
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            first_name="John",
            last_name="Doe",
            avatar_url="https://example.com/avatar.jpg",
            bio="Test bio",
            is_active=True,
            is_verified=True,
            is_superuser=False,
            created_at=created_at,
            updated_at=updated_at,
            email_verified_at=created_at,
        )

        result = user.to_dict()

        assert result["id"] == user_id
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"
        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"
        assert result["full_name"] == "John Doe"
        assert result["avatar_url"] == "https://example.com/avatar.jpg"
        assert result["bio"] == "Test bio"
        assert result["is_active"] is True
        assert result["is_verified"] is True
        assert result["is_superuser"] is False
        assert result["created_at"] == created_at.isoformat()
        assert result["updated_at"] == updated_at.isoformat()
        assert result["email_verified_at"] == created_at.isoformat()

        # Should not include sensitive info by default
        assert "failed_login_attempts" not in result
        assert "is_locked" not in result
        assert "locked_until" not in result
        assert "last_login_at" not in result
        assert "last_login_ip" not in result
        assert "password_changed_at" not in result

    def test_to_dict_with_none_dates(self):
        """Test to_dict method when datetime fields are None."""
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            created_at=None,
            updated_at=None,
            email_verified_at=None,
        )

        result = user.to_dict()

        assert result["created_at"] is None
        assert result["updated_at"] is None
        assert result["email_verified_at"] is None

    def test_to_dict_include_sensitive(self):
        """Test to_dict method with include_sensitive=True."""
        user_id = uuid4()
        utc_now()
        last_login_at = utc_now()
        locked_until = utc_now() + timedelta(hours=1)
        password_changed_at = utc_now()

        user = User(
            id=user_id,
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            failed_login_attempts=3,
            locked_until=locked_until,
            last_login_at=last_login_at,
            last_login_ip="192.168.1.1",
            password_changed_at=password_changed_at,
        )

        result = user.to_dict(include_sensitive=True)

        # Should include sensitive info
        assert result["failed_login_attempts"] == 3
        assert result["is_locked"] is True  # locked_until is in the future
        assert result["locked_until"] == locked_until.isoformat()
        assert result["last_login_at"] == last_login_at.isoformat()
        assert result["last_login_ip"] == "192.168.1.1"
        assert result["password_changed_at"] == password_changed_at.isoformat()

    def test_to_dict_include_sensitive_with_none_values(self):
        """Test to_dict method with include_sensitive=True and None values."""
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            failed_login_attempts=0,
            locked_until=None,
            last_login_at=None,
            last_login_ip=None,
            password_changed_at=None,
        )

        result = user.to_dict(include_sensitive=True)

        # Should include sensitive info with None values
        assert result["failed_login_attempts"] == 0
        assert result["is_locked"] is False  # locked_until is None
        assert result["locked_until"] is None
        assert result["last_login_at"] is None
        assert result["last_login_ip"] is None
        assert result["password_changed_at"] is None
