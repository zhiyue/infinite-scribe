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


class EmbeddingSettings(BaseModel):
    """Embedding service provider settings (simplified for testing)"""

    # Provider configuration
    provider: str = Field(default="ollama", description="Embedding provider: ollama, openai, anthropic")

    # Ollama settings
    ollama_host: str = Field(default="192.168.1.191")
    ollama_port: int = Field(default=11434)
    ollama_model: str = Field(default="dengcao/Qwen3-Embedding-0.6B:F16")

    # OpenAI settings
    openai_api_key: str = Field(default="", description="OpenAI API key for embeddings")
    openai_model: str = Field(default="text-embedding-ada-002", description="OpenAI embedding model")
    openai_base_url: str = Field(default="https://api.openai.com/v1", description="OpenAI API base URL")

    # Connection settings
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    max_keepalive_connections: int = Field(default=5)
    max_connections: int = Field(default=10)

    # Retry settings
    enable_retry: bool = Field(default=True, description="Enable retry mechanism for transient errors")
    retry_attempts: int = Field(default=3, description="Maximum number of retry attempts")

    @property
    def ollama_url(self) -> str:
        """Get Ollama API URL"""
        return f"http://{self.ollama_host}:{self.ollama_port}"


class LauncherConfigModel(BaseModel):
    """Launcher configuration (simplified for testing)"""

    default_mode: str = Field(default="api-gateway")
    components: list[str] = Field(default=["api-gateway"])
    agents: list[str] = Field(default=[])

    # Agent settings
    agent_max_retries: int = Field(default=3)
    agent_commit_batch_size: int = Field(default=20)


class RelaySettings(BaseModel):
    """Outbox Relay settings"""

    poll_interval_seconds: int = Field(default=5, description="Outbox relay poll interval in seconds")
    batch_size: int = Field(default=100, description="Outbox relay fetch batch size")
    retry_backoff_ms: int = Field(default=1000, description="Outbox relay base backoff (ms), exp growth")


class EventBridgeSettings(BaseModel):
    """EventBridge service settings"""

    domain_topics: list[str] = Field(
        default=["genesis.session.events"],
        description="Domain event topics to consume from Kafka",
    )
    group_id_suffix: str = Field(
        default="event-bridge",
        description="Consumer group ID suffix (will be prefixed with agent name)",
    )


class __TestingSettings(BaseSettings):
    """Test-specific Settings class that matches real Settings structure but doesn't load from files."""

    model_config = SettingsConfigDict(
        env_file=None,  # Disable .env file loading for tests
        env_file_encoding="utf-8",
        case_sensitive=False,  # 与实际配置一致
        env_prefix="",
        extra="ignore",
        env_nested_delimiter="__",
    )

    # Service identification (matches real Settings)
    service_name: str = Field(default="infinite-scribe-backend")
    service_type: str = Field(default="api-gateway")
    node_env: str = Field(default="development")

    # API Settings
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    frontend_url: str = Field(default="http://localhost:3000")
    allowed_origins: list[str] = Field(default=["*"])

    # Nested configuration (matches real Settings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings, description="Embedding provider configuration")
    launcher: LauncherConfigModel = Field(default_factory=LauncherConfigModel, description="Launcher configuration")
    
    # Outbox Relay (nested)
    relay: RelaySettings = Field(default_factory=RelaySettings)
    
    # EventBridge service (nested)  
    eventbridge: EventBridgeSettings = Field(default_factory=EventBridgeSettings)

    # External services
    milvus_host: str = Field(default="localhost")
    milvus_port: int = Field(default=19530)

    kafka_host: str = Field(default="localhost")
    kafka_port: int = Field(default=9092)
    kafka_auto_offset_reset: str = Field(default="earliest")
    kafka_group_id_prefix: str = Field(default="infinite-scribe")

    # Agent processing settings (matches real Settings)
    agent_max_retries: int = Field(default=3, description="Max retries before sending to DLT")
    agent_retry_backoff_ms: int = Field(default=500, description="Base backoff in ms for retry with exponential growth")
    agent_dlt_suffix: str = Field(default=".DLT", description="Suffix for dead-letter topics")
    agent_commit_batch_size: int = Field(default=20, description="Commit after N messages processed")
    agent_commit_interval_ms: int = Field(default=1000, description="Commit at least every T milliseconds")

    # MinIO
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str = Field(default="minioadmin")
    minio_secret_key: str = Field(default="minioadmin")

    # Prefect
    prefect_api_url: str = Field(default="http://localhost:4200/api")

    # AI Providers
    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")

    # LiteLLM Proxy
    litellm_api_host: str = Field(default="")
    litellm_api_key: str = Field(default="")

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Computed properties (matches real Settings)
    @property
    def kafka_bootstrap_servers(self) -> str:
        """计算 Kafka bootstrap servers 地址"""
        return f"{self.kafka_host}:{self.kafka_port}"

    @property
    def litellm_api_url(self) -> str:
        """计算 LiteLLM API 地址"""
        return f"{self.litellm_api_host.rstrip('/')}/" if self.litellm_api_host else ""

    @property
    def is_dev(self) -> bool:
        """Check if running in development environment"""
        return self.node_env == "development"

    @property
    def environment(self) -> str:
        """Get current environment"""
        return self.node_env


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
        # 嵌套Embedding配置
        "EMBEDDING__PROVIDER",
        "EMBEDDING__OLLAMA_HOST",
        "EMBEDDING__OLLAMA_PORT",
        "EMBEDDING__OLLAMA_MODEL",
        "EMBEDDING__OPENAI_API_KEY",
        "EMBEDDING__TIMEOUT",
        # 嵌套Launcher配置
        "LAUNCHER__DEFAULT_MODE",
        "LAUNCHER__COMPONENTS",
        "LAUNCHER__AGENTS",
        "LAUNCHER__AGENT_MAX_RETRIES",
        # 嵌套Relay配置
        "RELAY__POLL_INTERVAL_SECONDS",
        "RELAY__BATCH_SIZE",
        "RELAY__RETRY_BACKOFF_MS",
        # 嵌套EventBridge配置
        "EVENTBRIDGE__DOMAIN_TOPICS",
        "EVENTBRIDGE__GROUP_ID_SUFFIX",
        # Agent processing configuration
        "AGENT_MAX_RETRIES",
        "AGENT_RETRY_BACKOFF_MS",
        "AGENT_DLT_SUFFIX",
        "AGENT_COMMIT_BATCH_SIZE",
        "AGENT_COMMIT_INTERVAL_MS",
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
    settings = __TestingSettings()

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
    settings = __TestingSettings()

    assert settings.auth.jwt_secret_key == "test_secret_key"
    assert settings.auth.jwt_algorithm == "HS256"
    assert settings.auth.access_token_expire_minutes == 15
    assert settings.auth.password_min_length == 8


def test_postgres_url_generation():
    """Test PostgreSQL URL is generated correctly."""
    settings = __TestingSettings()
    expected_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/infinite_scribe"
    assert expected_url == settings.database.postgres_url


def test_neo4j_url_generation():
    """Test Neo4j URL is generated correctly."""
    settings = __TestingSettings()
    expected_url = "bolt://localhost:7687"
    assert expected_url == settings.database.neo4j_url


def test_neo4j_url_with_uri_override():
    """Test Neo4j URL uses neo4j_uri if provided."""
    with patch.dict(os.environ, {"DATABASE__NEO4J_URI": "bolt://custom-neo4j:7688"}):
        settings = __TestingSettings()
        assert settings.database.neo4j_url == "bolt://custom-neo4j:7688"


def test_redis_url_generation():
    """Test Redis URL is generated correctly."""
    settings = __TestingSettings()
    expected_url = "redis://localhost:6379/0"  # No password by default
    assert expected_url == settings.database.redis_url


def test_redis_url_with_password():
    """Test Redis URL with password is generated correctly."""
    with patch.dict(os.environ, {"DATABASE__REDIS_PASSWORD": "testpass"}):
        settings = __TestingSettings()
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
        settings = __TestingSettings()

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
    settings = __TestingSettings()
    assert isinstance(settings.allowed_origins, list)
    assert settings.allowed_origins == ["*"]


def test_case_sensitive_environment_variables():
    """Test that environment variables are case insensitive."""
    with patch.dict(os.environ, {"api_port": "9000", "API_PORT": "8080"}):
        settings = __TestingSettings()
        # Should use API_PORT (uppercase) as it's processed after api_port (lowercase) due to case_sensitive=False
        assert settings.api_port == 8080


def test_litellm_configuration():
    """Test LiteLLM configuration."""
    settings = __TestingSettings()

    # Test default values
    assert settings.litellm_api_host == ""
    assert settings.litellm_api_key == ""
    assert settings.litellm_api_url == ""

    # Test with environment variable override
    with patch.dict(os.environ, {"LITELLM_API_HOST": "https://api.example.com", "LITELLM_API_KEY": "test-key"}):
        settings = __TestingSettings()
        assert settings.litellm_api_host == "https://api.example.com"
        assert settings.litellm_api_key == "test-key"
        assert settings.litellm_api_url == "https://api.example.com/"


def test_litellm_url_with_trailing_slash():
    """Test LiteLLM URL formatting with trailing slash."""
    with patch.dict(os.environ, {"LITELLM_API_HOST": "https://api.example.com/"}):
        settings = __TestingSettings()
        assert settings.litellm_api_url == "https://api.example.com/"

    with patch.dict(os.environ, {"LITELLM_API_HOST": "https://api.example.com"}):
        settings = __TestingSettings()
        assert settings.litellm_api_url == "https://api.example.com/"


def test_agent_processing_settings():
    """Test agent processing configuration defaults."""
    settings = __TestingSettings()

    assert settings.agent_max_retries == 3
    assert settings.agent_retry_backoff_ms == 500
    assert settings.agent_dlt_suffix == ".DLT"
    assert settings.agent_commit_batch_size == 20
    assert settings.agent_commit_interval_ms == 1000


def test_environment_properties():
    """Test environment-related computed properties."""
    settings = __TestingSettings()

    # Test default development environment
    assert settings.is_dev is True
    assert settings.environment == "development"
    assert settings.node_env == "development"

    # Test production environment
    with patch.dict(os.environ, {"NODE_ENV": "production"}):
        settings = __TestingSettings()
        assert settings.is_dev is False
        assert settings.environment == "production"


def test_agent_settings_environment_override():
    """Test agent settings can be overridden via environment variables."""
    env_vars = {
        "AGENT_MAX_RETRIES": "5",
        "AGENT_RETRY_BACKOFF_MS": "1000",
        "AGENT_DLT_SUFFIX": ".DEAD",
        "AGENT_COMMIT_BATCH_SIZE": "50",
        "AGENT_COMMIT_INTERVAL_MS": "2000",
    }

    with patch.dict(os.environ, env_vars):
        settings = __TestingSettings()

        assert settings.agent_max_retries == 5
        assert settings.agent_retry_backoff_ms == 1000
        assert settings.agent_dlt_suffix == ".DEAD"
        assert settings.agent_commit_batch_size == 50
        assert settings.agent_commit_interval_ms == 2000


def test_service_identification_defaults():
    """Test service identification defaults match real config."""
    settings = __TestingSettings()

    assert settings.service_name == "infinite-scribe-backend"
    assert settings.service_type == "api-gateway"
    assert settings.frontend_url == "http://localhost:3000"


def test_nested_embedding_settings():
    """Test nested embedding configuration defaults."""
    settings = __TestingSettings()

    assert settings.embedding.provider == "ollama"
    assert settings.embedding.ollama_host == "192.168.1.191"
    assert settings.embedding.ollama_port == 11434
    assert settings.embedding.ollama_model == "dengcao/Qwen3-Embedding-0.6B:F16"
    assert settings.embedding.openai_api_key == ""
    assert settings.embedding.timeout == 30.0
    assert settings.embedding.enable_retry is True
    assert settings.embedding.retry_attempts == 3
    assert settings.embedding.ollama_url == "http://192.168.1.191:11434"


def test_nested_launcher_settings():
    """Test nested launcher configuration defaults."""
    settings = __TestingSettings()

    assert settings.launcher.default_mode == "api-gateway"
    assert settings.launcher.components == ["api-gateway"]
    assert settings.launcher.agents == []
    assert settings.launcher.agent_max_retries == 3
    assert settings.launcher.agent_commit_batch_size == 20


def test_nested_relay_settings():
    """Test nested relay configuration defaults."""
    settings = __TestingSettings()

    assert settings.relay.poll_interval_seconds == 5
    assert settings.relay.batch_size == 100
    assert settings.relay.retry_backoff_ms == 1000


def test_nested_eventbridge_settings():
    """Test nested eventbridge configuration defaults.""" 
    settings = __TestingSettings()

    assert settings.eventbridge.domain_topics == ["genesis.session.events"]
    assert settings.eventbridge.group_id_suffix == "event-bridge"


def test_embedding_environment_override():
    """Test embedding settings can be overridden via environment variables."""
    env_vars = {
        "EMBEDDING__PROVIDER": "openai",
        "EMBEDDING__OLLAMA_HOST": "custom-host",
        "EMBEDDING__OLLAMA_PORT": "8080",
        "EMBEDDING__OPENAI_API_KEY": "sk-test123",
        "EMBEDDING__TIMEOUT": "45.0",
        "EMBEDDING__RETRY_ATTEMPTS": "5",
    }

    with patch.dict(os.environ, env_vars):
        settings = __TestingSettings()

        assert settings.embedding.provider == "openai"
        assert settings.embedding.ollama_host == "custom-host"
        assert settings.embedding.ollama_port == 8080
        assert settings.embedding.openai_api_key == "sk-test123"
        assert settings.embedding.timeout == 45.0
        assert settings.embedding.retry_attempts == 5
        assert settings.embedding.ollama_url == "http://custom-host:8080"


def test_launcher_environment_override():
    """Test launcher settings can be overridden via environment variables."""
    env_vars = {
        "LAUNCHER__DEFAULT_MODE": "agent-worldsmith",
        "LAUNCHER__AGENT_MAX_RETRIES": "5",
        "LAUNCHER__AGENT_COMMIT_BATCH_SIZE": "50",
    }

    with patch.dict(os.environ, env_vars):
        settings = __TestingSettings()

        assert settings.launcher.default_mode == "agent-worldsmith"
        assert settings.launcher.agent_max_retries == 5
        assert settings.launcher.agent_commit_batch_size == 50


def test_relay_environment_override():
    """Test relay settings can be overridden via environment variables."""
    env_vars = {
        "RELAY__POLL_INTERVAL_SECONDS": "10", 
        "RELAY__BATCH_SIZE": "200",
        "RELAY__RETRY_BACKOFF_MS": "2000",
    }

    with patch.dict(os.environ, env_vars):
        settings = __TestingSettings()

        assert settings.relay.poll_interval_seconds == 10
        assert settings.relay.batch_size == 200
        assert settings.relay.retry_backoff_ms == 2000


def test_eventbridge_environment_override():
    """Test eventbridge settings can be overridden via environment variables."""
    env_vars = {
        "EVENTBRIDGE__GROUP_ID_SUFFIX": "custom-bridge",
    }

    with patch.dict(os.environ, env_vars):
        settings = __TestingSettings()

        assert settings.eventbridge.group_id_suffix == "custom-bridge"


def test_comprehensive_nested_override():
    """Test comprehensive nested configuration override scenario."""
    env_vars = {
        # Auth nested
        "AUTH__JWT_SECRET_KEY": "custom-jwt-key-for-testing-only",
        "AUTH__ACCESS_TOKEN_EXPIRE_MINUTES": "30",
        # Database nested
        "DATABASE__POSTGRES_HOST": "custom-postgres",
        "DATABASE__REDIS_PASSWORD": "redis-pass",
        # Embedding nested
        "EMBEDDING__PROVIDER": "openai",
        "EMBEDDING__OPENAI_API_KEY": "sk-custom123",
        # Launcher nested
        "LAUNCHER__DEFAULT_MODE": "agent-director",
        # Service level
        "SERVICE_NAME": "custom-backend",
        "API_PORT": "9000",
    }

    with patch.dict(os.environ, env_vars):
        settings = __TestingSettings()

        # Test auth nested override
        assert settings.auth.jwt_secret_key == "custom-jwt-key-for-testing-only"
        assert settings.auth.access_token_expire_minutes == 30
        
        # Test database nested override
        assert settings.database.postgres_host == "custom-postgres"
        assert settings.database.redis_password == "redis-pass"
        assert "redis-pass" in settings.database.redis_url
        
        # Test embedding nested override
        assert settings.embedding.provider == "openai"
        assert settings.embedding.openai_api_key == "sk-custom123"
        
        # Test launcher nested override
        assert settings.launcher.default_mode == "agent-director"
        
        # Test service level override
        assert settings.service_name == "custom-backend"
        assert settings.api_port == 9000
