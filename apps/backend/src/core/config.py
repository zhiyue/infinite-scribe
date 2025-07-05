"""Configuration management for backend services."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_project_root() -> Path:
    """
    Find project root by looking for marker files.

    More robust than using multiple .parent calls.
    Prioritizes more specific markers over generic ones.

    Returns:
        Path: The project root directory

    Raises:
        FileNotFoundError: If project root cannot be determined
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

    # 如果没找到强标记文件, 再寻找弱标记文件
    for parent in current_path.parents:
        if any((parent / marker).exists() for marker in weak_markers):
            return parent

    # 方法2: 环境变量 (备选)
    if project_root_env := os.getenv("PROJECT_ROOT"):
        return Path(project_root_env)

    # 如果所有方法都失败了, 抛出明确错误而不是使用脆弱的硬编码路径
    raise FileNotFoundError(
        "无法找到项目根目录，请检查环境或设置 PROJECT_ROOT 变量。"
        "查找的标记文件包括: pyproject.toml, .git, package.json, docker-compose.yml, "
        "pnpm-workspace.yaml, README.md, Makefile"
    )


def get_backend_root() -> Path:
    """
    获取 backend 服务根目录路径。

    使用多种方法确保健壮性：
    1. 从项目根目录构建 apps/backend 路径
    2. 如果失败，则查找包含配置文件的目录
    3. 最后使用环境变量备选方案

    Returns:
        Path: backend 服务根目录 (apps/backend/)

    Raises:
        FileNotFoundError: 如果无法找到 backend 根目录
    """
    # 方法1: 从项目根目录构建路径 (推荐)
    try:
        project_root = get_project_root()
        backend_root = project_root / "apps" / "backend"

        # 验证这确实是 backend 目录 (查找标记文件)
        backend_markers = [
            "src/core/config.py",  # 当前配置文件
            "src/__init__.py",  # Python 包标记
            "Dockerfile",  # Docker 配置
        ]

        if any((backend_root / marker).exists() for marker in backend_markers):
            return backend_root

    except FileNotFoundError:
        pass  # 项目根目录未找到，尝试其他方法

    # 方法2: 从当前文件向上查找 backend 根目录
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        # 检查是否是 backend 根目录 (包含 src 目录和标记文件)
        if (
            parent.name == "backend"
            and (parent / "src").exists()
            and (parent / "src" / "__init__.py").exists()
        ):
            return parent

    # 方法3: 环境变量备选方案
    if backend_root_env := os.getenv("BACKEND_ROOT"):
        return Path(backend_root_env)

    # 如果所有方法都失败了，抛出明确错误
    raise FileNotFoundError(
        "无法找到 backend 根目录。请检查项目结构或设置 BACKEND_ROOT 环境变量。"
        "期望的目录结构: PROJECT_ROOT/apps/backend/ 或包含 src/core/config.py 的目录"
    )


# 项目根目录
PROJECT_ROOT = get_project_root()

# Backend 特定的 .env 文件路径
BACKEND_ROOT = get_backend_root()
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"

# 项目根目录的 .env 文件路径
PROJECT_ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """
    Base settings for all backend services.

    配置优先级 (从高到低):
    1. 环境变量
    2. apps/backend/.env (backend 特定配置)
    3. PROJECT_ROOT/.env (项目通用配置)
    4. 默认值

    Pydantic 会自动从环境变量和 .env 文件中读取并完成类型转换.
    如果转换失败, 应用在启动时就会抛出清晰的验证错误.
    """

    model_config = SettingsConfigDict(
        # 按优先级从低到高排列，后面的文件会覆盖前面的
        env_file=[
            path
            for path in [
                str(PROJECT_ENV_FILE) if PROJECT_ENV_FILE.exists() else None,
                str(BACKEND_ENV_FILE) if BACKEND_ENV_FILE.exists() else None,
            ]
            if path is not None
        ],
        env_file_encoding="utf-8",
        case_sensitive=True,
        # 环境变量优先级高于 .env 文件
        env_prefix="",
        # 允许额外的字段 (忽略未定义的环境变量)
        extra="ignore",
    )

    # Service identification
    SERVICE_NAME: str = "infinite-scribe-backend"
    SERVICE_TYPE: str = "api-gateway"
    NODE_ENV: str = "development"

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"

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


# 创建全局设置实例
settings = Settings()
