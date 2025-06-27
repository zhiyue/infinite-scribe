"""Configuration management for backend services."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Base settings for all backend services."""

    # Service identification
    SERVICE_NAME: str = "infinite-scribe-backend"
    SERVICE_TYPE: str = "api-gateway"  # or agent-*

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Database Settings - Using environment variables
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "infinite_scribe"

    NEO4J_HOST: str = "neo4j"
    NEO4J_PORT: int = 7687
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j"
    NEO4J_URI: str = ""  # Will be set from env or computed

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "redis"

    # Computed URLs
    @property
    def POSTGRES_URL(self) -> str:  # noqa: N802
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def NEO4J_URL(self) -> str:  # noqa: N802
        if self.NEO4J_URI:
            return self.NEO4J_URI
        return f"bolt://{self.NEO4J_HOST}:{self.NEO4J_PORT}"

    @property
    def REDIS_URL(self) -> str:  # noqa: N802
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # Other services
    MILVUS_HOST: str = "milvus"
    MILVUS_PORT: int = 19530

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"

    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"

    # Prefect
    PREFECT_API_URL: str = "http://prefect:4200/api"

    # AI Providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    class Config:
        # Load from .env.backend first, then .env.infrastructure, then .env
        env_file = (".env.backend", ".env.infrastructure", ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
