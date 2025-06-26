"""Configuration management for backend services."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Base settings for all backend services."""
    
    # Service identification
    SERVICE_NAME: str = "infinite-scribe-backend"
    SERVICE_TYPE: str = "api-gateway"  # or agent-*
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Database URLs
    POSTGRES_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/infinite_scribe"
    REDIS_URL: str = "redis://:redis@localhost:6379/0"
    NEO4J_URL: str = "bolt://neo4j:neo4j@localhost:7687"
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    
    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    
    # Prefect
    PREFECT_API_URL: str = "http://localhost:4200/api"
    
    # AI Providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()