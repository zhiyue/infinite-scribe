"""
Novel-related Pydantic schemas

Schema modules based on accepted ADRs:
- create.py: Novel creation request DTOs
- update.py: Novel update request DTOs
- read.py: Novel query response DTOs
- dialogue.py: Conversation session management (ADR-001)
- version.py: Content version control (ADR-004)
- graph.py: Knowledge graph structures (ADR-005)
- embedding.py: Vector embedding integration (ADR-002)
"""

# Basic CRUD schemas
from .create import *  # noqa: F403

# ADR-001: Dialogue State Management
from .dialogue import (  # noqa: F401
    ConversationRoundCreate,
    ConversationRoundResponse,
    ConversationRoundUpdate,
    ConversationSessionCreate,
    ConversationSessionResponse,
    ConversationSessionUpdate,
    DialogueCache,
    DialogueHistory,
    DialogueRole,
    ScopeType,
    SessionStatus,
)

# ADR-002: Vector Embedding Model
from .embedding import (  # noqa: F401
    BatchEmbeddingRequest,
    BatchEmbeddingResponse,
    ContentDuplicationCheck,
    ContentDuplicationResult,
    EmbeddingConfig,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingTarget,
    IndexStatus,
    IndexType,
    MetricType,
    MilvusCollectionConfig,
    ReindexRequest,
    ReindexResponse,
    SearchScope,
    SemanticCluster,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
    SimilaritySearchResult,
)

# ADR-005: Knowledge Graph Schema
from .graph import (  # noqa: F401
    ChapterNode,
    CharacterNetwork,
    CharacterNode,
    CharacterRelationship,
    CharacterRole,
    CharacterStateNode,
    ConflictNode,
    ConflictSeverity,
    ConstraintNode,
    EventCausality,
    EventNode,
    GraphNodeBase,
    GraphQueryResult,
    LocationHierarchy,
    LocationNode,
    LocationType,
    NodeType,
    NovelNode,
    RelationshipBase,
    RelationshipType,
    SceneNode,
    SceneParticipation,
    StoryTimeline,
    WorldDimensionNode,
    WorldRuleNode,
)
from .read import *  # noqa: F403
from .update import *  # noqa: F403

# ADR-004: Content Version Control
from .version import (  # noqa: F401
    BranchCreate,
    BranchResponse,
    BranchStatus,
    BranchUpdate,
    ContentDeltaCreate,
    ContentDeltaResponse,
    ContentSnapshot,
    ContentVersionCreate,
    ContentVersionResponse,
    DeltaTargetKind,
    MergeRequest,
    MergeResult,
    PatchType,
    VersionGraph,
    VersionType,
)
