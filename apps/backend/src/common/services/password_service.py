"""Password service for hashing and validation."""

import re
from typing import Any

from passlib.context import CryptContext

from src.core.auth_config import auth_config


class PasswordService:
    """Service for password hashing and validation."""

    def __init__(self):
        """Initialize password service."""
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.min_length = auth_config.PASSWORD_MIN_LENGTH

        # Common passwords to check against
        self.common_passwords = {
            "password",
            "123456",
            "password123",
            "admin",
            "letmein",
            "welcome",
            "monkey",
            "dragon",
            "baseball",
            "iloveyou",
            "trustno1",
            "1234567",
            "sunshine",
            "master",
            "123456789",
            "welcome123",
            "shadow",
            "ashley",
            "football",
            "jesus",
            "michael",
            "ninja",
            "mustang",
            "password1",
        }

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches, False otherwise
        """
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

    def validate_password_strength(self, password: str) -> dict[str, Any]:
        """Validate password strength and return detailed results.

        Args:
            password: Password to validate

        Returns:
            Dictionary with validation results:
                - is_valid: Whether password meets minimum requirements
                - score: Strength score (0-5)
                - errors: List of validation errors
                - suggestions: List of improvement suggestions
        """
        errors = []
        suggestions = []
        score = 0

        # Check minimum length
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        else:
            score += 1

        # Check for uppercase
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        else:
            score += 1

        # Check for lowercase
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
        else:
            score += 1

        # Check for digit
        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")
        else:
            score += 1

        # Check for special character (bonus point, not required)
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1

        # Check against common passwords
        if password.lower() in self.common_passwords:
            score = max(0, score - 2)
            suggestions.append("This password is too common. Please choose a more unique password")

        # Additional checks for better passwords
        if len(password) >= 12:
            score = min(5, score + 1)

        # Check for repeated characters
        if re.search(r"(.)\1{2,}", password):
            suggestions.append("Avoid using repeated characters")

        # Check for sequential characters
        if self._has_sequential_chars(password):
            suggestions.append("Avoid using sequential characters like '123' or 'abc'")

        return {
            "is_valid": len(errors) == 0,
            "score": min(5, score),
            "errors": errors,
            "suggestions": suggestions,
        }

    def _has_sequential_chars(self, password: str) -> bool:
        """Check if password contains sequential characters.

        Args:
            password: Password to check

        Returns:
            True if sequential characters found
        """
        sequences = [
            "0123456789",
            "abcdefghijklmnopqrstuvwxyz",
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm",
        ]

        password_lower = password.lower()
        for seq in sequences:
            for i in range(len(seq) - 2):
                if seq[i : i + 3] in password_lower:
                    return True
                # Check reverse
                if seq[i + 2 : i - 1 : -1] in password_lower:
                    return True

        return False
