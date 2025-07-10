"""User service for authentication and user management."""

import logging
from datetime import datetime, timedelta
from typing import Any, cast

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.email_service import email_service
from src.common.services.email_tasks import email_tasks
from src.common.services.jwt_service import jwt_service
from src.common.services.password_service import PasswordService
from src.common.utils.datetime_utils import utc_now
from src.core.config import settings
from src.models.email_verification import EmailVerification, VerificationPurpose
from src.models.session import Session
from src.models.user import User

logger = logging.getLogger(__name__)

# Create singleton instance
password_service = PasswordService()


class UserService:
    """Service for user management and authentication."""

    def __init__(self):
        """Initialize user service."""
        self.password_service = password_service
        self.jwt_service = jwt_service
        self.email_service = email_service
        self.frontend_url = settings.frontend_url or "http://localhost:3000"

    async def register_user(
        self,
        db: AsyncSession,
        user_data: dict[str, Any],
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Register a new user.

        Args:
            db: Database session
            user_data: User registration data
            background_tasks: Optional FastAPI background tasks for async email sending

        Returns:
            Result dictionary with success status and user data or error
        """
        try:
            # Validate password strength
            password_result = self.password_service.validate_password_strength(user_data["password"])
            if not password_result["is_valid"]:
                return {"success": False, "error": "; ".join(password_result["errors"])}

            # Check if user already exists
            existing_user = await db.execute(
                select(User).where((User.email == user_data["email"]) | (User.username == user_data["username"]))
            )
            if existing_user.scalar_one_or_none():
                return {
                    "success": False,
                    "error": "User with this email or username already exists",
                }

            # Create new user
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=self.password_service.hash_password(user_data["password"]),
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                is_active=True,
                is_verified=False,
            )

            db.add(user)
            await db.commit()
            await db.refresh(user)

            # Create email verification token
            verification = EmailVerification.create_for_user(
                user_id=cast(int, user.id),
                email=cast(str, user.email),
                purpose=VerificationPurpose.EMAIL_VERIFY,
                expires_in_hours=settings.auth.email_verification_expire_hours,
            )
            db.add(verification)
            await db.commit()

            # Send verification email
            verification_url = f"{self.frontend_url}/auth/verify-email?token={verification.token}"

            if background_tasks:
                # 使用异步任务发送邮件
                await email_tasks.send_verification_email_async(
                    background_tasks,
                    cast(str, user.email),
                    user.full_name,
                    verification_url,
                )
            else:
                # 兼容旧代码，同步发送邮件
                await self.email_service.send_verification_email(
                    cast(str, user.email),
                    user.full_name,
                    verification_url,
                )

            return {
                "success": True,
                "user": user.to_dict(),
                "message": "Registration successful. Please check your email to verify your account.",
            }

        except IntegrityError:
            await db.rollback()
            return {"success": False, "error": "User with this email or username already exists"}
        except Exception as e:
            logger.error(f"Registration error: {e}")
            await db.rollback()
            return {"success": False, "error": "An error occurred during registration"}

    async def login(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Login a user.

        Args:
            db: Database session
            email: User's email
            password: User's password
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Result dictionary with tokens and user data or error
        """
        try:
            # Find user by email
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if not user:
                return {"success": False, "error": "Invalid credentials"}

            # Check if account is locked
            if getattr(user, "is_locked", False):
                return {"success": False, "error": f"Account is locked until {user.locked_until}"}

            # Check if account is verified
            if not getattr(user, "is_verified", False):
                return {"success": False, "error": "Please verify your email before logging in"}

            # Verify password
            if not self.password_service.verify_password(password, cast(str, user.password_hash)):
                # Increment failed login attempts
                user.failed_login_attempts = getattr(user, "failed_login_attempts", 0) + 1

                # Lock account if too many attempts
                if getattr(user, "failed_login_attempts", 0) >= settings.auth.account_lockout_attempts:
                    user.locked_until = utc_now() + timedelta(minutes=settings.auth.account_lockout_duration_minutes)

                await db.commit()
                return {"success": False, "error": "Invalid credentials"}

            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.last_login_at = utc_now()
            user.last_login_ip = ip_address

            # Create tokens
            access_token, jti, access_expires = self.jwt_service.create_access_token(
                str(user.id), {"email": user.email, "username": user.username}
            )
            refresh_token, refresh_expires = self.jwt_service.create_refresh_token(str(user.id))

            # Create session
            session = Session(
                user_id=user.id,
                jti=jti,
                refresh_token=refresh_token,
                access_token_expires_at=access_expires,
                refresh_token_expires_at=refresh_expires,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.add(session)
            await db.commit()

            return {
                "success": True,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": user.to_dict(),
            }

        except Exception as e:
            logger.error(f"Login error: {e}")
            await db.rollback()
            return {"success": False, "error": "An error occurred during login"}

    async def verify_email(
        self,
        db: AsyncSession,
        token: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Verify user's email address.

        Args:
            db: Database session
            token: Verification token
            background_tasks: Optional FastAPI background tasks for async email sending

        Returns:
            Result dictionary with success status
        """
        try:
            # Find verification token
            result = await db.execute(
                select(EmailVerification).where(
                    EmailVerification.token == token,
                    EmailVerification.purpose == VerificationPurpose.EMAIL_VERIFY,
                )
            )
            verification = result.scalar_one_or_none()

            if not verification:
                return {"success": False, "error": "Invalid verification token"}

            # Check if token is valid
            if not verification.is_valid:
                if verification.is_expired:
                    return {"success": False, "error": "Verification token has expired"}
                else:
                    return {"success": False, "error": "Verification token has already been used"}

            # Get user
            result = await db.execute(select(User).where(User.id == verification.user_id))
            user = result.scalar_one_or_none()

            if not user:
                return {"success": False, "error": "User not found"}

            # Mark user as verified
            user.is_verified = True
            user.email_verified_at = utc_now()

            # Mark token as used
            verification.mark_as_used()

            await db.commit()

            # Send welcome email
            if background_tasks:
                # 使用异步任务发送邮件
                await email_tasks.send_welcome_email_async(
                    background_tasks,
                    cast(str, user.email),
                    user.full_name,
                )
            else:
                # 兼容旧代码，同步发送邮件
                await self.email_service.send_welcome_email(
                    cast(str, user.email),
                    user.full_name,
                )

            return {"success": True, "message": "Email verified successfully"}

        except Exception as e:
            logger.error(f"Email verification error: {e}")
            await db.rollback()
            return {"success": False, "error": "An error occurred during email verification"}

    async def request_password_reset(
        self,
        db: AsyncSession,
        email: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Request password reset.

        Args:
            db: Database session
            email: User's email
            background_tasks: Optional FastAPI background tasks for async email sending

        Returns:
            Result dictionary with success status
        """
        try:
            # Find user
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if not user:
                # Return success to prevent email enumeration
                return {
                    "success": True,
                    "message": "If the email exists, a reset link has been sent",
                }

            # Create password reset token
            verification = EmailVerification.create_for_user(
                user_id=cast(int, user.id),
                email=cast(str, user.email),
                purpose=VerificationPurpose.PASSWORD_RESET,
                expires_in_hours=settings.auth.password_reset_expire_hours,
            )
            db.add(verification)
            await db.commit()

            # Send password reset email
            reset_url = f"{self.frontend_url}/auth/reset-password?token={verification.token}"

            if background_tasks:
                # 使用异步任务发送邮件
                await email_tasks.send_password_reset_email_async(
                    background_tasks,
                    cast(str, user.email),
                    user.full_name,
                    reset_url,
                )
            else:
                # 兼容旧代码，同步发送邮件
                await self.email_service.send_password_reset_email(
                    cast(str, user.email),
                    user.full_name,
                    reset_url,
                )

            return {"success": True, "message": "If the email exists, a reset link has been sent"}

        except Exception as e:
            logger.error(f"Password reset request error: {e}")
            return {"success": True, "message": "If the email exists, a reset link has been sent"}

    async def reset_password(self, db: AsyncSession, token: str, new_password: str) -> dict[str, Any]:
        """Reset user's password.

        Args:
            db: Database session
            token: Reset token
            new_password: New password

        Returns:
            Result dictionary with success status
        """
        try:
            # Validate new password
            password_result = self.password_service.validate_password_strength(new_password)
            if not password_result["is_valid"]:
                return {"success": False, "error": "; ".join(password_result["errors"])}

            # Find reset token
            result = await db.execute(
                select(EmailVerification).where(
                    EmailVerification.token == token,
                    EmailVerification.purpose == VerificationPurpose.PASSWORD_RESET,
                )
            )
            verification = result.scalar_one_or_none()

            if not verification or not verification.is_valid:
                return {"success": False, "error": "Invalid or expired reset token"}

            # Get user
            result = await db.execute(select(User).where(User.id == verification.user_id))
            user = result.scalar_one_or_none()

            if not user:
                return {"success": False, "error": "User not found"}

            # Update password
            user.password_hash = self.password_service.hash_password(new_password)
            user.password_changed_at = utc_now()

            # Mark token as used
            verification.mark_as_used()

            # Invalidate all user sessions
            sessions_result = await db.execute(
                select(Session).where(Session.user_id == user.id, Session.is_active.is_(True))
            )
            sessions = sessions_result.scalars().all()
            for session in sessions:
                session.revoke("Password reset")

            await db.commit()

            return {"success": True, "message": "Password reset successfully"}

        except Exception as e:
            logger.error(f"Password reset error: {e}")
            await db.rollback()
            return {"success": False, "error": "An error occurred during password reset"}

    async def logout(self, db: AsyncSession, jti: str) -> dict[str, Any]:
        """Logout a user.

        Args:
            db: Database session
            jti: JWT ID from access token

        Returns:
            Result dictionary with success status
        """
        try:
            # Find session by JTI
            result = await db.execute(select(Session).where(Session.jti == jti))
            session = result.scalar_one_or_none()

            if session:
                # Revoke session
                session.revoke("User logout")

                # Blacklist token
                self.jwt_service.blacklist_token(
                    cast(str, session.jti), cast(datetime, session.access_token_expires_at)
                )

                await db.commit()

            return {"success": True, "message": "Logged out successfully"}

        except Exception as e:
            logger.error(f"Logout error: {e}")
            return {"success": False, "error": "An error occurred during logout"}
