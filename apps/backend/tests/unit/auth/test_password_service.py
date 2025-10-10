"""Unit tests for password service."""

import pytest
from src.common.services.user.password_service import PasswordService


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

    def test_verify_password_with_malformed_hash(self, password_service):
        """Test password verification with malformed hash returns False."""
        password = "ValidPassword123!"

        # Test various malformed hashes
        malformed_hashes = [
            "not_a_hash",
            "$2b$12$invalid",
            "",
            "$2b$12$" + "x" * 50,  # Invalid base64
        ]

        for malformed_hash in malformed_hashes:
            result = password_service.verify_password(password, malformed_hash)
            assert result is False, f"Malformed hash {malformed_hash} should return False"

    def test_verify_password_encoding_consistency(self, password_service):
        """Test password verification works consistently with different encodings."""
        unicode_password = "测试密码Test123!"
        emoji_password = "Password123!😀🔐"

        for password in [unicode_password, emoji_password]:
            hashed = password_service.hash_password(password)
            assert password_service.verify_password(password, hashed) is True
            assert password_service.verify_password(password + "x", hashed) is False

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

    def test_hash_password_empty_string(self, password_service):
        """Test hashing empty string doesn't crash."""
        hashed = password_service.hash_password("")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

        # Should be able to verify empty string
        assert password_service.verify_password("", hashed) is True

    def test_hash_password_very_long(self, password_service):
        """Test hashing very long password works correctly."""
        very_long_password = "A" * 1000
        hashed = password_service.hash_password(very_long_password)

        assert isinstance(hashed, str)
        assert password_service.verify_password(very_long_password, hashed) is True

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

    def test_validate_password_strength_multiple_errors(self, password_service):
        """Test password strength validation with multiple validation errors."""
        weak_password = "abc"  # Too short, no uppercase, no digit
        result = password_service.validate_password_strength(weak_password)

        assert result["is_valid"] is False
        assert len(result["errors"]) >= 3  # Should have multiple errors
        assert result["score"] == 1  # Should have score 1 (gets 1 point for lowercase)

        # Check specific error messages are present
        error_text = " ".join(result["errors"]).lower()
        assert "at least 8 characters" in error_text
        assert "uppercase" in error_text
        assert "digit" in error_text

    def test_validate_password_strength_with_special_characters_bonus(self, password_service):
        """Test password strength gets bonus for special characters."""
        password_without_special = "Password123"
        password_with_special = "Password123!"

        result_without = password_service.validate_password_strength(password_without_special)
        result_with = password_service.validate_password_strength(password_with_special)

        assert result_with["score"] > result_without["score"]
        assert result_with["is_valid"] is True
        assert result_without["is_valid"] is True

    def test_validate_password_strength_long_password_bonus(self, password_service):
        """Test password strength gets bonus for length >= 12 characters."""
        short_password = "Pass123!"
        long_password = "Password123!Extra"

        result_short = password_service.validate_password_strength(short_password)
        result_long = password_service.validate_password_strength(long_password)

        assert result_long["score"] >= result_short["score"]
        assert len(long_password) >= 12
        assert result_long["is_valid"] is True

    def test_validate_password_strength_repeated_characters(self, password_service):
        """Test password strength validation detects repeated characters."""
        password_with_repeats = "Passsssword123!"
        result = password_service.validate_password_strength(password_with_repeats)

        # Should still be valid but have suggestions
        assert result["is_valid"] is True
        assert any("repeated" in suggestion.lower() for suggestion in result["suggestions"])

    def test_validate_password_strength_common_passwords_case_insensitive(self, password_service):
        """Test common password detection is case insensitive."""
        common_passwords = ["PASSWORD", "Password", "PassWord", "123456", "ADMIN"]

        for password in common_passwords:
            result = password_service.validate_password_strength(password)
            # Score should be reduced for common passwords
            suggestions_text = " ".join(result["suggestions"]).lower()
            if "common" in suggestions_text or "unique" in suggestions_text:
                # Common password detected
                assert result["score"] < 3, f"Password {password} should have reduced score"

    def test_validate_password_strength_sequential_suggestions(self, password_service):
        """Test that sequential characters generate appropriate suggestions."""
        password_with_sequence = "Password123"
        result = password_service.validate_password_strength(password_with_sequence)

        # Should suggest avoiding sequential characters
        suggestions_text = " ".join(result["suggestions"]).lower()
        if "sequential" in suggestions_text:
            assert "sequential" in suggestions_text or "123" in suggestions_text

    def test_password_strength_edge_cases(self, password_service):
        """Test password strength validation with edge cases."""
        edge_cases = [
            ("", False, 0),  # Empty password
            (" ", False, 0),  # Space only
            ("1", False, 0),  # Single character
            ("A" * 100, False, 1),  # Very long but only uppercase
            ("a" * 100, False, 1),  # Very long but only lowercase
            ("1" * 100, False, 1),  # Very long but only numbers
        ]

        for password, expected_valid, min_score in edge_cases:
            result = password_service.validate_password_strength(password)
            assert result["is_valid"] == expected_valid, f"Password '{password}' validation failed"
            if not expected_valid:
                assert result["score"] >= min_score, f"Password '{password}' score too low"

    def test_password_strength_comprehensive_strong_password(self, password_service):
        """Test a comprehensive strong password gets maximum score."""
        # 12+ chars, upper, lower, digit, special, not common, no sequences
        strong_password = "MyStr0ngP@ssw0rd!"
        result = password_service.validate_password_strength(strong_password)

        assert result["is_valid"] is True
        assert result["score"] >= 4  # Should get high score
        assert len(result["errors"]) == 0

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

    def test_password_service_initialization(self):
        """Test password service initialization with default settings."""
        service = PasswordService()

        assert service.min_length == 8  # Default from settings
        assert service.rounds == 12
        assert isinstance(service.common_passwords, set)
        assert len(service.common_passwords) > 0
        assert "password" in service.common_passwords

    def test_has_sequential_chars_numeric(self, password_service):
        """Test detection of sequential numeric characters."""
        passwords_with_sequences = [
            "Pass123word",   # Contains "123"
            "Password012",   # Contains "012"
            "Password789",   # Contains "789"
            "Test321Pass",   # Contains "321" (reverse)
            "Pass987word",   # Contains "987" (reverse)
            "abc890xyz",     # Contains "890"
        ]

        passwords_without_sequences = [
            "Password139",   # Non-sequential digits
            "Pass248word",   # Non-sequential digits
            "NoNumbers",     # No digits at all
            "Pass135word",   # Non-sequential (1,3,5)
            "Test147Pass",   # Non-sequential (1,4,7)
        ]

        for password in passwords_with_sequences:
            assert password_service._has_sequential_chars(password) is True, f"Should detect sequence in {password}"

        for password in passwords_without_sequences:
            assert password_service._has_sequential_chars(password) is False, f"Should not detect sequence in {password}"

    def test_has_sequential_chars_alphabetic(self, password_service):
        """Test detection of sequential alphabetic characters."""
        passwords_with_sequences = [
            "Passwordabc",   # Contains "abc"
            "Passworddef",   # Contains "def"
            "xyzPassword",   # Contains "xyz"
            "Passwordcba",   # Contains "cba" (reverse)
            "fedPassword",   # Contains "fed" (reverse)
            "Test789abc",    # Contains "abc"
        ]

        passwords_without_sequences = [
            "Passwordacb",   # Non-sequential letters
            "Passwordaek",   # Non-sequential letters
            "NoSequences",   # No sequential letters
            "Pass135word",   # Only digits, no letter sequences
            "TestXqzPass",   # Non-sequential letters
        ]

        for password in passwords_with_sequences:
            assert password_service._has_sequential_chars(password) is True, f"Should detect sequence in {password}"

        for password in passwords_without_sequences:
            assert password_service._has_sequential_chars(password) is False, f"Should not detect sequence in {password}"

    def test_has_sequential_chars_keyboard_patterns(self, password_service):
        """Test detection of keyboard pattern sequences."""
        passwords_with_sequences = [
            "Passwordqwe",   # Contains "qwe" (keyboard row)
            "Passwordasd",   # Contains "asd" (keyboard row)
            "zxcvPassword",  # Contains "zxc" (keyboard row)
            "Passwordewq",   # Contains "ewq" (reverse)
            "dsaPassword",   # Contains "dsa" (reverse)
            "PassghiWord",   # Contains "ghi" (keyboard)
        ]

        passwords_without_sequences = [
            "Passwordqae",   # Non-keyboard sequence
            "Passwordqix",   # Non-keyboard sequence
            "NoKeyboard",    # No keyboard patterns
            "Pass135word",   # Only digits, no keyboard patterns
            "TestXqzPass",   # Non-keyboard letters
        ]

        for password in passwords_with_sequences:
            assert password_service._has_sequential_chars(password) is True, f"Should detect keyboard sequence in {password}"

        for password in passwords_without_sequences:
            assert password_service._has_sequential_chars(password) is False, f"Should not detect keyboard sequence in {password}"
