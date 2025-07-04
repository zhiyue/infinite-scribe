"""Mock services for testing."""

from unittest.mock import AsyncMock, MagicMock


class MockRedis:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self.data = {}
    
    def set(self, key: str, value: str, ex: int = None):
        """Mock set method."""
        self.data[key] = value
        return True
    
    def setex(self, key: str, ex: int, value: str):
        """Mock setex method."""
        self.data[key] = value
        return True
    
    def get(self, key: str):
        """Mock get method."""
        return self.data.get(key)
    
    def delete(self, key: str):
        """Mock delete method."""
        if key in self.data:
            del self.data[key]
            return 1
        return 0
    
    def exists(self, key: str):
        """Mock exists method."""
        return 1 if key in self.data else 0
    
    def clear(self):
        """Clear all data."""
        self.data.clear()


class MockEmailService:
    """Mock email service for testing."""
    
    def __init__(self):
        self.sent_emails = []
    
    async def send_verification_email(self, email: str, token: str):
        """Mock send verification email."""
        self.sent_emails.append({
            "type": "verification",
            "email": email,
            "token": token
        })
        return {"success": True}
    
    async def send_welcome_email(self, email: str, name: str):
        """Mock send welcome email."""
        self.sent_emails.append({
            "type": "welcome",
            "email": email,
            "name": name
        })
        return {"success": True}
    
    async def send_password_reset_email(self, email: str, token: str):
        """Mock send password reset email."""
        self.sent_emails.append({
            "type": "password_reset",
            "email": email,
            "token": token
        })
        return {"success": True}
    
    def clear(self):
        """Clear sent emails."""
        self.sent_emails.clear()


# Global mock instances for test session
mock_redis = MockRedis()
mock_email_service = MockEmailService()