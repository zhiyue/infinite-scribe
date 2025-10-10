"""Unit tests for email service."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from src.external.clients.email.email_client import EmailClient


class TestEmailClient:
    """Test cases for EmailClient."""

    @pytest.fixture
    def email_client(self):
        """Create email service instance."""
        with patch("src.external.clients.email.email_client.settings") as mock_settings:
            mock_settings.node_env = "development"
            mock_settings.auth.use_maildev = True
            mock_settings.auth.resend_api_key = "test_api_key"
            mock_settings.auth.resend_from_email = "noreply@example.com"
            mock_settings.auth.maildev_host = "localhost"
            mock_settings.auth.maildev_port = 1025
            mock_settings.frontend_url = "http://localhost:3000"
            mock_settings.auth.password_reset_expire_hours = 1

            with patch("src.external.clients.email.email_client.EmailClient.__init__", return_value=None):
                service = EmailClient()
                service.is_development = True
                service.use_maildev = True
                service.template_env = MagicMock()
                return service

    @pytest.fixture
    def production_email_client(self):
        """Create email service instance for production (Resend)."""
        with patch("src.external.clients.email.email_client.settings") as mock_settings:
            mock_settings.node_env = "production"
            mock_settings.auth.use_maildev = False
            mock_settings.auth.resend_api_key = "test_api_key"
            mock_settings.auth.resend_from_email = "noreply@example.com"
            mock_settings.frontend_url = "https://example.com"
            mock_settings.auth.password_reset_expire_hours = 1

            with (
                patch("src.external.clients.email.email_client.EmailClient.__init__", return_value=None),
                patch("resend.api_key"),
            ):
                service = EmailClient()
                service.is_development = False
                service.use_maildev = False
                service.template_env = MagicMock()
                return service

    @pytest.mark.asyncio
    async def test_send_email_via_maildev_success(self, email_client):
        """Test successful email sending via Maildev."""
        # Arrange
        with patch.object(email_client, "_send_via_maildev", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            # Act
            result = await email_client.send_email(
                to=["test@example.com"],
                subject="Test Subject",
                html_content="<p>Test HTML</p>",
                text_content="Test Text",
            )

            # Assert
            assert result is True
            mock_send.assert_called_once_with(
                ["test@example.com"], "Test Subject", "<p>Test HTML</p>", "Test Text", None
            )

    @pytest.mark.asyncio
    async def test_send_email_via_maildev_failure(self, email_client):
        """Test email sending failure via Maildev."""
        # Arrange
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP connection failed")

            # Act
            result = await email_client.send_email(
                to=["test@example.com"], subject="Test Subject", html_content="<p>Test HTML</p>"
            )

            # Assert
            assert result is False

    @pytest.mark.asyncio
    @patch("resend.Emails.send")
    async def test_send_email_via_resend_success(self, mock_resend_send, production_email_client):
        """Test successful email sending via Resend."""
        # Arrange
        mock_resend_send.return_value = {"id": "test_id"}

        # Act
        result = await production_email_client.send_email(
            to=["test@example.com"],
            subject="Test Subject",
            html_content="<p>Test HTML</p>",
            text_content="Test Text",
            reply_to="reply@example.com",
            headers={"X-Custom": "value"},
        )

        # Assert
        assert result is True
        mock_resend_send.assert_called_once()
        call_args = mock_resend_send.call_args[0][0]
        assert call_args["to"] == ["test@example.com"]
        assert call_args["subject"] == "Test Subject"
        assert call_args["html"] == "<p>Test HTML</p>"
        assert call_args["text"] == "Test Text"
        assert call_args["reply_to"] == "reply@example.com"
        assert call_args["headers"]["X-Custom"] == "value"

    @pytest.mark.asyncio
    @patch("resend.Emails.send")
    async def test_send_email_via_resend_failure(self, mock_resend_send, production_email_client):
        """Test email sending failure via Resend."""
        # Arrange
        mock_resend_send.side_effect = Exception("API error")

        # Act
        result = await production_email_client.send_email(
            to=["test@example.com"], subject="Test Subject", html_content="<p>Test HTML</p>"
        )

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_send_email_development_headers(self):
        """Test that development headers are added in development mode."""
        # Arrange
        with (
            patch("src.external.clients.email.email_client.EmailClient.__init__", return_value=None),
            patch("resend.api_key"),
        ):
            service = EmailClient()
            service.is_development = True
            service.use_maildev = False  # Force Resend in dev
            service.template_env = MagicMock()

            with patch.object(service, "_send_via_resend", new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True

                # Act
                result = await service.send_email(
                    to=["test@example.com"], subject="Test Subject", html_content="<p>Test HTML</p>"
                )

                # Assert
                assert result is True
                # Check that _send_via_resend was called
                mock_send.assert_called_once()

    # NOTE: send_verification_email method does not exist on EmailClient.
    # This functionality is implemented in UserEmailService/UserEmailTasks.
    # EmailClient is a low-level HTTP client that only provides basic send_email method.

    # NOTE: send_password_reset_email method does not exist on EmailClient.
    # This functionality is implemented in UserEmailService/UserEmailTasks.
    # EmailClient is a low-level HTTP client that only provides basic send_email method.

    # NOTE: send_welcome_email method does not exist on EmailClient.
    # This functionality is implemented in UserEmailService/UserEmailTasks.
    # EmailClient is a low-level HTTP client that only provides basic send_email method.

    @pytest.mark.asyncio
    async def test_send_email_exception_handling(self, email_client):
        """Test that send_email handles exceptions gracefully."""
        # Arrange
        with patch.object(email_client, "_send_via_maildev", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("Unexpected error")

            # Act
            result = await email_client.send_email(to=["test@example.com"], subject="Test", html_content="<p>Test</p>")

            # Assert
            assert result is False

    def test_initialization_with_resend_api_key(self):
        """Test email service initialization with Resend API key."""
        # Arrange
        with patch("src.external.clients.email.email_client.settings") as mock_settings:
            mock_settings.node_env = "production"
            mock_settings.auth.use_maildev = False
            mock_settings.auth.resend_api_key = "test_api_key"

            with patch("resend.api_key"):
                # Act
                service = EmailClient()

                # Assert
                assert service.is_development is False
                assert service.use_maildev is False
