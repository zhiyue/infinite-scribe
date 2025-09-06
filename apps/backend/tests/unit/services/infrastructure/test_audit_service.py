"""Unit tests for audit service."""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from src.common.services.audit_service import AuditEventType, AuditService, audit_service


class TestAuditEventType:
    """Test cases for AuditEventType enum."""

    def test_all_event_types_exist(self):
        """Test that all expected event types exist."""
        expected_types = [
            "login_success",
            "login_failure",
            "logout",
            "register",
            "password_change",
            "password_reset_request",
            "password_reset_success",
            "email_verification",
            "account_locked",
            "account_unlocked",
            "rate_limit_exceeded",
            "unauthorized_access",
            "token_refresh",
            "profile_update",
        ]

        for event_type in expected_types:
            assert hasattr(AuditEventType, event_type.upper())

    def test_event_type_values(self):
        """Test event type values are correct."""
        assert AuditEventType.LOGIN_SUCCESS == "login_success"
        assert AuditEventType.LOGIN_FAILURE == "login_failure"
        assert AuditEventType.LOGOUT == "logout"
        assert AuditEventType.REGISTER == "register"


class TestAuditService:
    """Test cases for AuditService class."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            yield mock_logger

    @pytest.fixture
    def audit_service_instance(self, mock_logger):
        """Create an audit service instance with mocked logger."""
        with patch("logging.FileHandler"), patch("logging.Formatter"):
            service = AuditService()
            service.logger = mock_logger
            return service

    def test_init(self, mock_logger):
        """Test audit service initialization."""
        with patch("logging.FileHandler") as mock_handler, patch("logging.Formatter"):
            mock_logger.handlers = []
            AuditService()

            mock_logger.setLevel.assert_called_once_with(logging.INFO)
            mock_handler.assert_called_once_with("logs/audit.log")

    def test_init_with_existing_handlers(self, mock_logger):
        """Test initialization when logger already has handlers."""
        with patch("logging.FileHandler") as mock_handler:
            mock_logger.handlers = [MagicMock()]  # Simulate existing handler

            AuditService()

            # Should not create new handler
            mock_handler.assert_not_called()

    @patch("src.common.services.audit_service.utc_now")
    def test_log_event_basic(self, mock_utc_now, audit_service_instance):
        """Test basic log_event functionality."""
        mock_utc_now.return_value.isoformat.return_value = "2024-01-01T00:00:00Z"

        audit_service_instance.log_event(
            AuditEventType.LOGIN_SUCCESS,
            user_id="user123",
            email="test@example.com",
            ip_address="192.168.1.1",
            user_agent="TestAgent",
        )

        expected_data = {
            "timestamp": "2024-01-01T00:00:00Z",
            "event_type": "login_success",
            "user_id": "user123",
            "email": "test@example.com",
            "ip_address": "192.168.1.1",
            "user_agent": "TestAgent",
            "success": True,
            "error_message": None,
            "additional_data": {},
        }

        audit_service_instance.logger.info.assert_called_once_with(json.dumps(expected_data))

    @patch("src.common.services.audit_service.utc_now")
    def test_log_event_with_additional_data(self, mock_utc_now, audit_service_instance):
        """Test log_event with additional data."""
        mock_utc_now.return_value.isoformat.return_value = "2024-01-01T00:00:00Z"

        additional_data = {"failed_attempts": 3, "reason": "invalid_password"}

        audit_service_instance.log_event(
            AuditEventType.LOGIN_FAILURE,
            email="test@example.com",
            success=False,
            error_message="Authentication failed",
            additional_data=additional_data,
        )

        expected_data = {
            "timestamp": "2024-01-01T00:00:00Z",
            "event_type": "login_failure",
            "user_id": None,
            "email": "test@example.com",
            "ip_address": None,
            "user_agent": None,
            "success": False,
            "error_message": "Authentication failed",
            "additional_data": additional_data,
        }

        audit_service_instance.logger.info.assert_called_once_with(json.dumps(expected_data))

    def test_log_login_success(self, audit_service_instance):
        """Test log_login_success method."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            audit_service_instance.log_login_success(
                user_id="user123", email="test@example.com", ip_address="192.168.1.1", user_agent="TestAgent"
            )

            mock_log_event.assert_called_once_with(
                AuditEventType.LOGIN_SUCCESS,
                user_id="user123",
                email="test@example.com",
                ip_address="192.168.1.1",
                user_agent="TestAgent",
            )

    def test_log_login_failure(self, audit_service_instance):
        """Test log_login_failure method."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            audit_service_instance.log_login_failure(
                email="test@example.com", ip_address="192.168.1.1", user_agent="TestAgent", reason="Invalid password"
            )

            mock_log_event.assert_called_once_with(
                AuditEventType.LOGIN_FAILURE,
                email="test@example.com",
                ip_address="192.168.1.1",
                user_agent="TestAgent",
                success=False,
                error_message="Invalid password",
            )

    def test_log_logout(self, audit_service_instance):
        """Test log_logout method."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            audit_service_instance.log_logout(
                user_id="user123", email="test@example.com", ip_address="192.168.1.1", user_agent="TestAgent"
            )

            mock_log_event.assert_called_once_with(
                AuditEventType.LOGOUT,
                user_id="user123",
                email="test@example.com",
                ip_address="192.168.1.1",
                user_agent="TestAgent",
            )

    def test_log_registration(self, audit_service_instance):
        """Test log_registration method."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            audit_service_instance.log_registration(
                user_id="user123", email="test@example.com", ip_address="192.168.1.1", user_agent="TestAgent"
            )

            mock_log_event.assert_called_once_with(
                AuditEventType.REGISTER,
                user_id="user123",
                email="test@example.com",
                ip_address="192.168.1.1",
                user_agent="TestAgent",
            )

    def test_log_password_change(self, audit_service_instance):
        """Test log_password_change method."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            audit_service_instance.log_password_change(
                user_id="user123", email="test@example.com", ip_address="192.168.1.1", user_agent="TestAgent"
            )

            mock_log_event.assert_called_once_with(
                AuditEventType.PASSWORD_CHANGE,
                user_id="user123",
                email="test@example.com",
                ip_address="192.168.1.1",
                user_agent="TestAgent",
            )

    def test_log_password_reset_request(self, audit_service_instance):
        """Test log_password_reset_request method."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            audit_service_instance.log_password_reset_request(
                email="test@example.com", ip_address="192.168.1.1", user_agent="TestAgent"
            )

            mock_log_event.assert_called_once_with(
                AuditEventType.PASSWORD_RESET_REQUEST,
                email="test@example.com",
                ip_address="192.168.1.1",
                user_agent="TestAgent",
            )

    def test_log_password_reset_success(self, audit_service_instance):
        """Test log_password_reset_success method."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            audit_service_instance.log_password_reset_success(
                user_id="user123", email="test@example.com", ip_address="192.168.1.1", user_agent="TestAgent"
            )

            mock_log_event.assert_called_once_with(
                AuditEventType.PASSWORD_RESET_SUCCESS,
                user_id="user123",
                email="test@example.com",
                ip_address="192.168.1.1",
                user_agent="TestAgent",
            )

    def test_log_account_locked(self, audit_service_instance):
        """Test log_account_locked method."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            audit_service_instance.log_account_locked(
                user_id="user123", email="test@example.com", ip_address="192.168.1.1", failed_attempts=5
            )

            mock_log_event.assert_called_once_with(
                AuditEventType.ACCOUNT_LOCKED,
                user_id="user123",
                email="test@example.com",
                ip_address="192.168.1.1",
                additional_data={"failed_attempts": 5},
            )

    def test_log_account_unlocked(self, audit_service_instance):
        """Test log_account_unlocked method."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            audit_service_instance.log_account_unlocked(
                user_id="user123", email="test@example.com", unlock_reason="manual"
            )

            mock_log_event.assert_called_once_with(
                AuditEventType.ACCOUNT_UNLOCKED,
                user_id="user123",
                email="test@example.com",
                additional_data={"unlock_reason": "manual"},
            )

    def test_log_account_unlocked_default_reason(self, audit_service_instance):
        """Test log_account_unlocked with default reason."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            audit_service_instance.log_account_unlocked(user_id="user123", email="test@example.com")

            mock_log_event.assert_called_once_with(
                AuditEventType.ACCOUNT_UNLOCKED,
                user_id="user123",
                email="test@example.com",
                additional_data={"unlock_reason": "automatic"},
            )

    def test_log_rate_limit_exceeded(self, audit_service_instance):
        """Test log_rate_limit_exceeded method."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            audit_service_instance.log_rate_limit_exceeded(
                ip_address="192.168.1.1", endpoint="/api/login", user_id="user123"
            )

            mock_log_event.assert_called_once_with(
                AuditEventType.RATE_LIMIT_EXCEEDED,
                user_id="user123",
                ip_address="192.168.1.1",
                success=False,
                additional_data={"endpoint": "/api/login"},
            )

    def test_log_unauthorized_access(self, audit_service_instance):
        """Test log_unauthorized_access method."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            audit_service_instance.log_unauthorized_access(
                ip_address="192.168.1.1", endpoint="/api/admin", user_agent="TestAgent", reason="Invalid token"
            )

            mock_log_event.assert_called_once_with(
                AuditEventType.UNAUTHORIZED_ACCESS,
                ip_address="192.168.1.1",
                user_agent="TestAgent",
                success=False,
                error_message="Invalid token",
                additional_data={"endpoint": "/api/admin"},
            )

    def test_log_token_refresh(self, audit_service_instance):
        """Test log_token_refresh method."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            audit_service_instance.log_token_refresh(
                user_id="user123", ip_address="192.168.1.1", user_agent="TestAgent"
            )

            mock_log_event.assert_called_once_with(
                AuditEventType.TOKEN_REFRESH,
                user_id="user123",
                ip_address="192.168.1.1",
                user_agent="TestAgent",
            )

    def test_log_profile_update(self, audit_service_instance):
        """Test log_profile_update method."""
        with patch.object(audit_service_instance, "log_event") as mock_log_event:
            fields_changed = ["first_name", "email"]

            audit_service_instance.log_profile_update(
                user_id="user123",
                email="test@example.com",
                ip_address="192.168.1.1",
                user_agent="TestAgent",
                fields_changed=fields_changed,
            )

            mock_log_event.assert_called_once_with(
                AuditEventType.PROFILE_UPDATE,
                user_id="user123",
                email="test@example.com",
                ip_address="192.168.1.1",
                user_agent="TestAgent",
                additional_data={"fields_changed": fields_changed},
            )

    def test_module_instance_available(self):
        """Test that the module-level instance is available."""
        assert audit_service is not None
        assert isinstance(audit_service, AuditService)
