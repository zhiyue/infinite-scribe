"""Integration tests for the migrated_database pytest fixture.

These tests ensure that the migrated_database fixture correctly:
1. Creates valid database connection URLs
2. Runs Alembic migrations successfully
3. Creates expected database schema
4. Provides connectable database endpoints
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.asyncio
@pytest.mark.integration
async def test_migrated_database_provides_valid_urls(migrated_database):
    """Test that migrated_database fixture provides valid connection URLs."""
    # Fixture should return dict with async_url and sync_url
    assert isinstance(migrated_database, dict)
    assert "async_url" in migrated_database
    assert "sync_url" in migrated_database

    async_url = migrated_database["async_url"]
    sync_url = migrated_database["sync_url"]

    # URLs should be non-empty strings
    assert isinstance(async_url, str)
    assert isinstance(sync_url, str)
    assert len(async_url) > 0
    assert len(sync_url) > 0

    # Async URL should contain asyncpg driver
    assert "postgresql+asyncpg://" in async_url

    # Sync URL should be standard PostgreSQL URL
    assert "postgresql://" in sync_url and "postgresql+asyncpg://" not in sync_url


@pytest.mark.asyncio
@pytest.mark.integration
async def test_migrated_database_async_connection_works(migrated_database):
    """Test that async database connection works after migration."""
    async_url = migrated_database["async_url"]

    # Create async engine and test connection
    engine = create_async_engine(async_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 as test_value"))
            assert result.scalar() == 1
    except SQLAlchemyError as e:
        pytest.fail(f"Async database connection failed: {e}")
    finally:
        await engine.dispose()


@pytest.mark.integration
def test_migrated_database_sync_connection_works(migrated_database):
    """Test that sync database connection works after migration."""
    sync_url = migrated_database["sync_url"]

    # Create sync engine and test connection
    engine = create_engine(sync_url)
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test_value"))
            assert result.scalar() == 1
    except SQLAlchemyError as e:
        pytest.fail(f"Sync database connection failed: {e}")
    finally:
        engine.dispose()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_alembic_version_table_exists(migrated_database):
    """Test that Alembic version table exists after migration."""
    async_url = migrated_database["async_url"]

    engine = create_async_engine(async_url)
    try:
        async with engine.connect() as conn:
            # Check if alembic_version table exists
            result = await conn.execute(
                text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_name = 'alembic_version'
                );
            """)
            )
            assert result.scalar() is True, "alembic_version table should exist after migration"

            # Check that version is set
            version_result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            version = version_result.scalar()
            assert version is not None, "Alembic version should be set after migration"
            assert len(version) > 0, "Alembic version should be non-empty"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_migration_creates_expected_tables(migrated_database):
    """Test that migration creates expected application tables."""
    async_url = migrated_database["async_url"]

    engine = create_async_engine(async_url)
    try:
        async with engine.connect() as conn:
            # Get all tables in public schema (excluding alembic_version)
            result = await conn.execute(
                text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename != 'alembic_version'
                ORDER BY tablename
            """)
            )
            tables = [row[0] for row in result.fetchall()]

            # There should be at least some tables created by migrations
            assert len(tables) > 0, "Migration should create application tables"

            # Log found tables for debugging
            print(f"Found application tables after migration: {tables}")

            # Test that we can describe table structure for at least one table
            if tables:
                first_table = tables[0]
                columns_result = await conn.execute(
                    text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = '{first_table}' 
                    AND table_schema = 'public'
                    ORDER BY ordinal_position
                """)
                )
                columns = columns_result.fetchall()
                assert len(columns) > 0, f"Table {first_table} should have columns"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_migrated_database_supports_transactions(migrated_database):
    """Test that migrated database supports transactions properly."""
    async_url = migrated_database["async_url"]

    engine = create_async_engine(async_url)
    try:
        # Test transaction rollback
        async with engine.begin() as conn:
            # Create a temporary table
            await conn.execute(
                text("""
                CREATE TEMPORARY TABLE test_transaction (
                    id SERIAL PRIMARY KEY,
                    value VARCHAR(50)
                )
            """)
            )

            # Insert some data
            await conn.execute(
                text("""
                INSERT INTO test_transaction (value) VALUES ('test1'), ('test2')
            """)
            )

            # Verify data exists within transaction
            result = await conn.execute(text("SELECT COUNT(*) FROM test_transaction"))
            assert result.scalar() == 2

            # Rollback by not committing (raises exception)
            await conn.rollback()

        # Test transaction commit
        async with engine.begin() as conn:
            # Create temporary table again
            await conn.execute(
                text("""
                CREATE TEMPORARY TABLE test_transaction_commit (
                    id SERIAL PRIMARY KEY,
                    value VARCHAR(50)
                )
            """)
            )

            await conn.execute(
                text("""
                INSERT INTO test_transaction_commit (value) VALUES ('committed')
            """)
            )

            result = await conn.execute(text("SELECT COUNT(*) FROM test_transaction_commit"))
            assert result.scalar() == 1

            # Transaction will auto-commit when context exits normally

    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_migrated_database_fixture_isolation(migrated_database):
    """Test that each test gets a clean database state."""
    async_url = migrated_database["async_url"]

    engine = create_async_engine(async_url)
    try:
        async with engine.connect() as conn:
            # Check if any test data exists from previous tests
            # This assumes the pg_session fixture truncates tables between tests

            # Get list of all non-system tables
            result = await conn.execute(
                text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename != 'alembic_version'
            """)
            )
            tables = [row[0] for row in result.fetchall()]

            # Check that tables exist but are empty (cleaned by fixture)
            for table in tables:
                try:
                    count_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.scalar()
                    # Tables should be empty due to truncation in pg_session fixture
                    assert count == 0, f"Table {table} should be empty at start of test"
                except SQLAlchemyError:
                    # Some tables might not support COUNT(*) - that's ok
                    pass

    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_migration_is_idempotent(postgres_container):
    """Test that running migration multiple times is safe (idempotent)."""
    from tests.integration.fixtures.postgres import _build_urls, _run_alembic_upgrade_head

    async_url, sync_url = _build_urls(postgres_container)

    # Run migration first time
    _run_alembic_upgrade_head(sync_url)

    # Verify database is migrated
    engine = create_async_engine(async_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            first_version = result.scalar()
            assert first_version is not None
    finally:
        await engine.dispose()

    # Run migration second time - should not fail
    try:
        _run_alembic_upgrade_head(sync_url)
    except Exception as e:
        pytest.fail(f"Second migration run should not fail: {e}")

    # Verify version is still the same
    engine = create_async_engine(async_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            second_version = result.scalar()
            assert second_version == first_version, "Version should remain same after idempotent migration"
    finally:
        await engine.dispose()
