"""Audit logging service for security events."""

import json
import logging
from enum import Enum
from typing import Any

from src.common.utils.datetime_utils import utc_now


class AuditEventType(str, Enum):
    """Audit event types."""

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_SUCCESS = "password_reset_success"
    EMAIL_VERIFICATION = "email_verification"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    TOKEN_REFRESH = "token_refresh"
    PROFILE_UPDATE = "profile_update"


class AuditService:
    """Service for logging security and user events."""

    def __init__(self):
        """Initialize audit service."""
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # Create file handler for audit logs
        if not self.logger.handlers:
            import os

            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            handler = logging.FileHandler("logs/audit.log")
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        additional_data: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
    ):
        """Log an audit event.

        Args:
            event_type: Type of event being logged
            user_id: ID of the user (if applicable)
            email: Email of the user (if applicable)
            ip_address: IP address of the request
            user_agent: User agent string
            additional_data: Additional event-specific data
            success: Whether the event was successful
            error_message: Error message if event failed
        """
        audit_data = {
            "timestamp": utc_now().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "email": email,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "success": success,
            "error_message": error_message,
            "additional_data": additional_data or {},
        }

        # Log as JSON for easier parsing
        self.logger.info(json.dumps(audit_data))

    def log_login_success(self, user_id: str, email: str, ip_address: str, user_agent: str):
        """Log successful login."""
        self.log_event(
            AuditEventType.LOGIN_SUCCESS,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_login_failure(self, email: str, ip_address: str, user_agent: str, reason: str):
        """Log failed login attempt."""
        self.log_event(
            AuditEventType.LOGIN_FAILURE,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message=reason,
        )

    def log_logout(self, user_id: str, email: str, ip_address: str, user_agent: str):
        """Log user logout."""
        self.log_event(
            AuditEventType.LOGOUT,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_registration(self, user_id: str, email: str, ip_address: str, user_agent: str):
        """Log user registration."""
        self.log_event(
            AuditEventType.REGISTER,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_password_change(self, user_id: str, email: str, ip_address: str, user_agent: str):
        """Log password change."""
        self.log_event(
            AuditEventType.PASSWORD_CHANGE,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_password_reset_request(self, email: str, ip_address: str, user_agent: str):
        """Log password reset request."""
        self.log_event(
            AuditEventType.PASSWORD_RESET_REQUEST,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_password_reset_success(self, user_id: str, email: str, ip_address: str, user_agent: str):
        """Log successful password reset."""
        self.log_event(
            AuditEventType.PASSWORD_RESET_SUCCESS,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_account_locked(self, user_id: str, email: str, ip_address: str, failed_attempts: int):
        """Log account lockout."""
        self.log_event(
            AuditEventType.ACCOUNT_LOCKED,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            additional_data={"failed_attempts": failed_attempts},
        )

    def log_account_unlocked(self, user_id: str, email: str, unlock_reason: str = "automatic"):
        """Log account unlock."""
        self.log_event(
            AuditEventType.ACCOUNT_UNLOCKED,
            user_id=user_id,
            email=email,
            additional_data={"unlock_reason": unlock_reason},
        )

    def log_rate_limit_exceeded(self, ip_address: str, endpoint: str, user_id: str | None = None):
        """Log rate limit exceeded."""
        self.log_event(
            AuditEventType.RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            ip_address=ip_address,
            success=False,
            additional_data={"endpoint": endpoint},
        )

    def log_unauthorized_access(self, ip_address: str, endpoint: str, user_agent: str, reason: str):
        """Log unauthorized access attempt."""
        self.log_event(
            AuditEventType.UNAUTHORIZED_ACCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message=reason,
            additional_data={"endpoint": endpoint},
        )

    def log_token_refresh(self, user_id: str, ip_address: str, user_agent: str):
        """Log token refresh."""
        self.log_event(
            AuditEventType.TOKEN_REFRESH,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_profile_update(self, user_id: str, email: str, ip_address: str, user_agent: str, fields_changed: list):
        """Log profile update."""
        self.log_event(
            AuditEventType.PROFILE_UPDATE,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data={"fields_changed": fields_changed},
        )


# Global audit service instance
audit_service = AuditService()
