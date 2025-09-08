"""User email service for handling user-related email business logic."""

import logging

from fastapi import BackgroundTasks
from jinja2 import Environment, FileSystemLoader, select_autoescape
from src.core.config import settings
from src.external.clients.email import EmailClient
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class UserEmailService:
    """Service for handling user-related email business logic."""

    def __init__(self, email_client: EmailClient):
        """Initialize user email service.

        Args:
            email_client: Email client for sending emails
        """
        self.email_client = email_client

        # Setup Jinja2 for email templates
        self.template_env = Environment(
            loader=FileSystemLoader("src/templates/emails"),
            autoescape=select_autoescape(["html", "xml"]),
        )

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

        return await self.email_client.send_email(
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

        return await self.email_client.send_email(
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

        return await self.email_client.send_email(
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

        from datetime import UTC, datetime

        context = {
            "user_name": user_name,
            "app_name": "Infinite Scribe",
            "app_url": settings.frontend_url,
            "support_email": settings.auth.resend_from_email,
            "changed_at": datetime.now(UTC).strftime("%Y-%m-%d at %H:%M UTC"),
        }

        html_content = html_template.render(**context)
        text_content = text_template.render(**context)

        return await self.email_client.send_email(
            to=[user_email],
            subject="Password Changed Successfully",
            html_content=html_content,
            text_content=text_content,
        )


class UserEmailTasks:
    """User email tasks with retry mechanism."""

    def __init__(self, user_email_service: UserEmailService):
        """Initialize user email tasks.

        Args:
            user_email_service: User email service instance
        """
        self.user_email_service = user_email_service

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=False,
    )
    async def _send_email_with_retry(
        self,
        email_type: str,
        to_email: str,
        **kwargs,
    ) -> bool:
        """Send email with retry mechanism.

        Args:
            email_type: Email type (verification, password_reset, welcome, password_changed)
            to_email: Recipient email address
            **kwargs: Other email parameters

        Returns:
            True if email was sent successfully
        """
        try:
            logger.info(f"Attempting to send {email_type} email to {to_email}")

            # Route to appropriate email method
            if email_type == "verification":
                result = await self.user_email_service.send_verification_email(
                    to_email,
                    kwargs.get("user_name", ""),
                    kwargs.get("verification_url", ""),
                )
            elif email_type == "password_reset":
                result = await self.user_email_service.send_password_reset_email(
                    to_email,
                    kwargs.get("user_name", ""),
                    kwargs.get("reset_url", ""),
                )
            elif email_type == "welcome":
                result = await self.user_email_service.send_welcome_email(
                    to_email,
                    kwargs.get("user_name", ""),
                )
            elif email_type == "password_changed":
                result = await self.user_email_service.send_password_changed_email(
                    to_email,
                    kwargs.get("user_name", ""),
                )
            else:
                logger.error(f"Unknown email type: {email_type}")
                return False

            if result:
                logger.info(f"Successfully sent {email_type} email to {to_email}")
            else:
                logger.warning(f"Failed to send {email_type} email to {to_email}")

            return result

        except Exception as e:
            logger.error(f"Error sending {email_type} email to {to_email}: {e}")
            # Re-raise exception to trigger retry
            raise

    async def send_verification_email_async(
        self,
        background_tasks: BackgroundTasks,
        user_email: str,
        user_name: str,
        verification_url: str,
    ) -> None:
        """Send verification email asynchronously.

        Args:
            background_tasks: FastAPI background tasks object
            user_email: User email
            user_name: User name
            verification_url: Verification URL
        """
        background_tasks.add_task(
            self._send_email_with_retry,
            email_type="verification",
            to_email=user_email,
            user_name=user_name,
            verification_url=verification_url,
        )
        logger.info(f"Added verification email task to queue: {user_email}")

    async def send_password_reset_email_async(
        self,
        background_tasks: BackgroundTasks,
        user_email: str,
        user_name: str,
        reset_url: str,
    ) -> None:
        """Send password reset email asynchronously.

        Args:
            background_tasks: FastAPI background tasks object
            user_email: User email
            user_name: User name
            reset_url: Reset URL
        """
        background_tasks.add_task(
            self._send_email_with_retry,
            email_type="password_reset",
            to_email=user_email,
            user_name=user_name,
            reset_url=reset_url,
        )
        logger.info(f"Added password reset email task to queue: {user_email}")

    async def send_welcome_email_async(
        self,
        background_tasks: BackgroundTasks,
        user_email: str,
        user_name: str,
    ) -> None:
        """Send welcome email asynchronously.

        Args:
            background_tasks: FastAPI background tasks object
            user_email: User email
            user_name: User name
        """
        background_tasks.add_task(
            self._send_email_with_retry,
            email_type="welcome",
            to_email=user_email,
            user_name=user_name,
        )
        logger.info(f"Added welcome email task to queue: {user_email}")

    async def send_password_changed_email_async(
        self,
        background_tasks: BackgroundTasks,
        user_email: str,
        user_name: str,
    ) -> None:
        """Send password changed email asynchronously.

        Args:
            background_tasks: FastAPI background tasks object
            user_email: User email
            user_name: User name
        """
        background_tasks.add_task(
            self._send_email_with_retry,
            email_type="password_changed",
            to_email=user_email,
            user_name=user_name,
        )
        logger.info(f"Added password changed email task to queue: {user_email}")


# Create instances for backward compatibility
from src.external.clients.email import email_client

user_email_service = UserEmailService(email_client)
user_email_tasks = UserEmailTasks(user_email_service)
