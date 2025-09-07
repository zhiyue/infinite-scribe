"""
Content version control schemas based on ADR-004

This module defines schemas for content versioning with snapshot + delta approach,
supporting DAG version graphs and three-way merge capabilities.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from src.schemas.base import BaseSchema


class VersionType(str, Enum):
    """Content version types"""

    SNAPSHOT = "snapshot"  # Full content snapshot
    DELTA = "delta"  # Delta/patch from parent
    MERGE = "merge"  # Merge of multiple versions


class PatchType(str, Enum):
    """Patch format types"""

    DMP = "dmp"  # Diff-Match-Patch format
    JSON_PATCH = "json_patch"  # JSON Patch RFC 6902
    REPLACE = "replace"  # Simple replacement


class DeltaTargetKind(str, Enum):
    """Target types for delta patches"""

    CHAPTER = "chapter"  # Chapter content
    METADATA = "metadata"  # Novel/chapter metadata
    OUTLINE = "outline"  # Story outline
    CHARACTER = "character"  # Character information
    WORLD = "world"  # World-building elements


class BranchStatus(str, Enum):
    """Branch lifecycle status"""

    ACTIVE = "active"  # Currently being worked on
    MERGED = "merged"  # Successfully merged
    ABANDONED = "abandoned"  # Abandoned/deleted


class ContentVersionCreate(BaseSchema):
    """Create a new content version"""

    project_id: UUID = Field(..., description="Project/Novel ID")
    branch_name: str = Field(
        ..., min_length=1, max_length=100, description="Branch name (e.g., 'main', 'draft-chapter-5')"
    )
    version_type: VersionType = Field(..., description="Version type")
    parent_ids: list[UUID] = Field(
        default_factory=list, description="Parent version IDs (empty for initial, multiple for merge)"
    )
    message: str = Field(..., min_length=1, max_length=500, description="Version commit message")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional version metadata")

    @field_validator("parent_ids")
    @classmethod
    def validate_parents(cls, v: list[UUID], info) -> list[UUID]:
        """Validate parent IDs based on version type"""
        values = info.data
        version_type = values.get("version_type")

        if version_type == VersionType.MERGE and len(v) < 2:
            raise ValueError("Merge versions must have at least 2 parents")
        elif version_type != VersionType.MERGE and len(v) > 1:
            raise ValueError("Non-merge versions can have at most 1 parent")

        return v


class ContentVersionResponse(BaseSchema):
    """Content version response"""

    id: UUID = Field(..., description="Version ID")
    project_id: UUID = Field(..., description="Project/Novel ID")
    branch_name: str = Field(..., description="Branch name")
    sequence: int = Field(..., ge=1, description="Sequence number within branch")
    version_type: VersionType = Field(..., description="Version type")
    storage_path: str | None = Field(None, description="MinIO object key for snapshots")
    content_hash: str = Field(..., description="SHA256 hash of content")
    content_size: int = Field(..., ge=0, description="Content size in bytes")
    compression: str | None = Field(None, description="Compression algorithm (e.g., 'zstd')")
    message: str = Field(..., description="Version message")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Version metadata")
    is_archived: bool = Field(False, description="Whether version is archived")
    created_at: datetime = Field(..., description="Creation timestamp")
    created_by: str = Field(..., description="Creator user ID or system identifier")


class ContentDeltaCreate(BaseSchema):
    """Create a content delta/patch"""

    project_id: UUID = Field(..., description="Project/Novel ID")
    version_id: UUID = Field(..., description="Associated version ID")
    target_kind: DeltaTargetKind = Field(..., description="Target content type")
    delta_path: str = Field(..., description="JSON Pointer path (e.g., '/chapters/5/content')")
    patch_type: PatchType = Field(..., description="Patch format")
    patch: bytes = Field(..., description="Compressed patch data")

    @field_validator("delta_path")
    @classmethod
    def validate_delta_path(cls, v: str) -> str:
        """Validate JSON Pointer format"""
        if not v.startswith("/"):
            raise ValueError("Delta path must start with '/'")
        return v


class ContentDeltaResponse(BaseSchema):
    """Content delta response"""

    id: UUID = Field(..., description="Delta ID")
    project_id: UUID = Field(..., description="Project/Novel ID")
    version_id: UUID = Field(..., description="Associated version ID")
    target_kind: DeltaTargetKind = Field(..., description="Target content type")
    delta_path: str = Field(..., description="JSON Pointer path")
    patch_type: PatchType = Field(..., description="Patch format")
    patch_size: int = Field(..., ge=0, description="Patch data size in bytes")
    stats: dict[str, Any] = Field(default_factory=dict, description="Delta statistics (additions, deletions, etc.)")


class BranchCreate(BaseSchema):
    """Create a new branch"""

    project_id: UUID = Field(..., description="Project/Novel ID")
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9-_]*$",
        description="Branch name (alphanumeric, hyphens, underscores)",
    )
    base_version_id: UUID | None = Field(None, description="Base version to branch from (None for initial branch)")
    description: str | None = Field(None, max_length=500, description="Branch description")


class BranchUpdate(BaseSchema):
    """Update branch HEAD"""

    head_version_id: UUID = Field(..., description="New HEAD version ID")
    expected_head: UUID | None = Field(None, description="Expected current HEAD for CAS update")
    status: BranchStatus | None = Field(None, description="Branch status")

    @model_validator(mode="after")
    def at_least_one_field(self):
        """Ensure at least one field is being updated"""
        if all(value is None for value in [self.head_version_id, self.status]):
            raise ValueError("At least one field must be provided for update")
        return self


class BranchResponse(BaseSchema):
    """Branch response"""

    id: UUID = Field(..., description="Branch ID")
    project_id: UUID = Field(..., description="Project/Novel ID")
    name: str = Field(..., description="Branch name")
    head_version_id: UUID | None = Field(None, description="Current HEAD version")
    base_version_id: UUID | None = Field(None, description="Base version ID")
    status: BranchStatus = Field(..., description="Branch status")
    description: str | None = Field(None, description="Branch description")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class VersionGraph(BaseSchema):
    """DAG representation of version history"""

    project_id: UUID = Field(..., description="Project/Novel ID")
    versions: list[ContentVersionResponse] = Field(..., description="All versions")
    edges: list[tuple[UUID, UUID]] = Field(..., description="Parent-child relationships (parent_id, child_id)")
    branches: list[BranchResponse] = Field(..., description="All branches")

    @property
    def root_versions(self) -> list[UUID]:
        """Get root versions (no parents)"""
        children = {edge[1] for edge in self.edges}
        return [v.id for v in self.versions if v.id not in children]

    @property
    def leaf_versions(self) -> list[UUID]:
        """Get leaf versions (no children)"""
        parents = {edge[0] for edge in self.edges}
        return [v.id for v in self.versions if v.id not in parents]


class MergeRequest(BaseSchema):
    """Request to merge branches"""

    project_id: UUID = Field(..., description="Project/Novel ID")
    source_branch: str = Field(..., description="Source branch name")
    target_branch: str = Field(..., description="Target branch name")
    message: str = Field(..., description="Merge commit message")
    strategy: str = Field("three-way", description="Merge strategy (three-way, ours, theirs)")
    conflict_resolution: dict[str, Any] | None = Field(None, description="Manual conflict resolutions")


class MergeResult(BaseSchema):
    """Result of merge operation"""

    success: bool = Field(..., description="Whether merge succeeded")
    merge_version_id: UUID | None = Field(None, description="Created merge version ID")
    conflicts: list[dict[str, Any]] = Field(default_factory=list, description="Detected conflicts requiring resolution")
    merged_changes: dict[str, Any] = Field(default_factory=dict, description="Summary of merged changes")


class ContentSnapshot(BaseSchema):
    """Full content snapshot for storage"""

    version_id: UUID = Field(..., description="Version ID")
    project_id: UUID = Field(..., description="Project/Novel ID")
    content: dict[str, Any] = Field(..., description="Full novel content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Snapshot metadata")

    @property
    def storage_key(self) -> str:
        """Generate MinIO storage key using content addressing"""
        import hashlib

        content_str = str(self.content)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()
        return f"snapshots/{self.project_id}/{content_hash[:2]}/{content_hash}"

    @property
    def cache_key(self) -> str:
        """Generate Redis cache key"""
        return f"version:content:{self.version_id}"
