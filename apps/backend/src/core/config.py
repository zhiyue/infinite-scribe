"""统一的配置管理系统"""

import os

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseModel):
    """认证相关设置"""

    # JWT Settings
    jwt_secret_key: str = Field(
        default="test_jwt_secret_key_for_development_only_32_chars",
        description="Secret key for JWT signing (min 32 chars)",
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=15)
    refresh_token_expire_days: int = Field(default=7)

    # Email Service
    resend_api_key: str = Field(default="test_api_key")
    resend_domain: str = Field(default="test.example.com")
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

    # Development Settings
    use_maildev: bool = Field(default=False)
    maildev_host: str = Field(default="localhost")
    maildev_port: int = Field(default=1025)

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        """验证 JWT 密钥"""
        node_env = os.getenv("NODE_ENV", "development")
        if node_env not in ["test", "development"]:
            if not v or v == "test_jwt_secret_key_for_development_only_32_chars":
                raise ValueError("JWT_SECRET_KEY must be set to a secure value in production")
            if len(v) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("resend_api_key", "resend_domain")
    @classmethod
    def validate_resend_config(cls, v: str, info) -> str:
        """验证 Resend 配置"""
        node_env = os.getenv("NODE_ENV", "development")
        field_name = info.field_name

        if node_env not in ["test", "development"]:
            if field_name == "resend_api_key" and v == "test_api_key":
                raise ValueError("RESEND_API_KEY must be set to a valid value in production")
            elif field_name == "resend_domain" and v == "test.example.com":
                raise ValueError("RESEND_DOMAIN must be set to a valid domain in production")
        return v


class DatabaseSettings(BaseModel):
    """数据库相关设置"""

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
            # URL 编码密码以处理特殊字符
            from urllib.parse import quote

            encoded_password = quote(self.redis_password, safe="")
            return f"redis://:{encoded_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"


class Settings(BaseSettings):
    """应用主配置

    环境变量命名规则：
    - 顶层配置：直接使用变量名（如 NODE_ENV, API_PORT）
    - 嵌套配置：使用双下划线分隔（如 AUTH__JWT_SECRET_KEY, DATABASE__POSTGRES_HOST）

    配置文件位置：apps/backend/.env
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

    # 嵌套配置
    auth: AuthSettings = Field(default_factory=AuthSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    # 其他服务配置
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
        # 使用 backend 目录下的 .env 文件
        env_file="../../.env",  # 相对于 apps/backend/src/core/config.py
        env_file_encoding="utf-8",
        case_sensitive=False,  # 不区分大小写
        env_nested_delimiter="__",  # 支持嵌套环境变量
        extra="ignore",  # 忽略额外的环境变量
    )

    # 便捷的计算属性
    @property
    def kafka_bootstrap_servers(self) -> str:
        """计算 Kafka bootstrap servers"""
        return f"{self.kafka_host}:{self.kafka_port}"

    @property
    def embedding_api_url(self) -> str:
        """计算 Embedding API URL"""
        return f"http://{self.embedding_api_host}:{self.embedding_api_port}"

    @property
    def litellm_api_url(self) -> str:
        """计算 LiteLLM API URL"""
        if self.litellm_api_host:
            host = self.litellm_api_host.rstrip("/")
            return f"{host}/"
        return ""

    @property
    def is_dev(self) -> bool:
        """检查是否为开发环境"""
        return self.node_env == "development"


# 创建全局配置实例
settings = Settings()
