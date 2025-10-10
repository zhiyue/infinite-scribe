"""Unit tests for database compatibility layer."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from src import database


class TestDatabase:
    """Test cases for database compatibility layer functions."""

    @pytest.mark.asyncio
    @patch("src.database.engine")
    async def test_init_db(self, mock_engine):
        """Test database initialization."""
        # Arrange
        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin.return_value = mock_context_manager

        # Mock Base.metadata.create_all
        with patch("src.database.Base") as mock_base:
            mock_base.metadata.create_all = Mock()

            # Act
            await database.init_db()

            # Assert
            mock_engine.begin.assert_called_once()
            mock_conn.run_sync.assert_called_once_with(mock_base.metadata.create_all)

    @pytest.mark.asyncio
    @patch("src.database.engine")
    async def test_close_db(self, mock_engine):
        """Test database connection closing."""
        # Arrange
        mock_engine.dispose = AsyncMock()

        # Act
        await database.close_db()

        # Assert
        mock_engine.dispose.assert_called_once()

    def test_imports_and_exports(self):
        """Test that all required imports and exports are available."""
        # Test that all expected exports are available
        expected_exports = [
            "Base",
            "engine",
            "async_session_maker",
            "get_db",
            "init_db",
            "close_db",
        ]

        for export_name in expected_exports:
            assert hasattr(database, export_name), f"Missing export: {export_name}"
            assert export_name in database.__all__, f"Export {export_name} not in __all__"

    def test_all_exports_defined(self):
        """Test that __all__ contains exactly the expected exports."""
        expected_all = [
            "Base",
            "engine",
            "async_session_maker",
            "get_db",
            "init_db",
            "close_db",
        ]

        assert database.__all__ == expected_all

    @pytest.mark.asyncio
    async def test_get_db_import(self):
        """Test that get_db function is properly imported."""
        # This tests that the import works without issues
        assert callable(database.get_db)

        # Test that it's the same function as the one imported
        from src.db.sql.session import get_sql_session

        assert database.get_db == get_sql_session

    def test_imports_work(self):
        """Test that all imports from src.db.sql work correctly."""
        # Test Base import
        from src.db.sql import Base as OriginalBase

        assert database.Base == OriginalBase

        # Test engine import
        from src.db.sql import engine as original_engine

        assert database.engine == original_engine

        # Test async_session_maker import
        from src.db.sql import async_session_maker as original_session_maker

        assert database.async_session_maker == original_session_maker
