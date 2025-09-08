"""Embedding API client for generating text vectors.

This module provides an async HTTP client wrapper to call the external
embedding service and return embedding vectors. It is intentionally
kept independent from the vector database access layer so callers can
compose generation + storage according to their needs.
"""

from __future__ import annotations

import httpx

from src.core.config import settings


class EmbeddingService:
    """Client for interacting with the embedding HTTP API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Create the underlying HTTP client if not present."""
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )

    async def disconnect(self) -> None:
        """Close and dispose the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def check_connection(self) -> bool:
        """Simple health check against the embedding API."""
        try:
            if not self._client:
                await self.connect()

            assert self._client is not None, "Client should be initialized after connect()"

            response = await self._client.get(f"{settings.embedding_api_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def get_embedding(self, text: str) -> list[float]:
        """Get the embedding vector for a single text input."""
        if not self._client:
            await self.connect()

        if not self._client:
            raise RuntimeError("Embedding service client not connected")

        try:
            response = await self._client.post(
                f"{settings.embedding_api_url}/api/embed",
                json={"model": settings.embedding_api_model, "input": text},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result = response.json()
            # Handle both common response formats
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
        """Get embeddings for a list of texts sequentially."""
        embeddings: list[list[float]] = []
        for text in texts:
            embedding = await self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings


# Module-level singleton for convenience (matches previous usage)
embedding_service = EmbeddingService()

