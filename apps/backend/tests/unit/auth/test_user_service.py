"""Unit tests for user service."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import UserService without models to avoid circular import
from src.common.services.user_service import UserService
from src.models.email_verification import VerificationPurpose


class TestUserService:
    """Test cases for UserService."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def mock_password_service(self):
        """Mock password service."""
        with patch("src.common.services.user_service.password_service") as mock:
            mock.hash_password.return_value = "hashed_password"
            mock.verify_password.return_value = True
            mock.validate_password_strength.return_value = {
                "is_valid": True,
                "score": 4,
                "errors": [],
                "suggestions": [],
            }
            yield mock

    @pytest.fixture
    def mock_jwt_service(self):
        """Mock JWT service."""
        with patch("src.common.services.user_service.jwt_service") as mock:
            mock.create_access_token.return_value = (
                "access_token",
                "jti123",
                datetime.utcnow() + timedelta(minutes=15),
            )
            mock.create_refresh_token.return_value = ("refresh_token", datetime.utcnow() + timedelta(days=7))
            yield mock

    @pytest.fixture
    def mock_email_service(self):
        """Mock email service."""
        with patch("src.common.services.user_service.email_service") as mock:
            mock.send_verification_email = AsyncMock(return_value=True)
            mock.send_welcome_email = AsyncMock(return_value=True)
            mock.send_password_reset_email = AsyncMock(return_value=True)
            yield mock

    @pytest.fixture
    def user_service(self, mock_password_service, mock_jwt_service, mock_email_service):
        """Create user service instance with mocked dependencies."""
        return UserService()

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        user = Mock()
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.password_hash = "hashed_password"
        user.is_active = True
        user.is_verified = True
        user.failed_login_attempts = 0
        user.is_locked = False
        user.created_at = datetime.utcnow()
        user.email_verified_at = datetime.utcnow()
        user.to_dict = Mock(
            return_value={
                "id": 1,
                "username": "testuser",
                "email": "test@example.com",
                "is_active": True,
                "is_verified": True,
            }
        )
        return user

    @pytest.mark.asyncio
    @patch("src.common.services.user_service.select")
    @patch("src.common.services.user_service.EmailVerification")
    @patch("src.common.services.user_service.User")
    async def test_register_user_success(
        self,
        mock_user_model,
        mock_email_verification,
        mock_select,
        user_service,
        mock_db_session,
        mock_password_service,
    ):
        """Test successful user registration."""
        # Arrange
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "first_name": "New",
            "last_name": "User",
        }

        # Mock User instance
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = user_data["email"]
        mock_user.full_name = f"{user_data['first_name']} {user_data['last_name']}"
        mock_user.to_dict = Mock(
            return_value={
                "id": 1,
                "username": user_data["username"],
                "email": user_data["email"],
                "is_active": True,
                "is_verified": False,
            }
        )
        mock_user_model.return_value = mock_user

        # Mock EmailVerification
        mock_verification = Mock()
        mock_verification.token = "test_token"
        mock_email_verification.create_for_user.return_value = mock_verification

        # Mock select query
        mock_select.return_value.where.return_value = "mock_query"
        mock_db_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

        # Act
        result = await user_service.register_user(mock_db_session, user_data)

        # Assert
        assert result["success"] is True
        assert "user" in result
        assert result["user"]["username"] == "newuser"
        assert result["user"]["email"] == "newuser@example.com"
        mock_password_service.validate_password_strength.assert_called_once()
        mock_password_service.hash_password.assert_called_once()
        assert mock_db_session.add.call_count == 2  # Called twice: User and EmailVerification
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_register_user_weak_password(self, user_service, mock_db_session, mock_password_service):
        """Test registration with weak password."""
        # Arrange
        user_data = {"username": "newuser", "email": "newuser@example.com", "password": "weak"}

        mock_password_service.validate_password_strength.return_value = {
            "is_valid": False,
            "score": 1,
            "errors": ["Password too short"],
            "suggestions": [],
        }

        # Act
        result = await user_service.register_user(mock_db_session, user_data)

        # Assert
        assert result["success"] is False
        assert "Password too short" in result["error"]
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, user_service, mock_db_session):
        """Test registration with duplicate email."""
        # Arrange
        user_data = {"username": "newuser", "email": "existing@example.com", "password": "SecurePassword123!"}

        # Mock existing user check
        mock_db_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=Mock(id=1))))

        # Act
        result = await user_service.register_user(mock_db_session, user_data)

        # Assert
        assert result["success"] is False
        assert "already exists" in result["error"]

    @pytest.mark.asyncio
    @patch("src.common.services.user_service.Session")
    async def test_login_success(
        self, mock_session_model, user_service, mock_db_session, sample_user, mock_password_service
    ):
        """Test successful login."""
        # Arrange
        # Mock Session instance
        mock_session = Mock()
        mock_session.id = 1
        mock_session_model.return_value = mock_session

        mock_db_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=sample_user)))

        # Act
        result = await user_service.login(
            mock_db_session, "test@example.com", "password123", "127.0.0.1", "Mozilla/5.0"
        )

        # Assert
        assert result["success"] is True
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user"]["id"] == 1
        mock_password_service.verify_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, user_service, mock_db_session, sample_user, mock_password_service):
        """Test login with invalid credentials."""
        # Arrange
        mock_db_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=sample_user)))
        mock_password_service.verify_password.return_value = False

        # Act
        result = await user_service.login(
            mock_db_session, "test@example.com", "wrongpassword", "127.0.0.1", "Mozilla/5.0"
        )

        # Assert
        assert result["success"] is False
        assert "Invalid credentials" in result["error"]

    @pytest.mark.asyncio
    @patch("src.common.services.user_service.Session")
    async def test_login_account_locked(self, mock_session_model, user_service, mock_db_session, sample_user):
        """Test login with locked account."""
        # Arrange
        sample_user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        sample_user.is_locked = True  # Update the property
        mock_db_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=sample_user)))

        # Act
        result = await user_service.login(
            mock_db_session, "test@example.com", "password123", "127.0.0.1", "Mozilla/5.0"
        )

        # Assert
        assert result["success"] is False
        assert "locked" in result["error"]

    @pytest.mark.asyncio
    async def test_login_unverified_account(self, user_service, mock_db_session, sample_user):
        """Test login with unverified account."""
        # Arrange
        sample_user.is_verified = False
        mock_db_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=sample_user)))

        # Act
        result = await user_service.login(
            mock_db_session, "test@example.com", "password123", "127.0.0.1", "Mozilla/5.0"
        )

        # Assert
        assert result["success"] is False
        assert "verify your email" in result["error"]

    @pytest.mark.asyncio
    async def test_verify_email_success(self, user_service, mock_db_session, sample_user):
        """Test successful email verification."""
        # Arrange
        verification = Mock()
        verification.user_id = 1
        verification.token = "valid_token"
        verification.purpose = VerificationPurpose.EMAIL_VERIFY
        verification.expires_at = datetime.utcnow() + timedelta(hours=1)
        verification.email = "test@example.com"
        verification.is_expired = False
        verification.is_used = False
        verification.is_valid = True
        verification.mark_as_used = Mock()
        sample_user.is_verified = False

        mock_db_session.execute = AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=verification)),
                Mock(scalar_one_or_none=Mock(return_value=sample_user)),
            ]
        )

        # Act
        result = await user_service.verify_email(mock_db_session, "valid_token")

        # Assert
        assert result["success"] is True
        assert "verified successfully" in result["message"]
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, user_service, mock_db_session):
        """Test email verification with invalid token."""
        # Arrange
        mock_db_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

        # Act
        result = await user_service.verify_email(mock_db_session, "invalid_token")

        # Assert
        assert result["success"] is False
        assert "Invalid" in result["error"]

    @pytest.mark.asyncio
    async def test_verify_email_expired_token(self, user_service, mock_db_session):
        """Test email verification with expired token."""
        # Arrange
        verification = Mock()
        verification.user_id = 1
        verification.token = "expired_token"
        verification.purpose = VerificationPurpose.EMAIL_VERIFY
        verification.expires_at = datetime.utcnow() - timedelta(hours=1)
        verification.email = "test@example.com"
        verification.is_expired = True
        verification.is_used = False
        verification.is_valid = False

        mock_db_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=verification)))

        # Act
        result = await user_service.verify_email(mock_db_session, "expired_token")

        # Assert
        assert result["success"] is False
        assert "expired" in result["error"]

    @pytest.mark.asyncio
    @patch("src.common.services.user_service.EmailVerification")
    async def test_request_password_reset_success(
        self, mock_email_verification, user_service, mock_db_session, sample_user, mock_email_service
    ):
        """Test successful password reset request."""
        # Arrange
        # Mock EmailVerification
        mock_verification = Mock()
        mock_verification.token = "reset_token"
        mock_email_verification.create_for_user.return_value = mock_verification

        mock_db_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=sample_user)))

        # Act
        result = await user_service.request_password_reset(mock_db_session, "test@example.com")

        # Assert
        assert result["success"] is True
        mock_email_service.send_password_reset_email.assert_called_once()
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_reset_password_success(self, user_service, mock_db_session, sample_user, mock_password_service):
        """Test successful password reset."""
        # Arrange
        verification = Mock()
        verification.user_id = 1
        verification.token = "reset_token"
        verification.purpose = VerificationPurpose.PASSWORD_RESET
        verification.expires_at = datetime.utcnow() + timedelta(hours=1)
        verification.email = "test@example.com"
        verification.is_expired = False
        verification.is_used = False
        verification.is_valid = True
        verification.mark_as_used = Mock()

        mock_db_session.execute = AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=verification)),
                Mock(scalar_one_or_none=Mock(return_value=sample_user)),
                Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),  # Empty sessions
            ]
        )

        # Act
        result = await user_service.reset_password(mock_db_session, "reset_token", "NewSecurePassword123!")

        # Assert
        assert result["success"] is True
        mock_password_service.validate_password_strength.assert_called_once()
        mock_password_service.hash_password.assert_called_once()
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_logout_success(self, user_service, mock_db_session, mock_jwt_service):
        """Test successful logout."""
        # Arrange
        session = Mock()
        session.user_id = 1
        session.jti = "jti123"
        session.refresh_token = "refresh_token"
        session.access_token_expires_at = datetime.utcnow() + timedelta(minutes=15)
        session.refresh_token_expires_at = datetime.utcnow() + timedelta(days=7)
        session.is_active = True
        session.revoke = Mock()

        mock_db_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=session)))

        # Act
        result = await user_service.logout(mock_db_session, "jti123")

        # Assert
        assert result["success"] is True
        mock_jwt_service.blacklist_token.assert_called_once_with("jti123", session.access_token_expires_at)
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    @patch("src.common.services.user_service.select")
    @patch("src.common.services.user_service.EmailVerification")
    @patch("src.common.services.user_service.User")
    @patch("src.common.services.user_service.email_tasks")
    async def test_register_user_with_background_tasks(
        self,
        mock_email_tasks,
        mock_user_model,
        mock_email_verification,
        mock_select,
        user_service,
        mock_db_session,
        mock_password_service,
    ):
        """Test user registration with background tasks for async email sending."""
        # Arrange
        from fastapi import BackgroundTasks

        background_tasks = Mock(spec=BackgroundTasks)

        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "first_name": "New",
            "last_name": "User",
        }

        # Mock User instance
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = user_data["email"]
        mock_user.full_name = f"{user_data['first_name']} {user_data['last_name']}"
        mock_user.to_dict = Mock(
            return_value={
                "id": 1,
                "username": user_data["username"],
                "email": user_data["email"],
                "is_active": True,
                "is_verified": False,
            }
        )
        mock_user_model.return_value = mock_user

        # Mock EmailVerification
        mock_verification = Mock()
        mock_verification.token = "test_token"
        mock_email_verification.create_for_user.return_value = mock_verification

        # Mock select query
        mock_select.return_value.where.return_value = "mock_query"
        mock_db_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

        # Mock email tasks
        mock_email_tasks.send_verification_email_async = AsyncMock()

        # Act
        result = await user_service.register_user(mock_db_session, user_data, background_tasks)

        # Assert
        assert result["success"] is True
        mock_email_tasks.send_verification_email_async.assert_called_once_with(
            background_tasks,
            user_data["email"],
            mock_user.full_name,
            f"{user_service.frontend_url}/auth/verify-email?token=test_token",
        )

    @pytest.mark.asyncio
    @patch("src.common.services.user_service.EmailVerification")
    @patch("src.common.services.user_service.email_tasks")
    async def test_request_password_reset_with_background_tasks(
        self, mock_email_tasks, mock_email_verification, user_service, mock_db_session, sample_user
    ):
        """Test password reset request with background tasks for async email sending."""
        # Arrange
        from fastapi import BackgroundTasks

        background_tasks = Mock(spec=BackgroundTasks)

        # Mock EmailVerification
        mock_verification = Mock()
        mock_verification.token = "reset_token"
        mock_email_verification.create_for_user.return_value = mock_verification

        # Set full_name before the service call
        sample_user.full_name = "Test User"
        mock_db_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=sample_user)))

        # Mock email tasks
        mock_email_tasks.send_password_reset_email_async = AsyncMock()

        # Act
        result = await user_service.request_password_reset(mock_db_session, "test@example.com", background_tasks)

        # Assert
        assert result["success"] is True
        mock_email_tasks.send_password_reset_email_async.assert_called_once_with(
            background_tasks,
            sample_user.email,
            sample_user.full_name,
            f"{user_service.frontend_url}/auth/reset-password?token=reset_token",
        )

    @pytest.mark.asyncio
    @patch("src.common.services.user_service.email_tasks")
    async def test_verify_email_with_background_tasks(
        self, mock_email_tasks, user_service, mock_db_session, sample_user
    ):
        """Test email verification with background tasks for welcome email."""
        # Arrange
        from fastapi import BackgroundTasks

        background_tasks = Mock(spec=BackgroundTasks)

        verification = Mock()
        verification.user_id = 1
        verification.token = "valid_token"
        verification.purpose = VerificationPurpose.EMAIL_VERIFY
        verification.expires_at = datetime.utcnow() + timedelta(hours=1)
        verification.email = "test@example.com"
        verification.is_expired = False
        verification.is_used = False
        verification.is_valid = True
        verification.mark_as_used = Mock()
        sample_user.is_verified = False
        sample_user.full_name = "Test User"  # Set full_name before the call

        mock_db_session.execute = AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=verification)),
                Mock(scalar_one_or_none=Mock(return_value=sample_user)),
            ]
        )

        # Mock email tasks
        mock_email_tasks.send_welcome_email_async = AsyncMock()

        # Act
        result = await user_service.verify_email(mock_db_session, "valid_token", background_tasks)

        # Assert
        assert result["success"] is True
        mock_email_tasks.send_welcome_email_async.assert_called_once_with(
            background_tasks, sample_user.email, sample_user.full_name
        )

    @pytest.mark.asyncio
    @patch("src.common.services.user_service.select")
    @patch("src.common.services.user_service.EmailVerification")
    @patch("src.common.services.user_service.User")
    async def test_register_user_without_background_tasks(
        self,
        mock_user_model,
        mock_email_verification,
        mock_select,
        user_service,
        mock_db_session,
        mock_password_service,
        mock_email_service,
    ):
        """Test user registration without background tasks (sync email sending)."""
        # Arrange
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "first_name": "New",
            "last_name": "User",
        }

        # Mock User instance
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = user_data["email"]
        mock_user.full_name = f"{user_data['first_name']} {user_data['last_name']}"
        mock_user.to_dict = Mock(
            return_value={
                "id": 1,
                "username": user_data["username"],
                "email": user_data["email"],
                "is_active": True,
                "is_verified": False,
            }
        )
        mock_user_model.return_value = mock_user

        # Mock EmailVerification
        mock_verification = Mock()
        mock_verification.token = "test_token"
        mock_email_verification.create_for_user.return_value = mock_verification

        # Mock select query
        mock_select.return_value.where.return_value = "mock_query"
        mock_db_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

        # Act - no background_tasks parameter
        result = await user_service.register_user(mock_db_session, user_data)

        # Assert - should use sync email sending
        assert result["success"] is True
        mock_email_service.send_verification_email.assert_called_once_with(
            user_data["email"], mock_user.full_name, f"{user_service.frontend_url}/auth/verify-email?token=test_token"
        )
