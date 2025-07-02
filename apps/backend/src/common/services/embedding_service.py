"""Embedding service implementation for text vectorization."""

import httpx

from src.core.config import settings


class EmbeddingService:
    """Service for interacting with embedding API."""

    def __init__(self):
        """Initialize embedding service."""
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Establish HTTP client for embedding API."""
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def check_connection(self) -> bool:
        """Check if embedding API is accessible."""
        try:
            if not self._client:
                await self.connect()

            # 发送健康检查请求
            response = await self._client.get(f"{settings.EMBEDDING_API_URL}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def get_embedding(self, text: str) -> list[float]:
        """获取文本的向量表示."""
        if not self._client:
            await self.connect()

        if not self._client:
            raise RuntimeError("Embedding service client not connected")

        try:
            response = await self._client.post(
                f"{settings.EMBEDDING_API_URL}/api/embed",
                json={"model": settings.EMBEDDING_API_MODEL, "input": text},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result = response.json()
            # 根据 API 返回格式提取向量
            if "embeddings" in result:
                return result["embeddings"][0] if result["embeddings"] else []
            elif "embedding" in result:
                return result["embedding"]
            else:
                raise ValueError(f"Unexpected response format: {result}")

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Embedding API error: {e.response.status_code} - {e.response.text}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to get embedding: {e!s}") from e

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """批量获取文本的向量表示."""
        embeddings = []
        for text in texts:
            embedding = await self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings


# 创建全局实例
embedding_service = EmbeddingService()
