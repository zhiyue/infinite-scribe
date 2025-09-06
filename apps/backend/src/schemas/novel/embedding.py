"""
Vector embedding integration schemas based on ADR-002

This module defines schemas for vector embedding operations using the Qwen3-Embedding model,
supporting semantic search and similarity calculations across novel content.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from src.schemas.base import BaseSchema


class EmbeddingTarget(str, Enum):
    """Target types for embedding generation"""

    CHAPTER_CONTENT = "chapter_content"  # Chapter text content
    CHARACTER_DESCRIPTION = "character_description"  # Character details
    SCENE_DESCRIPTION = "scene_description"  # Scene descriptions
    WORLD_ELEMENT = "world_element"  # World-building elements
    DIALOGUE = "dialogue"  # Character dialogue
    PLOT_SUMMARY = "plot_summary"  # Plot summaries
    THEME_CONCEPT = "theme_concept"  # Thematic concepts


class SearchScope(str, Enum):
    """Search scope for similarity queries"""

    NOVEL = "novel"  # Search within single novel
    PROJECT = "project"  # Search across project
    GLOBAL = "global"  # Search across all content


class IndexType(str, Enum):
    """Milvus index types"""

    HNSW = "HNSW"  # Hierarchical Navigable Small World
    IVF_FLAT = "IVF_FLAT"  # Inverted File with Flat
    IVF_SQ8 = "IVF_SQ8"  # Inverted File with Scalar Quantization
    ANNOY = "ANNOY"  # Approximate Nearest Neighbors Oh Yeah


class MetricType(str, Enum):
    """Distance metric types"""

    COSINE = "COSINE"  # Cosine similarity
    L2 = "L2"  # Euclidean distance
    IP = "IP"  # Inner product


# Configuration Schemas


class EmbeddingConfig(BaseSchema):
    """Embedding model configuration"""

    model_name: str = Field("Qwen3-Embedding", description="Embedding model name")
    model_size: str = Field("0.6B", description="Model size")
    embedding_dimension: int = Field(768, description="Vector dimension")
    api_endpoint: str = Field("http://192.168.1.191:11434/api/embed", description="Ollama API endpoint")
    max_tokens: int = Field(8192, description="Maximum input tokens")
    batch_size: int = Field(32, description="Batch processing size")

    @field_validator("embedding_dimension")
    @classmethod
    def validate_dimension(cls, v: int) -> int:
        """Validate embedding dimension"""
        if v not in [384, 768, 1536]:
            raise ValueError("Dimension must be 384, 768, or 1536 for Qwen3-Embedding")
        return v


class MilvusCollectionConfig(BaseSchema):
    """Milvus collection configuration"""

    collection_name: str = Field(..., description="Collection name")
    dimension: int = Field(768, description="Vector dimension")
    index_type: IndexType = Field(IndexType.HNSW, description="Index type")
    metric_type: MetricType = Field(MetricType.COSINE, description="Distance metric")
    index_params: dict[str, Any] = Field(
        default_factory=lambda: {"M": 32, "efConstruction": 200}, description="Index parameters"
    )
    search_params: dict[str, Any] = Field(default_factory=lambda: {"ef": 100}, description="Search parameters")

    @model_validator(mode="after")
    def validate_index_params(self):
        """Validate index parameters based on type"""
        if self.index_type == IndexType.HNSW:
            required = {"M", "efConstruction"}
            if not all(k in self.index_params for k in required):
                raise ValueError(f"HNSW requires parameters: {required}")
        elif self.index_type == IndexType.IVF_FLAT:
            if "nlist" not in self.index_params:
                raise ValueError("IVF_FLAT requires 'nlist' parameter")
        return self


# Embedding Operation Schemas


class EmbeddingRequest(BaseSchema):
    """Request to generate embeddings"""

    content: str = Field(..., description="Text content to embed")
    target_type: EmbeddingTarget = Field(..., description="Content type")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    chunk_size: int | None = Field(None, ge=100, le=2000, description="Optional chunk size for long content")
    overlap: int = Field(50, ge=0, le=500, description="Overlap between chunks")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is not empty"""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class EmbeddingResponse(BaseSchema):
    """Embedding generation response"""

    embedding_id: str = Field(..., description="Embedding identifier")
    vector: list[float] = Field(..., description="Embedding vector")
    dimension: int = Field(..., description="Vector dimension")
    target_type: EmbeddingTarget = Field(..., description="Content type")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")
    model_version: str = Field(..., description="Model version used")
    created_at: datetime = Field(..., description="Generation timestamp")

    @field_validator("vector")
    @classmethod
    def validate_vector(cls, v: list[float], info) -> list[float]:
        """Validate vector dimension matches"""
        values = info.data
        dimension = values.get("dimension", 768)
        if len(v) != dimension:
            raise ValueError(f"Vector dimension mismatch: expected {dimension}, got {len(v)}")
        return v


class BatchEmbeddingRequest(BaseSchema):
    """Batch embedding request"""

    items: list[EmbeddingRequest] = Field(..., min_length=1, max_length=100, description="Batch of embedding requests")
    parallel: bool = Field(True, description="Process in parallel")

    @field_validator("items")
    @classmethod
    def validate_batch_size(cls, v: list) -> list:
        """Validate batch size limits"""
        if len(v) > 100:
            raise ValueError("Batch size cannot exceed 100 items")
        return v


class BatchEmbeddingResponse(BaseSchema):
    """Batch embedding response"""

    embeddings: list[EmbeddingResponse] = Field(..., description="Generated embeddings")
    batch_size: int = Field(..., description="Actual batch size processed")
    processing_time_ms: int = Field(..., ge=0, description="Total processing time")
    failed_items: list[dict[str, str]] = Field(default_factory=list, description="Failed items with error messages")

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.batch_size
        failed = len(self.failed_items)
        return (total - failed) / total if total > 0 else 0.0


# Search and Similarity Schemas


class SimilaritySearchRequest(BaseSchema):
    """Similarity search request"""

    query: str | list[float] = Field(..., description="Query text or vector")
    target_types: list[EmbeddingTarget] | None = Field(None, description="Filter by content types")
    scope: SearchScope = Field(SearchScope.NOVEL, description="Search scope")
    scope_id: UUID | None = Field(None, description="Scope identifier (novel/project ID)")
    top_k: int = Field(10, ge=1, le=100, description="Number of results")
    score_threshold: float | None = Field(None, ge=0.0, le=1.0, description="Minimum similarity score")
    filters: dict[str, Any] = Field(default_factory=dict, description="Additional metadata filters")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v) -> str | list[float]:
        """Validate query format"""
        if isinstance(v, str) and not v.strip():
            raise ValueError("Query text cannot be empty")
        elif isinstance(v, list) and (len(v) == 0 or not all(isinstance(x, int | float) for x in v)):
            raise ValueError("Query vector must be non-empty list of numbers")
        return v


class SimilaritySearchResult(BaseSchema):
    """Single search result"""

    id: str = Field(..., description="Result identifier")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    content: str = Field(..., description="Original content")
    target_type: EmbeddingTarget = Field(..., description="Content type")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Result metadata")
    source_reference: dict[str, Any] = Field(..., description="Source location (chapter, scene, etc.)")


class SimilaritySearchResponse(BaseSchema):
    """Similarity search response"""

    query: str = Field(..., description="Original query")
    results: list[SimilaritySearchResult] = Field(..., description="Search results")
    total_found: int = Field(..., ge=0, description="Total matches found")
    search_time_ms: int = Field(..., ge=0, description="Search execution time")

    @property
    def has_results(self) -> bool:
        """Check if search found results"""
        return len(self.results) > 0

    @property
    def best_score(self) -> float | None:
        """Get best similarity score"""
        return max((r.score for r in self.results), default=None)


class SemanticCluster(BaseSchema):
    """Semantic cluster of similar content"""

    cluster_id: str = Field(..., description="Cluster identifier")
    centroid: list[float] = Field(..., description="Cluster centroid vector")
    members: list[str] = Field(..., description="Member embedding IDs")
    target_type: EmbeddingTarget = Field(..., description="Primary content type")
    coherence_score: float = Field(..., ge=0.0, le=1.0, description="Cluster coherence score")
    representative_content: str = Field(..., description="Representative text sample")

    @property
    def size(self) -> int:
        """Get cluster size"""
        return len(self.members)


class ContentDuplicationCheck(BaseSchema):
    """Check for content duplication"""

    content: str = Field(..., description="Content to check")
    threshold: float = Field(0.9, ge=0.0, le=1.0, description="Similarity threshold for duplication")
    scope: SearchScope = Field(SearchScope.NOVEL, description="Check scope")
    scope_id: UUID | None = Field(None, description="Scope identifier")


class ContentDuplicationResult(BaseSchema):
    """Duplication check result"""

    is_duplicate: bool = Field(..., description="Whether content is duplicate")
    similar_content: list[SimilaritySearchResult] = Field(default_factory=list, description="Similar content found")
    max_similarity: float = Field(0.0, ge=0.0, le=1.0, description="Maximum similarity score")

    @model_validator(mode="after")
    def validate_duplication(self):
        """Update duplication flag based on results"""
        if self.similar_content:
            self.max_similarity = max(r.score for r in self.similar_content)
        return self


# Index Management Schemas


class IndexStatus(BaseSchema):
    """Milvus index status"""

    collection_name: str = Field(..., description="Collection name")
    index_type: IndexType = Field(..., description="Index type")
    metric_type: MetricType = Field(..., description="Metric type")
    total_vectors: int = Field(..., ge=0, description="Total vectors indexed")
    index_size_mb: float = Field(..., ge=0, description="Index size in MB")
    is_built: bool = Field(..., description="Whether index is built")
    last_updated: datetime = Field(..., description="Last update timestamp")


class ReindexRequest(BaseSchema):
    """Request to rebuild index"""

    collection_name: str = Field(..., description="Collection to reindex")
    new_index_type: IndexType | None = Field(None, description="Optional new index type")
    new_index_params: dict[str, Any] | None = Field(None, description="Optional new parameters")
    force: bool = Field(False, description="Force reindex even if up-to-date")


class ReindexResponse(BaseSchema):
    """Reindex operation response"""

    success: bool = Field(..., description="Whether reindex succeeded")
    vectors_processed: int = Field(..., ge=0, description="Vectors processed")
    time_taken_seconds: float = Field(..., ge=0, description="Time taken")
    old_index_type: IndexType = Field(..., description="Previous index type")
    new_index_type: IndexType = Field(..., description="New index type")
