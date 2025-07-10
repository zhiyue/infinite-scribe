"""Unit tests for password service."""

import pytest
from src.common.services.password_service import PasswordService


class TestPasswordService:
    """Test cases for PasswordService."""

    @pytest.fixture
    def password_service(self):
        """Create password service instance."""
        return PasswordService()

    @pytest.fixture
    def sample_passwords(self):
        """Sample passwords for testing."""
        return {
            "valid": "SecurePassword123!",
            "weak": "12345",
            "empty": "",
            "long": "a" * 200,
            "unicode": "密码Test123!",
            "special": "P@ssw0rd!#$%^&*()",
        }

    def test_hash_password_creates_different_hashes(self, password_service, sample_passwords):
        """Test that same password creates different hashes each time."""
        password = sample_passwords["valid"]
        hash1 = password_service.hash_password(password)
        hash2 = password_service.hash_password(password)

        assert hash1 != hash2  # Different salts should create different hashes
        assert isinstance(hash1, str)
        assert len(hash1) > 50  # Bcrypt hashes are typically 60 chars

    def test_verify_password_with_correct_password(self, password_service, sample_passwords):
        """Test password verification with correct password."""
        password = sample_passwords["valid"]
        hashed = password_service.hash_password(password)

        assert password_service.verify_password(password, hashed) is True

    def test_verify_password_with_incorrect_password(self, password_service, sample_passwords):
        """Test password verification with incorrect password."""
        password = sample_passwords["valid"]
        hashed = password_service.hash_password(password)

        assert password_service.verify_password("WrongPassword", hashed) is False

    def test_verify_password_with_empty_password(self, password_service):
        """Test password verification with empty password."""
        hashed = password_service.hash_password("ValidPassword123!")

        assert password_service.verify_password("", hashed) is False

    def test_hash_password_with_unicode(self, password_service, sample_passwords):
        """Test hashing passwords with unicode characters."""
        password = sample_passwords["unicode"]
        hashed = password_service.hash_password(password)

        assert password_service.verify_password(password, hashed) is True

    def test_hash_password_with_special_characters(self, password_service, sample_passwords):
        """Test hashing passwords with special characters."""
        password = sample_passwords["special"]
        hashed = password_service.hash_password(password)

        assert password_service.verify_password(password, hashed) is True

    def test_validate_password_strength_valid(self, password_service, sample_passwords):
        """Test password strength validation with valid password."""
        result = password_service.validate_password_strength(sample_passwords["valid"])

        assert result["is_valid"] is True
        assert result["score"] >= 3  # Strong password
        assert len(result["errors"]) == 0

    def test_validate_password_strength_too_short(self, password_service):
        """Test password strength validation with short password."""
        result = password_service.validate_password_strength("Pass1!")

        assert result["is_valid"] is False
        assert "at least 8 characters" in result["errors"][0].lower()

    def test_validate_password_strength_no_uppercase(self, password_service):
        """Test password strength validation without uppercase."""
        result = password_service.validate_password_strength("password123!")

        assert result["is_valid"] is False
        assert "uppercase" in result["errors"][0].lower()

    def test_validate_password_strength_no_lowercase(self, password_service):
        """Test password strength validation without lowercase."""
        result = password_service.validate_password_strength("PASSWORD123!")

        assert result["is_valid"] is False
        assert "lowercase" in result["errors"][0].lower()

    def test_validate_password_strength_no_digit(self, password_service):
        """Test password strength validation without digit."""
        result = password_service.validate_password_strength("Password!")

        assert result["is_valid"] is False
        assert "digit" in result["errors"][0].lower()

    def test_validate_password_strength_common_password(self, password_service):
        """Test password strength validation with common password."""
        result = password_service.validate_password_strength("Password123")

        assert result["score"] < 3  # Common password should have lower score

    def test_hash_performance(self, password_service, sample_passwords):
        """Test that hashing doesn't take too long."""
        import time

        password = sample_passwords["valid"]
        start = time.time()
        password_service.hash_password(password)
        duration = time.time() - start

        assert duration < 5.0  # Hashing should complete within 5 seconds (bcrypt rounds=12 can be slow)

    def test_verify_performance(self, password_service, sample_passwords):
        """Test that verification doesn't take too long."""
        import time

        password = sample_passwords["valid"]
        hashed = password_service.hash_password(password)

        start = time.time()
        password_service.verify_password(password, hashed)
        duration = time.time() - start

        assert duration < 0.5  # Verification should be faster than hashing
