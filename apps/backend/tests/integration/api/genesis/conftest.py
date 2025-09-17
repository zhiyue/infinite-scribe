"""Genesis-specific test fixtures."""

import random
import time
from uuid import uuid4

import pytest
from src.common.services.user.auth_service import auth_service
from src.models.novel import Novel
from src.models.user import User


@pytest.fixture
async def test_novel(pg_session):
    """Create a test novel for Genesis flow tests."""
    # Ensure the mock user exists in the database to satisfy foreign key constraints
    from sqlalchemy import select

    result = await pg_session.execute(select(User).where(User.id == 999))
    mock_user = result.scalar_one_or_none()

    if not mock_user:
        mock_user = User(
            id=999,
            username="testuser",
            email="test@example.com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6QlTUpSxKO",
            is_active=True,
            is_verified=True,
        )
        pg_session.add(mock_user)
        await pg_session.commit()

    # Create a unique novel
    timestamp = str(int(time.time() * 1000000))
    random_suffix = str(random.randint(1000, 9999))
    unique_id = f"{timestamp}_{random_suffix}"

    novel = Novel(
        id=uuid4(),
        title=f"Test Novel for Genesis {unique_id}",
        theme="Test Theme",
        writing_style="Test Style",
        target_chapters=10,
        completed_chapters=0,
        status="GENESIS",
        version=1,
        user_id=999,  # Must match the mock user ID in async_client fixture
    )

    pg_session.add(novel)
    await pg_session.commit()
    await pg_session.refresh(novel)
    return novel


@pytest.fixture
async def other_test_user(pg_session):
    """Create another test user for access control tests."""
    timestamp = str(int(time.time() * 1000000))
    random_suffix = str(random.randint(1000, 9999))
    unique_id = f"{timestamp}_{random_suffix}"

    user = User(
        username=f"otheruser_{unique_id}",
        email=f"otheruser_{unique_id}@example.com",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6QlTUpSxKO",  # "testpass"
        is_active=True,
        is_verified=True,
    )
    pg_session.add(user)
    await pg_session.commit()
    await pg_session.refresh(user)
    return user


@pytest.fixture
async def other_user_headers(other_test_user):
    """Create authentication headers for the other test user."""
    # Create token for the other user
    access_token, _, _ = auth_service.create_access_token(
        str(other_test_user.id), {"email": other_test_user.email, "username": other_test_user.username}
    )
    return {"Authorization": f"Bearer {access_token}"}
