"""Email service for sending emails via Resend or Maildev."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

import resend
from jinja2 import Environment, FileSystemLoader, select_autoescape

if TYPE_CHECKING:
    from resend.emails._emails import Emails

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        """Initialize email service."""
        self.is_development = settings.node_env == "development"
        self.use_maildev = settings.auth.use_maildev or self.is_development

        if not self.use_maildev:
            # Configure Resend API
            resend.api_key = settings.auth.resend_api_key

        # Setup Jinja2 for email templates
        self.template_env = Environment(
            loader=FileSystemLoader("src/templates/emails"),
            autoescape=select_autoescape(["html", "xml"]),
        )

    async def send_email(
        self,
        to: list[str],
        subject: str,
        html_content: str,
        text_content: str | None = None,
        from_email: str | None = None,
        reply_to: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> bool:
        """Send an email.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional)
            from_email: Sender email address
            reply_to: Reply-to email address
            headers: Additional email headers

        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            if self.use_maildev:
                return await self._send_via_maildev(to, subject, html_content, text_content, from_email)
            else:
                return await self._send_via_resend(
                    to, subject, html_content, text_content, from_email, reply_to, headers
                )
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def _send_via_resend(
        self,
        to: list[str],
        subject: str,
        html_content: str,
        text_content: str | None = None,
        from_email: str | None = None,
        reply_to: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> bool:
        """Send email via Resend API."""
        try:
            # Prepare headers dict
            headers_dict = headers.copy() if headers else {}

            # Add sandbox header for development
            if self.is_development:
                headers_dict["X-Entity-Ref-ID"] = "development"

            # Build request payload
            send_params: Emails.SendParams = {
                "from": from_email or f"Infinite Scribe <{settings.auth.resend_from_email}>",
                "to": to,
                "subject": subject,
                "html": html_content,
            }

            if text_content:
                send_params["text"] = text_content
            if reply_to:
                send_params["reply_to"] = reply_to
            if headers_dict:
                send_params["headers"] = headers_dict

            # Send email
            response = resend.Emails.send(send_params)
            logger.info(f"Email sent successfully via Resend: {response}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email via Resend: {e}")
            return False

    async def _send_via_maildev(
        self,
        to: list[str],
        subject: str,
        html_content: str,
        text_content: str | None = None,
        from_email: str | None = None,
    ) -> bool:
        """Send email via Maildev SMTP server."""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email or f"Infinite Scribe <{settings.auth.resend_from_email}>"
            msg["To"] = ", ".join(to)

            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, "plain")
                msg.attach(text_part)

            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # Send via SMTP
            with smtplib.SMTP(settings.auth.maildev_host, settings.auth.maildev_port) as server:
                server.send_message(msg)

            logger.info(f"Email sent successfully via Maildev to {to}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email via Maildev: {e}")
            return False

    async def send_verification_email(self, user_email: str, user_name: str, verification_url: str) -> bool:
        """Send email verification email.

        Args:
            user_email: Recipient email address
            user_name: User's name
            verification_url: URL for email verification

        Returns:
            True if email was sent successfully
        """
        # Render templates
        html_template = self.template_env.get_template("verify_email.html")
        text_template = self.template_env.get_template("verify_email.txt")

        context = {
            "user_name": user_name,
            "verification_url": verification_url,
            "app_name": "Infinite Scribe",
        }

        html_content = html_template.render(**context)
        text_content = text_template.render(**context)

        return await self.send_email(
            to=[user_email],
            subject="Verify your email address",
            html_content=html_content,
            text_content=text_content,
        )

    async def send_password_reset_email(self, user_email: str, user_name: str, reset_url: str) -> bool:
        """Send password reset email.

        Args:
            user_email: Recipient email address
            user_name: User's name
            reset_url: URL for password reset

        Returns:
            True if email was sent successfully
        """
        # Render templates
        html_template = self.template_env.get_template("password_reset.html")
        text_template = self.template_env.get_template("password_reset.txt")

        context = {
            "user_name": user_name,
            "reset_url": reset_url,
            "app_name": "Infinite Scribe",
            "expire_hours": settings.auth.password_reset_expire_hours,
        }

        html_content = html_template.render(**context)
        text_content = text_template.render(**context)

        return await self.send_email(
            to=[user_email],
            subject="Reset your password",
            html_content=html_content,
            text_content=text_content,
        )

    async def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Send welcome email to new user.

        Args:
            user_email: Recipient email address
            user_name: User's name

        Returns:
            True if email was sent successfully
        """
        # Render templates
        html_template = self.template_env.get_template("welcome.html")
        text_template = self.template_env.get_template("welcome.txt")

        context = {
            "user_name": user_name,
            "app_name": "Infinite Scribe",
            "app_url": settings.frontend_url,
        }

        html_content = html_template.render(**context)
        text_content = text_template.render(**context)

        return await self.send_email(
            to=[user_email],
            subject="Welcome to Infinite Scribe!",
            html_content=html_content,
            text_content=text_content,
        )

    async def send_password_changed_email(self, user_email: str, user_name: str) -> bool:
        """Send password changed notification email.

        Args:
            user_email: Recipient email address
            user_name: User's name

        Returns:
            True if email was sent successfully
        """
        # Render templates
        html_template = self.template_env.get_template("password_changed.html")
        text_template = self.template_env.get_template("password_changed.txt")

        context = {
            "user_name": user_name,
            "app_name": "Infinite Scribe",
            "app_url": settings.frontend_url,
            "support_email": settings.auth.resend_from_email,
        }

        html_content = html_template.render(**context)
        text_content = text_template.render(**context)

        return await self.send_email(
            to=[user_email],
            subject="Password Changed Successfully",
            html_content=html_content,
            text_content=text_content,
        )


# Create singleton instance
email_service = EmailService()
