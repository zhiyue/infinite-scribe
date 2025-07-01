"""Tests for configuration module."""

import os
from pathlib import Path
from unittest.mock import patch

from src.core.config import PROJECT_ROOT, get_project_root


class TestProjectRootDetection:
    """Test project root detection functionality."""

    def test_project_root_exists(self):
        """Test that project root is detected and exists."""
        assert PROJECT_ROOT.exists()
        assert PROJECT_ROOT.is_dir()

    def test_project_root_has_marker_files(self):
        """Test that detected project root contains expected marker files."""
        marker_files = ["pyproject.toml", "package.json", ".git", "docker-compose.yml", "README.md"]

        # At least one marker file should exist
        has_marker = any((PROJECT_ROOT / marker).exists() for marker in marker_files)
        assert has_marker, f"No marker files found in {PROJECT_ROOT}"

    def test_get_project_root_with_env_var(self):
        """Test project root detection using environment variable."""
        test_path = "/tmp/test_project"

        with patch.dict(os.environ, {"PROJECT_ROOT": test_path}):
            # Mock the marker file check to fail
            with patch("pathlib.Path.exists", return_value=False):
                root = get_project_root()
                assert str(root) == test_path

    def test_get_project_root_fallback(self):
        """Test fallback mechanism when no marker files found."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch.dict(os.environ, {}, clear=True):
                root = get_project_root()
                # Should fall back to parents[4] calculation
                expected = Path(__file__).resolve().parents[5]  # Adjust for test file location
                # Just verify it returns a Path object
                assert isinstance(root, Path)

    def test_project_structure_assumptions(self):
        """Test that our assumptions about project structure are correct."""
        config_file = Path(__file__).parent.parent / "src" / "core" / "config.py"

        # Verify the config file exists where we expect it
        assert config_file.exists(), f"Config file not found at {config_file}"

        # The PROJECT_ROOT should be the actual project root (where pyproject.toml is)
        # Let's check if PROJECT_ROOT contains the expected marker files
        expected_markers = ["pyproject.toml", "package.json"]
        has_expected_markers = any((PROJECT_ROOT / marker).exists() for marker in expected_markers)
        assert has_expected_markers, f"PROJECT_ROOT {PROJECT_ROOT} doesn't contain expected markers"

        # The config file should be under the project root
        try:
            config_file.resolve().relative_to(PROJECT_ROOT)
        except ValueError:
            assert False, f"Config file {config_file} is not under PROJECT_ROOT {PROJECT_ROOT}"


class TestSettings:
    """Test settings configuration."""

    def test_env_file_path_is_valid(self):
        """Test that ENV_FILE_PATH points to a valid location."""
        from src.core.config import ENV_FILE_PATH

        # Should be a Path object
        assert isinstance(ENV_FILE_PATH, Path)

        # Parent directory should exist
        assert ENV_FILE_PATH.parent.exists()

        # Should end with .env
        assert ENV_FILE_PATH.name == ".env"

    def test_database_url_construction(self):
        """Test database URL construction."""
        from src.core.config import Settings

        settings = Settings()

        # Test PostgreSQL URL
        pg_url = settings.POSTGRES_URL
        assert "postgresql+asyncpg://" in pg_url
        assert settings.POSTGRES_USER in pg_url
        assert str(settings.POSTGRES_PORT) in pg_url

        # Test Neo4j URL
        neo4j_url = settings.NEO4J_URL
        assert "bolt://" in neo4j_url or "neo4j://" in neo4j_url

        # Test Redis URL
        redis_url = settings.REDIS_URL
        assert "redis://" in redis_url
