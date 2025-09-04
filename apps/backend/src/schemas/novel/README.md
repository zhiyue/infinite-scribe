# Novel Schemas Documentation

This directory contains Pydantic schemas for the novel-writing domain, organized according to accepted Architecture Decision Records (ADRs).

## Schema Organization

### Core CRUD Operations

- **`create.py`** - Novel creation request schemas
- **`update.py`** - Novel update request schemas  
- **`read.py`** - Novel query response schemas

### ADR-001: Dialogue State Management

**File:** `dialogue.py`

Implements generic conversation session management for AI-assisted novel creation dialogues.

**Key Concepts:**
- **Session Scopes**: GENESIS, CHAPTER, REVIEW, PLANNING, WORLDBUILDING
- **Session Status**: ACTIVE, COMPLETED, ABANDONED, PAUSED
- **Hierarchical Rounds**: Support for nested dialogue turns (e.g., "2.1.1")
- **Optimistic Concurrency**: Version-based conflict resolution
- **Caching Strategy**: Write-through with Redis (30-day TTL)

**Main Schemas:**
- `ConversationSessionCreate/Update/Response` - Session lifecycle management
- `ConversationRoundCreate/Update/Response` - Individual dialogue turns
- `DialogueHistory` - Complete session history with metrics
- `DialogueCache` - Redis cache structure

### ADR-002: Vector Embedding Model

**File:** `embedding.py`

Integrates Qwen3-Embedding 0.6B model for semantic search and similarity calculations.

**Key Concepts:**
- **Self-hosted Model**: Qwen3-Embedding at `http://192.168.1.191:11434`
- **Vector Storage**: Milvus with HNSW indexing
- **Embedding Targets**: Chapter content, characters, scenes, world elements
- **Search Scopes**: Novel, project, or global

**Main Schemas:**
- `EmbeddingConfig` - Model configuration (768-dim vectors)
- `MilvusCollectionConfig` - Index configuration (HNSW, COSINE)
- `EmbeddingRequest/Response` - Single/batch embedding operations
- `SimilaritySearchRequest/Response` - Semantic search operations
- `ContentDuplicationCheck/Result` - Duplicate detection

### ADR-004: Content Version Control

**File:** `version.py`

Provides Git-like version control for novel content with snapshot + delta storage.

**Key Concepts:**
- **Hybrid Storage**: Snapshots in MinIO, deltas in PostgreSQL
- **DAG Version Graph**: Support for branching and merging
- **Three-way Merge**: Chapter-level conflict resolution
- **Content Addressing**: SHA256-based deduplication
- **Compression**: zstd for efficient storage

**Main Schemas:**
- `ContentVersionCreate/Response` - Version creation and retrieval
- `ContentDeltaCreate/Response` - Incremental changes (DMP/JSON Patch)
- `BranchCreate/Update/Response` - Branch management with CAS updates
- `MergeRequest/Result` - Three-way merge operations
- `VersionGraph` - DAG representation of version history

### ADR-005: Knowledge Graph Schema

**File:** `graph.py`

Defines Neo4j graph structure for world-building and story consistency.

**Key Concepts:**
- **Mixed Model**: Hierarchical (locations) + Network (relationships)
- **8-Dimensional Characters**: Appearance, personality, background, motivation, goals, obstacles, arc, secrets
- **Novel Isolation**: All nodes scoped by `novel_id`
- **Consistency Tracking**: Constraints and conflict detection
- **Scale Support**: 100k+ nodes, 500k+ relationships

**Node Types:**
- **World-building**: Novel, WorldDimension, WorldRule, Location
- **Characters**: Character (8 dimensions), CharacterState
- **Story Structure**: Chapter, Scene, Event
- **Consistency**: Constraint, Conflict

**Relationship Types:**
- `RELATES_TO` - Character relationships (-10 to +10 strength)
- `LOCATED_IN` - Location hierarchy
- `PARTICIPATES_IN` - Character-scene participation
- `TRIGGERS` - Event causality chains
- `AFFECTS` - Event impacts on characters

## Database Schema Requirements

Based on the accepted ADRs, the following database changes are required:

### PostgreSQL Tables

**To Create:**
```sql
-- ADR-001: Dialogue State Management
conversation_sessions (
  id UUID PRIMARY KEY,
  scope_type TEXT,
  scope_id TEXT,
  status TEXT,
  stage TEXT,
  state JSONB,
  version INTEGER,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

conversation_rounds (
  session_id UUID REFERENCES conversation_sessions,
  round_path TEXT,
  role TEXT,
  input JSONB,
  output JSONB,
  tool_calls JSONB,
  model TEXT,
  tokens_in INTEGER,
  tokens_out INTEGER,
  latency_ms INTEGER,
  cost NUMERIC,
  correlation_id TEXT,
  created_at TIMESTAMPTZ,
  PRIMARY KEY (session_id, round_path)
)

-- ADR-004: Content Version Control
content_versions (
  id UUID PRIMARY KEY,
  project_id UUID,
  branch_name STRING,
  sequence BIGINT,
  version_type ENUM,
  storage_path STRING,
  content_hash STRING,
  content_size BIGINT,
  compression STRING,
  message STRING,
  metadata JSON,
  is_archived BOOLEAN,
  created_at TIMESTAMPTZ,
  created_by STRING
)

content_version_parents (
  version_id UUID REFERENCES content_versions,
  parent_id UUID REFERENCES content_versions,
  relation ENUM,
  PRIMARY KEY (version_id, parent_id)
)

content_deltas (
  id UUID PRIMARY KEY,
  project_id UUID,
  version_id UUID REFERENCES content_versions,
  target_kind ENUM,
  delta_path STRING,
  patch_type ENUM,
  patch LARGEBINARY,
  stats JSON
)

branches (
  id UUID PRIMARY KEY,
  project_id UUID,
  name STRING,
  head_version_id UUID REFERENCES content_versions,
  base_version_id UUID REFERENCES content_versions,
  status ENUM,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
```

**To Delete:**
- `genesis_sessions` (replaced by conversation_sessions)

### Neo4j Constraints & Indexes

```cypher
-- Unique constraints on app_id for all node types
CREATE CONSTRAINT unique_novel_app_id ON (n:Novel) ASSERT n.app_id IS UNIQUE;
CREATE CONSTRAINT unique_character_app_id ON (c:Character) ASSERT c.app_id IS UNIQUE;
CREATE CONSTRAINT unique_location_app_id ON (l:Location) ASSERT l.app_id IS UNIQUE;
-- ... (repeat for all node types)

-- Indexes for performance
CREATE INDEX novel_id_index FOR (n:Novel) ON (n.novel_id);
CREATE INDEX character_name_index FOR (c:Character) ON (c.name);
CREATE INDEX location_name_index FOR (l:Location) ON (l.name);
```

### Redis Key Patterns

- Dialogue sessions: `dialogue:session:{session_id}`
- Content versions: `version:content:{version_id}`
- Embedding cache: `embedding:{content_hash}`

### MinIO Storage Structure

```
/snapshots/{project_id}/{hash[:2]}/{hash}  # Content snapshots
/embeddings/{novel_id}/{type}/{id}         # Vector embeddings
```

### Milvus Collections

```python
collection_schema = {
    "name": "novel_embeddings",
    "dimension": 768,
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "index_params": {
        "M": 32,
        "efConstruction": 200
    }
}
```

## Usage Examples

### Creating a Dialogue Session

```python
from src.schemas.novel import ConversationSessionCreate, ScopeType

session = ConversationSessionCreate(
    scope_type=ScopeType.GENESIS,
    scope_id="novel_123",
    stage="world_building",
    initial_state={"theme": "sci-fi", "setting": "mars"}
)
```

### Generating Embeddings

```python
from src.schemas.novel import EmbeddingRequest, EmbeddingTarget

request = EmbeddingRequest(
    content="The red planet loomed before them...",
    target_type=EmbeddingTarget.CHAPTER_CONTENT,
    metadata={"chapter": 5, "scene": 2}
)
```

### Creating a Version

```python
from src.schemas.novel import ContentVersionCreate, VersionType

version = ContentVersionCreate(
    project_id="novel_123",
    branch_name="draft-chapter-5",
    version_type=VersionType.DELTA,
    parent_ids=["parent_version_id"],
    message="Added opening scene to chapter 5"
)
```

### Defining a Character Node

```python
from src.schemas.novel import CharacterNode, CharacterRole

character = CharacterNode(
    app_id="char_001",
    novel_id="novel_123",
    name="Alex Chen",
    role=CharacterRole.PROTAGONIST,
    age=32,
    appearance={"height": "180cm", "hair": "black"},
    personality={"traits": ["determined", "curious"]},
    goals={
        "short_term": ["Find the artifact"],
        "mid_term": ["Uncover the conspiracy"],
        "long_term": ["Save humanity"]
    }
)
```

## Integration Points

### Service Dependencies

- **PostgreSQL**: Session state, version metadata, deltas
- **Redis**: Session caching, version content caching  
- **Neo4j**: Knowledge graph storage and queries
- **Milvus**: Vector embeddings and similarity search
- **MinIO**: Content snapshot storage
- **Ollama**: Embedding model API (`http://192.168.1.191:11434`)

### API Endpoints

Suggested endpoint structure:

```
/api/v1/novels/{novel_id}/
  /sessions/           # Dialogue sessions
  /versions/           # Content versions
  /branches/           # Version branches
  /graph/              # Knowledge graph queries
  /search/             # Semantic search
  /embeddings/         # Embedding operations
```

## Migration Notes

When implementing these schemas:

1. Run database migrations in order:
   - Create new tables before deleting old ones
   - Migrate data from `genesis_sessions` to `conversation_sessions`
   
2. Initialize Neo4j constraints before data import

3. Configure Milvus collections with proper index parameters

4. Set up Redis with appropriate TTL policies

5. Ensure MinIO buckets are created with proper access policies

## Testing Considerations

- Use test containers for all databases
- Mock Ollama API for unit tests
- Test version graph traversal algorithms
- Validate constraint checking in Neo4j
- Test cache invalidation scenarios
- Verify embedding dimension consistency