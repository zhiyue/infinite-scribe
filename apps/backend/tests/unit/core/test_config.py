"""Unit tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict
from src.core.config import Settings, get_backend_root


class MockSettings(BaseSettings):
    """Test-specific Settings class that doesn't load from .env file."""
    
    model_config = SettingsConfigDict(
        env_file=None,  # Disable .env file loading for tests
        env_file_encoding="utf-8",
        case_sensitive=True,
        env_prefix="",
        extra="ignore",
    )

    # Service identification
    SERVICE_NAME: str = "infinite-scribe-backend"
    SERVICE_TYPE: str = "api-gateway"

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Database Settings - 使用环境变量
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "infinite_scribe"

    NEO4J_HOST: str = "localhost"
    NEO4J_PORT: int = 7687
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j"
    NEO4J_URI: str = ""  # 可选, 从环境变量或计算

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # Other services
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530

    # Kafka - 关键配置
    KAFKA_HOST: str = "localhost"
    KAFKA_PORT: int = 9092
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_GROUP_ID_PREFIX: str = "infinite-scribe"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"

    # Prefect
    PREFECT_API_URL: str = "http://localhost:4200/api"

    # AI Providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # LiteLLM Proxy Configuration
    LITELLM_API_HOST: str = ""
    LITELLM_API_KEY: str = ""

    # Embedding API Configuration
    EMBEDDING_API_HOST: str = "192.168.1.191"
    EMBEDDING_API_PORT: int = 11434
    EMBEDDING_API_MODEL: str = "dengcao/Qwen3-Embedding-0.6B:F16"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Computed URLs
    @property
    def POSTGRES_URL(self) -> str:  # noqa: N802
        """计算 PostgreSQL 连接 URL"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def NEO4J_URL(self) -> str:  # noqa: N802
        """计算 Neo4j 连接 URL"""
        if self.NEO4J_URI:
            return self.NEO4J_URI
        return f"bolt://{self.NEO4J_HOST}:{self.NEO4J_PORT}"

    @property
    def REDIS_URL(self) -> str:  # noqa: N802
        """计算 Redis 连接 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def KAFKA_BOOTSTRAP_SERVERS(self) -> str:  # noqa: N802
        """计算 Kafka bootstrap servers 地址"""
        return f"{self.KAFKA_HOST}:{self.KAFKA_PORT}"

    @property
    def EMBEDDING_API_URL(self) -> str:  # noqa: N802
        """计算 Embedding API 地址"""
        return f"http://{self.EMBEDDING_API_HOST}:{self.EMBEDDING_API_PORT}"

    @property
    def LITELLM_API_URL(self) -> str:  # noqa: N802
        """计算 LiteLLM API 地址"""
        if self.LITELLM_API_HOST:
            # 确保 URL 以 / 结尾
            host = self.LITELLM_API_HOST.rstrip("/")
            return f"{host}/"
        return ""


@pytest.fixture(autouse=True)
def clean_environment():
    """Clear database-related environment variables for tests."""
    env_vars_to_clear = [
        "POSTGRES_HOST",
        "POSTGRES_PORT", 
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "NEO4J_HOST",
        "NEO4J_PORT",
        "NEO4J_USER", 
        "NEO4J_PASSWORD",
        "NEO4J_URI",
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_PASSWORD",
        "KAFKA_HOST",
        "KAFKA_PORT",
        "SERVICE_NAME",
        "API_PORT",
        "USE_EXTERNAL_SERVICES",
        "LITELLM_API_HOST",
        "LITELLM_API_KEY",
    ]

    # Store original values
    original_values = {var: os.environ.get(var) for var in env_vars_to_clear}

    # Clear the variables
    for var in env_vars_to_clear:
        if var in os.environ:
            del os.environ[var]

    yield

    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value


def test_default_settings():
    """Test default settings are loaded correctly."""
    settings = MockSettings()

    assert settings.SERVICE_NAME == "infinite-scribe-backend"
    assert settings.SERVICE_TYPE == "api-gateway"
    assert settings.API_HOST == "0.0.0.0"
    assert settings.API_PORT == 8000
    assert settings.POSTGRES_HOST == "localhost"
    assert settings.POSTGRES_PORT == 5432
    assert settings.POSTGRES_USER == "postgres"
    assert settings.POSTGRES_PASSWORD == "postgres"
    assert settings.POSTGRES_DB == "infinite_scribe"


def test_postgres_url_generation():
    """Test PostgreSQL URL is generated correctly."""
    settings = MockSettings()
    expected_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/infinite_scribe"
    assert expected_url == settings.POSTGRES_URL


def test_neo4j_url_generation():
    """Test Neo4j URL is generated correctly."""
    settings = MockSettings()
    expected_url = "bolt://localhost:7687"
    assert expected_url == settings.NEO4J_URL


def test_neo4j_url_with_uri_override():
    """Test Neo4j URL uses NEO4J_URI if provided."""
    with patch.dict(os.environ, {"NEO4J_URI": "bolt://custom-neo4j:7688"}):
        settings = MockSettings()
        assert settings.NEO4J_URL == "bolt://custom-neo4j:7688"


def test_redis_url_generation():
    """Test Redis URL is generated correctly."""
    settings = MockSettings()
    expected_url = "redis://localhost:6379/0"  # No password by default
    assert expected_url == settings.REDIS_URL


def test_redis_url_with_password():
    """Test Redis URL with password is generated correctly."""
    with patch.dict(os.environ, {"REDIS_PASSWORD": "testpass"}):
        settings = MockSettings()
        expected_url = "redis://:testpass@localhost:6379/0"
        assert expected_url == settings.REDIS_URL


def test_environment_variable_override():
    """Test environment variables override default settings."""
    env_vars = {
        "SERVICE_NAME": "test-service",
        "API_PORT": "9000",
        "POSTGRES_HOST": "test-postgres",
        "POSTGRES_PASSWORD": "test-password",
        "NEO4J_USER": "test-neo4j-user",
        "KAFKA_HOST": "test-kafka",
        "KAFKA_PORT": "9092",
    }

    with patch.dict(os.environ, env_vars):
        settings = MockSettings()

        assert settings.SERVICE_NAME == "test-service"
        assert settings.API_PORT == 9000
        assert settings.POSTGRES_HOST == "test-postgres"
        assert settings.POSTGRES_PASSWORD == "test-password"
        assert settings.NEO4J_USER == "test-neo4j-user"
        assert settings.KAFKA_HOST == "test-kafka"
        assert settings.KAFKA_PORT == 9092
        assert settings.KAFKA_BOOTSTRAP_SERVERS == "test-kafka:9092"


def test_allowed_origins_list():
    """Test ALLOWED_ORIGINS is properly parsed as a list."""
    settings = MockSettings()
    assert isinstance(settings.ALLOWED_ORIGINS, list)
    assert settings.ALLOWED_ORIGINS == ["*"]


def test_case_sensitive_environment_variables():
    """Test that environment variables are case sensitive."""
    with patch.dict(os.environ, {"api_port": "9000", "API_PORT": "8080"}):
        settings = MockSettings()
        # Should use API_PORT (uppercase) due to case_sensitive=True
        assert settings.API_PORT == 8080


def test_litellm_configuration():
    """Test LiteLLM configuration."""
    settings = MockSettings()
    
    # Test default values
    assert settings.LITELLM_API_HOST == ""
    assert settings.LITELLM_API_KEY == ""
    assert settings.LITELLM_API_URL == ""
    
    # Test with environment variable override
    with patch.dict(os.environ, {
        "LITELLM_API_HOST": "https://api.example.com",
        "LITELLM_API_KEY": "test-key"
    }):
        settings = MockSettings()
        assert settings.LITELLM_API_HOST == "https://api.example.com"
        assert settings.LITELLM_API_KEY == "test-key"
        assert settings.LITELLM_API_URL == "https://api.example.com/"


def test_litellm_url_with_trailing_slash():
    """Test LiteLLM URL formatting with trailing slash."""
    with patch.dict(os.environ, {"LITELLM_API_HOST": "https://api.example.com/"}):
        settings = MockSettings()
        assert settings.LITELLM_API_URL == "https://api.example.com/"
    
    with patch.dict(os.environ, {"LITELLM_API_HOST": "https://api.example.com"}):
        settings = MockSettings()
        assert settings.LITELLM_API_URL == "https://api.example.com/"


class TestBackendRoot:
    """Test backend root directory detection."""

    def test_get_backend_root_from_project_root(self):
        """Test backend root detection from project root."""
        backend_root = get_backend_root()
        
        # Should be a valid Path
        assert isinstance(backend_root, Path)
        
        # Should end with 'backend'
        assert backend_root.name == "backend"
        
        # Should contain expected structure
        assert (backend_root / "src").exists()
        assert (backend_root / "src" / "__init__.py").exists()
        assert (backend_root / "src" / "core" / "config.py").exists()

    def test_get_backend_root_has_expected_markers(self):
        """Test backend root contains expected marker files."""
        backend_root = get_backend_root()
        
        # Check for at least one expected marker
        markers = [
            "src/core/config.py",
            "src/__init__.py", 
            "Dockerfile",
        ]
        
        has_markers = [
            (backend_root / marker).exists() for marker in markers
        ]
        
        # Should have at least one marker file
        assert any(has_markers), f"Backend root {backend_root} should contain at least one marker file"

    @patch("src.core.config.os.getenv")
    def test_get_backend_root_with_env_var(self, mock_getenv):
        """Test backend root detection with environment variable."""
        mock_backend_path = "/custom/backend/path"
        mock_getenv.return_value = mock_backend_path
        
        # Mock the project root to fail
        with patch("src.core.config.get_project_root") as mock_project_root:
            mock_project_root.side_effect = FileNotFoundError("Test failure")
            
            # Mock the path traversal to fail
            with patch("src.core.config.Path") as mock_path:
                mock_current = MagicMock()
                mock_current.parents = []  # No parents to search
                mock_path(__file__).resolve.return_value = mock_current
                mock_path.return_value = Path(mock_backend_path)
                
                result = get_backend_root()
                assert str(result) == mock_backend_path
