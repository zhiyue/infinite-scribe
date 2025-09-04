"""Integration test to assert Alembic migrations applied."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
@pytest.mark.integration
async def test_database_migrations_applied_successfully(postgres_test_session: AsyncSession):
    # Alembic version table exists
    result = await postgres_test_session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'alembic_version'
            );
            """
        )
    )
    assert result.scalar() is True, "Alembic version table should exist"

    # Current version is set
    result = await postgres_test_session.execute(text("SELECT version_num FROM alembic_version;"))
    version = result.scalar()
    assert version is not None, "Database should have a migration version"

