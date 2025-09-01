"""Unified configuration management system"""

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

# Import launcher configuration models
from ..launcher.config import LauncherConfigModel
from .toml_loader import load_toml_config


# Validation constants
class ValidationConstants:
    """Configuration validation constants"""

    JWT_MIN_LENGTH = 32
    DEFAULT_JWT_KEY = "test_jwt_secret_key_for_development_only_32_chars"
    DEFAULT_RESEND_API_KEY = "test_api_key"
    DEFAULT_RESEND_DOMAIN = "test.example.com"
    NON_PROD_ENVS = {"test", "development"}


def _is_production_env() -> bool:
    """Check if running in production environment"""
    return os.getenv("NODE_ENV", "development") not in ValidationConstants.NON_PROD_ENVS


def _validate_required_in_prod(value: str, default: str, field_name: str) -> str:
    """Validate that a field is not using default value in production"""
    if _is_production_env() and value == default:
        raise ValueError(f"{field_name} must be set to a valid value in production")
    return value


class TomlConfigSettingsSource(PydanticBaseSettingsSource):
    """Custom settings source that loads from TOML config with environment variable interpolation"""

    def __init__(self, settings_cls: type[BaseSettings], config_path: Path = Path("config.toml")):
        super().__init__(settings_cls)
        self.config_path = config_path

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        """Get field value from TOML config"""
        config = self._load_config()
        field_value = config.get(field_name)
        return field_value, field_name, field_value is not None

    def __call__(self) -> dict[str, Any]:
        """Return all settings from TOML file"""
        return self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load and parse TOML file with error handling"""
        if not self.config_path.exists():
            return {}

        try:
            return load_toml_config(self.config_path)
        except Exception as e:
            print(f"Failed to load TOML config: {e}")
            return {}


class AuthSettings(BaseModel):
    """Authentication related settings"""

    # JWT Settings
    jwt_secret_key: str = Field(
        default=ValidationConstants.DEFAULT_JWT_KEY,
        description="Secret key for JWT signing (min 32 chars)",
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=15)
    refresh_token_expire_days: int = Field(default=7)
    sse_token_expire_seconds: int = Field(default=60, description="SSE token expiration in seconds")

    # Email Service
    resend_api_key: str = Field(default=ValidationConstants.DEFAULT_RESEND_API_KEY)
    resend_domain: str = Field(default=ValidationConstants.DEFAULT_RESEND_DOMAIN)
    resend_from_email: str = Field(default="noreply@example.com")

    # Security Settings
    password_min_length: int = Field(default=8)
    account_lockout_attempts: int = Field(default=5)
    account_lockout_duration_minutes: int = Field(default=30)

    # Rate Limiting
    rate_limit_login_per_minute: int = Field(default=5)
    rate_limit_register_per_hour: int = Field(default=10)
    rate_limit_password_reset_per_hour: int = Field(default=3)

    # Email Verification
    email_verification_expire_hours: int = Field(default=24)
    password_reset_expire_hours: int = Field(default=1)

    # Session Management
    session_strategy: str = Field(default="multi_device")  # multi_device, single_device, max_sessions
    max_sessions_per_user: int = Field(default=10)  # Only used when strategy is max_sessions

    # Development Settings
    use_maildev: bool = Field(default=False)
    maildev_host: str = Field(default="localhost")
    maildev_port: int = Field(default=1025)

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        """Validate JWT secret key"""
        if _is_production_env():
            if not v or v == ValidationConstants.DEFAULT_JWT_KEY:
                raise ValueError("JWT_SECRET_KEY must be set to a secure value in production")
            if len(v) < ValidationConstants.JWT_MIN_LENGTH:
                raise ValueError(
                    f"JWT_SECRET_KEY must be at least {ValidationConstants.JWT_MIN_LENGTH} characters long"
                )
        return v

    @field_validator("resend_api_key")
    @classmethod
    def validate_resend_api_key(cls, v: str) -> str:
        """Validate Resend API key"""
        return _validate_required_in_prod(v, ValidationConstants.DEFAULT_RESEND_API_KEY, "RESEND_API_KEY")

    @field_validator("resend_domain")
    @classmethod
    def validate_resend_domain(cls, v: str) -> str:
        """Validate Resend domain"""
        return _validate_required_in_prod(v, ValidationConstants.DEFAULT_RESEND_DOMAIN, "RESEND_DOMAIN")


class DatabaseSettings(BaseModel):
    """Database configuration settings"""

    # PostgreSQL
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_db: str = Field(default="infinite_scribe")

    # Neo4j
    neo4j_host: str = Field(default="localhost")
    neo4j_port: int = Field(default=7687)
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="neo4j")
    neo4j_uri: str | None = Field(default="")

    # Redis
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")
    redis_sse_stream_maxlen: int = Field(
        default=1000, description="Maximum length for Redis SSE event streams (XADD maxlen parameter)"
    )

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def neo4j_url(self) -> str:
        """Get Neo4j connection URL"""
        return self.neo4j_uri if self.neo4j_uri else f"bolt://{self.neo4j_host}:{self.neo4j_port}"

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL with password handling"""
        if self.redis_password:
            from urllib.parse import quote

            encoded_password = quote(self.redis_password, safe="")
            return f"redis://:{encoded_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"


class Settings(BaseSettings):
    """应用主配置

    配置优先级（从高到低）：
    1. 环境变量
    2. .env 文件
    3. config.toml 文件（支持环境变量插值）
    4. 默认值

    环境变量命名规则：
    - 顶层配置：直接使用变量名（如 NODE_ENV, API_PORT）
    - 嵌套配置：使用双下划线分隔（如 AUTH__JWT_SECRET_KEY, DATABASE__POSTGRES_HOST, LAUNCHER__DEFAULT_MODE）

    配置文件位置：
    - TOML 配置：默认从运行目录读取 `config.toml`。在本项目中，后端服务以 `apps/backend` 为工作目录运行，
      因此建议将实际配置文件放置在 `apps/backend/config.toml`（不纳入版本控制）。
    - 模板文件：`apps/backend/config.toml.example`，可复制为 `config.toml` 并按需修改。
    - 环境变量：`apps/backend/.env`（开发环境）
    """

    # Service identification
    service_name: str = Field(default="infinite-scribe-backend")
    service_type: str = Field(default="api-gateway")
    node_env: str = Field(default="development")

    # API Settings
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    frontend_url: str = Field(default="http://localhost:3000")
    allowed_origins: list[str] = Field(default=["*"])

    # Nested configuration
    auth: AuthSettings = Field(default_factory=AuthSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    launcher: LauncherConfigModel = Field(default_factory=LauncherConfigModel, description="Launcher configuration")

    # External services
    milvus_host: str = Field(default="localhost")
    milvus_port: int = Field(default=19530)

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

    # LiteLLM Proxy
    litellm_api_host: str = Field(default="")
    litellm_api_key: str = Field(default="")

    # Embedding API
    embedding_api_host: str = Field(default="192.168.1.191")
    embedding_api_port: int = Field(default=11434)
    embedding_api_model: str = Field(default="dengcao/Qwen3-Embedding-0.6B:F16")

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Custom configuration source priority order"""
        toml_settings = TomlConfigSettingsSource(settings_cls)

        return (
            init_settings,
            env_settings,
            dotenv_settings,
            toml_settings,
            file_secret_settings,
        )

    # Computed properties
    @property
    def kafka_bootstrap_servers(self) -> str:
        """Get Kafka bootstrap servers"""
        return f"{self.kafka_host}:{self.kafka_port}"

    @property
    def embedding_api_url(self) -> str:
        """Get embedding API URL"""
        return f"http://{self.embedding_api_host}:{self.embedding_api_port}"

    @property
    def litellm_api_url(self) -> str:
        """Get LiteLLM API URL"""
        return f"{self.litellm_api_host.rstrip('/')}/" if self.litellm_api_host else ""

    @property
    def is_dev(self) -> bool:
        """Check if running in development environment"""
        return self.node_env == "development"


# Global configuration instance
settings = Settings()
