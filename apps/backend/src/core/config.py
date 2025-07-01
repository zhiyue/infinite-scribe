"""Configuration management for backend services."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings


def get_project_root() -> Path:
    """
    Find project root by looking for marker files.

    More robust than using multiple .parent calls.
    Prioritizes more specific markers over generic ones.
    """
    # 方法1: 查找标记文件 (推荐)
    current_path = Path(__file__).resolve()

    # 优先级1: 强标记文件 (通常只存在于项目根目录)
    strong_markers = [
        "pyproject.toml",
        ".git",
        "package.json",
        "docker-compose.yml",
        "pnpm-workspace.yaml",  # 添加这个作为monorepo的强标记
    ]

    # 优先级2: 弱标记文件 (可能存在于子目录)
    weak_markers = [
        "README.md",
        "Makefile",
    ]

    # 首先寻找强标记文件
    for parent in current_path.parents:
        if any((parent / marker).exists() for marker in strong_markers):
            return parent

    # 如果没找到强标记文件，再寻找弱标记文件
    for parent in current_path.parents:
        if any((parent / marker).exists() for marker in weak_markers):
            return parent

    # 方法2: 环境变量 (备选)
    if project_root_env := os.getenv("PROJECT_ROOT"):
        return Path(project_root_env)

    # 方法3: 固定相对路径 (最后备选)
    # 从当前文件位置: apps/backend/src/core/config.py
    return Path(__file__).resolve().parents[4]


# 项目根目录
PROJECT_ROOT = get_project_root()
ENV_FILE_PATH = PROJECT_ROOT / ".env"


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
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "infinite_scribe"

    NEO4J_HOST: str = "localhost"
    NEO4J_PORT: int = 7687
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j"
    NEO4J_URI: str = ""  # Will be set from env or computed

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

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
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # Other services
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530

    # Kafka - 关键配置
    KAFKA_HOST: str = "localhost"
    KAFKA_PORT: int = 9092
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_GROUP_ID_PREFIX: str = "infinite-scribe"

    @property
    def KAFKA_BOOTSTRAP_SERVERS(self) -> str:  # noqa: N802
        """计算 Kafka bootstrap servers 地址"""
        return f"{self.KAFKA_HOST}:{self.KAFKA_PORT}"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"

    # Prefect
    PREFECT_API_URL: str = "http://localhost:4200/api"

    # AI Providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    class Config:
        # 优先从环境变量加载，然后从 .env 文件
        env_file = str(ENV_FILE_PATH) if ENV_FILE_PATH.exists() else None
        env_file_encoding = "utf-8"
        case_sensitive = True
        # 环境变量优先级高于文件
        env_prefix = ""
        # 允许额外的字段（忽略未定义的环境变量）
        extra = "ignore"


# 创建全局设置实例
settings = Settings()
