"""User service for authentication and user management."""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.common.services.password_service import PasswordService
from src.common.services.jwt_service import jwt_service
from src.common.services.email_service import email_service
from src.core.auth_config import auth_config
from src.core.config import settings
from src.models.user import User
from src.models.session import Session
from src.models.email_verification import EmailVerification, VerificationPurpose


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
        self.frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
    
    async def register_user(
        self,
        db: AsyncSession,
        user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Register a new user.
        
        Args:
            db: Database session
            user_data: User registration data
            
        Returns:
            Result dictionary with success status and user data or error
        """
        try:
            # Validate password strength
            password_result = self.password_service.validate_password_strength(
                user_data["password"]
            )
            if not password_result["is_valid"]:
                return {
                    "success": False,
                    "error": "; ".join(password_result["errors"])
                }
            
            # Check if user already exists
            existing_user = await db.execute(
                select(User).where(
                    (User.email == user_data["email"]) | 
                    (User.username == user_data["username"])
                )
            )
            if existing_user.scalar_one_or_none():
                return {
                    "success": False,
                    "error": "User with this email or username already exists"
                }
            
            # Create new user
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=self.password_service.hash_password(user_data["password"]),
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                is_active=True,
                is_verified=False
            )
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            # Create email verification token
            verification = EmailVerification.create_for_user(
                user_id=user.id,
                email=user.email,
                purpose=VerificationPurpose.EMAIL_VERIFY,
                expires_in_hours=auth_config.EMAIL_VERIFICATION_EXPIRE_HOURS
            )
            db.add(verification)
            await db.commit()
            
            # Send verification email
            verification_url = f"{self.frontend_url}/auth/verify-email?token={verification.token}"
            await self.email_service.send_verification_email(
                user.email,
                user.full_name,
                verification_url
            )
            
            return {
                "success": True,
                "user": user.to_dict(),
                "message": "Registration successful. Please check your email to verify your account."
            }
            
        except IntegrityError:
            await db.rollback()
            return {
                "success": False,
                "error": "User with this email or username already exists"
            }
        except Exception as e:
            logger.error(f"Registration error: {e}")
            await db.rollback()
            return {
                "success": False,
                "error": "An error occurred during registration"
            }
    
    async def login(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
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
            result = await db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {
                    "success": False,
                    "error": "Invalid credentials"
                }
            
            # Check if account is locked
            if user.is_locked:
                return {
                    "success": False,
                    "error": f"Account is locked until {user.locked_until}"
                }
            
            # Check if account is verified
            if not user.is_verified:
                return {
                    "success": False,
                    "error": "Please verify your email before logging in"
                }
            
            # Verify password
            if not self.password_service.verify_password(password, user.password_hash):
                # Increment failed login attempts
                user.failed_login_attempts += 1
                
                # Lock account if too many attempts
                if user.failed_login_attempts >= auth_config.ACCOUNT_LOCKOUT_ATTEMPTS:
                    user.locked_until = datetime.utcnow() + timedelta(
                        minutes=auth_config.ACCOUNT_LOCKOUT_DURATION_MINUTES
                    )
                    await db.commit()
                    return {
                        "success": False,
                        "error": "Account locked due to too many failed attempts"
                    }
                
                await db.commit()
                return {
                    "success": False,
                    "error": "Invalid credentials"
                }
            
            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.last_login_at = datetime.utcnow()
            user.last_login_ip = ip_address
            
            # Create tokens
            access_token, jti, access_expires = self.jwt_service.create_access_token(
                str(user.id),
                {"email": user.email, "username": user.username}
            )
            refresh_token, refresh_expires = self.jwt_service.create_refresh_token(
                str(user.id)
            )
            
            # Create session
            session = Session(
                user_id=user.id,
                jti=jti,
                refresh_token=refresh_token,
                access_token_expires_at=access_expires,
                refresh_token_expires_at=refresh_expires,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.add(session)
            await db.commit()
            
            return {
                "success": True,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": user.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            await db.rollback()
            return {
                "success": False,
                "error": "An error occurred during login"
            }
    
    async def verify_email(
        self,
        db: AsyncSession,
        token: str
    ) -> Dict[str, Any]:
        """Verify user's email address.
        
        Args:
            db: Database session
            token: Verification token
            
        Returns:
            Result dictionary with success status
        """
        try:
            # Find verification token
            result = await db.execute(
                select(EmailVerification).where(
                    EmailVerification.token == token,
                    EmailVerification.purpose == VerificationPurpose.EMAIL_VERIFY
                )
            )
            verification = result.scalar_one_or_none()
            
            if not verification:
                return {
                    "success": False,
                    "error": "Invalid verification token"
                }
            
            # Check if token is valid
            if not verification.is_valid:
                if verification.is_expired:
                    return {
                        "success": False,
                        "error": "Verification token has expired"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Verification token has already been used"
                    }
            
            # Get user
            result = await db.execute(
                select(User).where(User.id == verification.user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {
                    "success": False,
                    "error": "User not found"
                }
            
            # Mark user as verified
            user.is_verified = True
            user.email_verified_at = datetime.utcnow()
            
            # Mark token as used
            verification.mark_as_used()
            
            await db.commit()
            
            # Send welcome email
            await self.email_service.send_welcome_email(
                user.email,
                user.full_name
            )
            
            return {
                "success": True,
                "message": "Email verified successfully"
            }
            
        except Exception as e:
            logger.error(f"Email verification error: {e}")
            await db.rollback()
            return {
                "success": False,
                "error": "An error occurred during email verification"
            }
    
    async def request_password_reset(
        self,
        db: AsyncSession,
        email: str
    ) -> Dict[str, Any]:
        """Request password reset.
        
        Args:
            db: Database session
            email: User's email
            
        Returns:
            Result dictionary with success status
        """
        try:
            # Find user
            result = await db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                # Return success to prevent email enumeration
                return {
                    "success": True,
                    "message": "If the email exists, a reset link has been sent"
                }
            
            # Create password reset token
            verification = EmailVerification.create_for_user(
                user_id=user.id,
                email=user.email,
                purpose=VerificationPurpose.PASSWORD_RESET,
                expires_in_hours=auth_config.PASSWORD_RESET_EXPIRE_HOURS
            )
            db.add(verification)
            await db.commit()
            
            # Send password reset email
            reset_url = f"{self.frontend_url}/auth/reset-password?token={verification.token}"
            await self.email_service.send_password_reset_email(
                user.email,
                user.full_name,
                reset_url
            )
            
            return {
                "success": True,
                "message": "If the email exists, a reset link has been sent"
            }
            
        except Exception as e:
            logger.error(f"Password reset request error: {e}")
            return {
                "success": True,
                "message": "If the email exists, a reset link has been sent"
            }
    
    async def reset_password(
        self,
        db: AsyncSession,
        token: str,
        new_password: str
    ) -> Dict[str, Any]:
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
                return {
                    "success": False,
                    "error": "; ".join(password_result["errors"])
                }
            
            # Find reset token
            result = await db.execute(
                select(EmailVerification).where(
                    EmailVerification.token == token,
                    EmailVerification.purpose == VerificationPurpose.PASSWORD_RESET
                )
            )
            verification = result.scalar_one_or_none()
            
            if not verification or not verification.is_valid:
                return {
                    "success": False,
                    "error": "Invalid or expired reset token"
                }
            
            # Get user
            result = await db.execute(
                select(User).where(User.id == verification.user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {
                    "success": False,
                    "error": "User not found"
                }
            
            # Update password
            user.password_hash = self.password_service.hash_password(new_password)
            user.password_changed_at = datetime.utcnow()
            
            # Mark token as used
            verification.mark_as_used()
            
            # Invalidate all user sessions
            sessions_result = await db.execute(
                select(Session).where(
                    Session.user_id == user.id,
                    Session.is_active == True
                )
            )
            sessions = sessions_result.scalars().all()
            for session in sessions:
                session.revoke("Password reset")
            
            await db.commit()
            
            return {
                "success": True,
                "message": "Password reset successfully"
            }
            
        except Exception as e:
            logger.error(f"Password reset error: {e}")
            await db.rollback()
            return {
                "success": False,
                "error": "An error occurred during password reset"
            }
    
    async def logout(
        self,
        db: AsyncSession,
        jti: str
    ) -> Dict[str, Any]:
        """Logout a user.
        
        Args:
            db: Database session
            jti: JWT ID from access token
            
        Returns:
            Result dictionary with success status
        """
        try:
            # Find session by JTI
            result = await db.execute(
                select(Session).where(Session.jti == jti)
            )
            session = result.scalar_one_or_none()
            
            if session:
                # Revoke session
                session.revoke("User logout")
                
                # Blacklist token
                self.jwt_service.blacklist_token(
                    session.jti,
                    session.access_token_expires_at
                )
                
                await db.commit()
            
            return {
                "success": True,
                "message": "Logged out successfully"
            }
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return {
                "success": False,
                "error": "An error occurred during logout"
            }