"""Unit tests for configuration management."""

import os
from unittest.mock import patch

import pytest
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# from src.core.config import get_backend_root  # 已删除


class AuthSettings(BaseModel):
    """认证相关配置"""

    jwt_secret_key: str = Field(default="test_secret_key")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=15)
    refresh_token_expire_days: int = Field(default=7)
    resend_api_key: str = Field(default="")
    resend_domain: str = Field(default="")
    resend_from_email: str = Field(default="noreply@example.com")
    password_min_length: int = Field(default=8)
    account_lockout_attempts: int = Field(default=5)
    account_lockout_duration_minutes: int = Field(default=30)
    rate_limit_login_per_minute: int = Field(default=5)
    rate_limit_register_per_hour: int = Field(default=10)
    rate_limit_password_reset_per_hour: int = Field(default=3)
    email_verification_expire_hours: int = Field(default=24)
    password_reset_expire_hours: int = Field(default=1)
    use_maildev: bool = Field(default=False)
    maildev_host: str = Field(default="localhost")
    maildev_port: int = Field(default=1025)


class DatabaseSettings(BaseModel):
    """数据库相关配置"""

    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_db: str = Field(default="infinite_scribe")
    neo4j_host: str = Field(default="localhost")
    neo4j_port: int = Field(default=7687)
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="neo4j")
    neo4j_uri: str = Field(default="")
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")

    @property
    def postgres_url(self) -> str:
        """计算 PostgreSQL 连接 URL"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def neo4j_url(self) -> str:
        """计算 Neo4j 连接 URL"""
        if self.neo4j_uri:
            return self.neo4j_uri
        return f"bolt://{self.neo4j_host}:{self.neo4j_port}"

    @property
    def redis_url(self) -> str:
        """计算 Redis 连接 URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"


class MockSettings(BaseSettings):
    """Test-specific Settings class that doesn't load from .env file."""

    model_config = SettingsConfigDict(
        env_file=None,  # Disable .env file loading for tests
        env_file_encoding="utf-8",
        case_sensitive=False,  # 改为 False，与实际配置一致
        env_prefix="",
        extra="ignore",
        env_nested_delimiter="__",
    )

    # 嵌套配置
    auth: AuthSettings = Field(default_factory=AuthSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    # Service identification
    service_name: str = Field(default="infinite-scribe-backend")
    service_type: str = Field(default="api-gateway")
    node_env: str = Field(default="development")

    # API Settings
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    frontend_url: str = Field(default="http://localhost:3000")

    # CORS
    allowed_origins: list[str] = Field(default=["*"])

    # Other services
    milvus_host: str = Field(default="localhost")
    milvus_port: int = Field(default=19530)

    # Kafka
    kafka_host: str = Field(default="localhost")
    kafka_port: int = Field(default=9092)
    kafka_auto_offset_reset: str = Field(default="earliest")
    kafka_group_id_prefix: str = Field(default="infinite-scribe")

    # MinIO
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str = Field(default="minioadmin")
    minio_secret_key: str = Field(default="minioadmin")

    # Prefect
    prefect_api_url: str = Field(default="http://localhost:4200/api")

    # AI Providers
    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")

    # LiteLLM Proxy Configuration
    litellm_api_host: str = Field(default="")
    litellm_api_key: str = Field(default="")

    # Embedding API Configuration
    embedding_api_host: str = Field(default="192.168.1.191")
    embedding_api_port: int = Field(default=11434)
    embedding_api_model: str = Field(default="dengcao/Qwen3-Embedding-0.6B:F16")

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    @property
    def kafka_bootstrap_servers(self) -> str:
        """计算 Kafka bootstrap servers 地址"""
        return f"{self.kafka_host}:{self.kafka_port}"

    @property
    def embedding_api_url(self) -> str:
        """计算 Embedding API 地址"""
        return f"http://{self.embedding_api_host}:{self.embedding_api_port}"

    @property
    def litellm_api_url(self) -> str:
        """计算 LiteLLM API 地址"""
        if self.litellm_api_host:
            host = self.litellm_api_host.rstrip("/")
            return f"{host}/"
        return ""


@pytest.fixture(autouse=True)
def clean_environment():
    """Clear database-related environment variables for tests."""
    env_vars_to_clear = [
        # 嵌套认证配置
        "AUTH__JWT_SECRET_KEY",
        "AUTH__JWT_ALGORITHM",
        "AUTH__ACCESS_TOKEN_EXPIRE_MINUTES",
        "AUTH__RESEND_API_KEY",
        # 嵌套数据库配置
        "DATABASE__POSTGRES_HOST",
        "DATABASE__POSTGRES_PORT",
        "DATABASE__POSTGRES_USER",
        "DATABASE__POSTGRES_PASSWORD",
        "DATABASE__POSTGRES_DB",
        "DATABASE__NEO4J_HOST",
        "DATABASE__NEO4J_PORT",
        "DATABASE__NEO4J_USER",
        "DATABASE__NEO4J_PASSWORD",
        "DATABASE__NEO4J_URI",
        "DATABASE__REDIS_HOST",
        "DATABASE__REDIS_PORT",
        "DATABASE__REDIS_PASSWORD",
        # 其他配置
        "KAFKA_HOST",
        "KAFKA_PORT",
        "SERVICE_NAME",
        "API_PORT",
        "NODE_ENV",
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

    assert settings.service_name == "infinite-scribe-backend"
    assert settings.service_type == "api-gateway"
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.database.postgres_host == "localhost"
    assert settings.database.postgres_port == 5432
    assert settings.database.postgres_user == "postgres"
    assert settings.database.postgres_password == "postgres"
    assert settings.database.postgres_db == "infinite_scribe"


def test_nested_auth_settings():
    """Test nested authentication settings."""
    settings = MockSettings()

    assert settings.auth.jwt_secret_key == "test_secret_key"
    assert settings.auth.jwt_algorithm == "HS256"
    assert settings.auth.access_token_expire_minutes == 15
    assert settings.auth.password_min_length == 8


def test_postgres_url_generation():
    """Test PostgreSQL URL is generated correctly."""
    settings = MockSettings()
    expected_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/infinite_scribe"
    assert expected_url == settings.database.postgres_url


def test_neo4j_url_generation():
    """Test Neo4j URL is generated correctly."""
    settings = MockSettings()
    expected_url = "bolt://localhost:7687"
    assert expected_url == settings.database.neo4j_url


def test_neo4j_url_with_uri_override():
    """Test Neo4j URL uses neo4j_uri if provided."""
    with patch.dict(os.environ, {"DATABASE__NEO4J_URI": "bolt://custom-neo4j:7688"}):
        settings = MockSettings()
        assert settings.database.neo4j_url == "bolt://custom-neo4j:7688"


def test_redis_url_generation():
    """Test Redis URL is generated correctly."""
    settings = MockSettings()
    expected_url = "redis://localhost:6379/0"  # No password by default
    assert expected_url == settings.database.redis_url


def test_redis_url_with_password():
    """Test Redis URL with password is generated correctly."""
    with patch.dict(os.environ, {"DATABASE__REDIS_PASSWORD": "testpass"}):
        settings = MockSettings()
        expected_url = "redis://:testpass@localhost:6379/0"
        assert expected_url == settings.database.redis_url


def test_nested_environment_variable_override():
    """Test nested environment variables override default settings."""
    env_vars = {
        "SERVICE_NAME": "test-service",
        "API_PORT": "9000",
        "DATABASE__POSTGRES_HOST": "test-postgres",
        "DATABASE__POSTGRES_PASSWORD": "test-password",
        "DATABASE__NEO4J_USER": "test-neo4j-user",
        "AUTH__JWT_SECRET_KEY": "test-jwt-key",
        "AUTH__ACCESS_TOKEN_EXPIRE_MINUTES": "30",
        "KAFKA_HOST": "test-kafka",
        "KAFKA_PORT": "9092",
    }

    with patch.dict(os.environ, env_vars):
        settings = MockSettings()

        assert settings.service_name == "test-service"
        assert settings.api_port == 9000
        assert settings.database.postgres_host == "test-postgres"
        assert settings.database.postgres_password == "test-password"
        assert settings.database.neo4j_user == "test-neo4j-user"
        assert settings.auth.jwt_secret_key == "test-jwt-key"
        assert settings.auth.access_token_expire_minutes == 30
        assert settings.kafka_host == "test-kafka"
        assert settings.kafka_port == 9092
        assert settings.kafka_bootstrap_servers == "test-kafka:9092"


def test_allowed_origins_list():
    """Test allowed_origins is properly parsed as a list."""
    settings = MockSettings()
    assert isinstance(settings.allowed_origins, list)
    assert settings.allowed_origins == ["*"]


def test_case_sensitive_environment_variables():
    """Test that environment variables are case sensitive."""
    with patch.dict(os.environ, {"api_port": "9000", "API_PORT": "8080"}):
        settings = MockSettings()
        # Should use API_PORT (uppercase) due to case_sensitive=True
        assert settings.api_port == 8080


def test_litellm_configuration():
    """Test LiteLLM configuration."""
    settings = MockSettings()

    # Test default values
    assert settings.litellm_api_host == ""
    assert settings.litellm_api_key == ""
    assert settings.litellm_api_url == ""

    # Test with environment variable override
    with patch.dict(os.environ, {"LITELLM_API_HOST": "https://api.example.com", "LITELLM_API_KEY": "test-key"}):
        settings = MockSettings()
        assert settings.litellm_api_host == "https://api.example.com"
        assert settings.litellm_api_key == "test-key"
        assert settings.litellm_api_url == "https://api.example.com/"


def test_litellm_url_with_trailing_slash():
    """Test LiteLLM URL formatting with trailing slash."""
    with patch.dict(os.environ, {"LITELLM_API_HOST": "https://api.example.com/"}):
        settings = MockSettings()
        assert settings.litellm_api_url == "https://api.example.com/"

    with patch.dict(os.environ, {"LITELLM_API_HOST": "https://api.example.com"}):
        settings = MockSettings()
        assert settings.litellm_api_url == "https://api.example.com/"
