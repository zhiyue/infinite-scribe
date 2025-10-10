"""Email service for sending emails via Resend or Maildev."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

import resend

if TYPE_CHECKING:
    from resend.emails._emails import Emails

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmailClient:
    """Client for sending emails via external providers."""

    def __init__(self):
        """Initialize email client."""
        self.is_development = settings.node_env == "development"
        self.use_maildev = settings.auth.use_maildev or self.is_development

        if not self.use_maildev:
            # Configure Resend API
            resend.api_key = settings.auth.resend_api_key

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


# Create instance for backward compatibility
email_client = EmailClient()


# Backward compatibility - remove this line since email_client is created above
