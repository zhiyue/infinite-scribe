---
created: 2025-08-28T12:10:36Z
last_updated: 2025-08-28T12:24:28Z
version: 1.1
author: Claude Code PM System
---

# System Patterns & Architecture

## Core Architectural Patterns

### Event-Driven Microservices Architecture
InfiniteScribe follows a sophisticated event-driven microservices architecture designed for AI-powered novel generation:

- **Central Event Bus**: Apache Kafka serves as the backbone for all inter-service communication
- **Service Decoupling**: Services communicate exclusively through events, avoiding direct calls
- **Service Types**: API Gateway, Message Relay, Prefect Orchestrator, Callback Service, AI Agents
- **Async Processing**: All AI generation and business logic operates asynchronously
- **System Resilience**: Event-driven design provides high fault tolerance and scalability

### Core Implementation Patterns

#### CQRS (Command Query Responsibility Segregation)
```python
# Command Side - Write Operations
class CommandHandler:
    async def handle_generate_chapter_command(self, command: GenerateChapterCommand):
        # Write to command_inbox with idempotency
        # Publish events to event_outbox
        # Update state snapshots
        pass

# Query Side - Read Operations  
class QueryHandler:
    async def get_novel_state(self, novel_id: str) -> NovelState:
        # Read from optimized state snapshots
        # No business logic, just data retrieval
        pass
```

#### Event Sourcing
```python
# domain_events table as single source of truth
class DomainEvent:
    id: UUID
    aggregate_id: UUID  # novel_id, chapter_id, etc.
    event_type: str     # "Chapter.OutlineCreated", "Novel.StatusChanged"
    event_data: Dict    # All state change information
    occurred_at: DateTime
    version: int        # For optimistic concurrency
```

#### Transactional Outbox Pattern
```python
# Ensures atomic writes and reliable message publishing
@transaction
async def create_chapter_outline(self, command: CreateOutlineCommand):
    # 1. Write domain event
    await self.event_store.append_event(domain_event)
    # 2. Write to outbox (same transaction)
    await self.outbox.add_message(kafka_message)
    # 3. Message Relay publishes from outbox to Kafka
```

#### Command Inbox Pattern
```python
# Provides idempotent command processing
class CommandInbox:
    async def process_command(self, command_id: str, command: Command):
        # Check if already processed (idempotency)
        if await self.is_processed(command_id):
            return await self.get_result(command_id)
        
        # Process command atomically
        result = await self.handle_command(command)
        await self.mark_processed(command_id, result)
        return result
```

### Pause and Resume Workflow Pattern
```python
# Prefect workflows can pause and resume based on external events
@flow
async def chapter_generation_workflow():
    # Execute initial tasks
    outline = await create_outline_task()
    
    # Register callback and pause
    callback_handle = await register_callback("Chapter.Drafted")
    await self.pause_until_event("Chapter.Drafted", callback_handle)
    
    # Resume when AI agent completes work
    draft = await get_callback_result()
    # Continue workflow...
```

## Multi-Agent Coordination Patterns

### Specialized Agent Architecture
InfiniteScribe employs a sophisticated multi-agent system with 10 specialized AI agents:

```python
class AgentRegistry:
    AGENTS = {
        'worldsmith': WorldsmithAgent,      # Genesis world creation
        'plotmaster': PlotMasterAgent,      # High-level plot strategy
        'outliner': OutlinerAgent,          # Chapter-level planning
        'director': DirectorAgent,          # Scene structure and pacing
        'character_expert': CharacterExpertAgent,  # Character development
        'worldbuilder': WorldBuilderAgent,  # World expansion
        'writer': WriterAgent,              # Content generation
        'critic': CriticAgent,              # Quality assessment
        'fact_checker': FactCheckerAgent,   # Consistency validation
        'rewriter': RewriterAgent           # Content revision
    }
```

### Agent Communication Pattern
```python
# Agents communicate via Kafka events, not direct calls
class AgentCoordinator:
    async def execute_chapter_workflow(self, chapter_context: ChapterContext):
        # Outliner creates chapter outline
        await self.publish_event("OutlineGeneration.Requested", chapter_context)
        
        # Director breaks down into scenes (triggered by OutlineGeneration.Completed)
        # CharacterExpert plans dialogues (triggered by Scene.StructureCreated)  
        # Writer generates content (triggered by Character.InteractionsPlanned)
        # Critic evaluates quality (triggered by Chapter.Drafted)
        # FactChecker validates consistency (triggered by Chapter.Reviewed)
```

### Knowledge Persistence Pattern
```python
class KnowledgeManager:
    # Multi-database knowledge persistence
    async def store_agent_output(self, agent_type: str, output: AgentOutput):
        # PostgreSQL for structured metadata
        await self.postgres.store_metadata(output.metadata)
        
        # Neo4j for relationships (character connections, plot threads)
        await self.neo4j.store_relationships(output.relationships)
        
        # Milvus for vector embeddings (context retrieval)
        await self.milvus.store_embeddings(output.content_embeddings)
        
        # MinIO for large content (chapter drafts, worldbuilding docs)
        await self.minio.store_content(output.content_files)
```

### Agent Workflow Orchestration
```python
# Prefect orchestrates complex multi-agent workflows
@flow
async def novel_generation_flow(novel_context: NovelContext):
    # Strategic level (runs periodically)
    plot_guidance = await plotmaster_task(novel_context)
    
    # Tactical level (per chapter)
    for chapter_num in range(novel_context.target_chapters):
        # Planning phase
        outline = await outliner_task(plot_guidance, chapter_num)
        scenes = await director_task(outline)
        
        # Creation phase  
        character_work = await character_expert_task(scenes)
        world_expansion = await worldbuilder_task(scenes)
        
        # Generation phase
        draft = await writer_task(scenes, character_work, world_expansion)
        
        # Review phase
        quality_review = await critic_task(draft)
        consistency_check = await fact_checker_task(draft)
        
        # Revision if needed
        if not quality_review.approved or not consistency_check.approved:
            draft = await rewriter_task(draft, quality_review, consistency_check)
```

## Frontend Architectural Patterns

### Component-Based Architecture
- **Atomic Design**: Atoms, molecules, organisms, templates, pages
- **Presentation/Container**: Separation of UI logic and business logic
- **Higher-Order Components**: Cross-cutting concerns like authentication
- **Custom Hooks**: Reusable state logic and side effects

### State Management Pattern
```typescript
// Zustand-based global state management
interface AppState {
  user: User | null;
  currentNovel: Novel | null;
  agentStates: Record<string, AgentState>;
  workflowStatus: WorkflowStatus;
}

// Zustand store with actions
const useAppStore = create<AppState & AppActions>((set, get) => ({
  user: null,
  currentNovel: null,
  agentStates: {},
  workflowStatus: 'idle',
  
  // Actions
  setUser: (user: User) => set({ user }),
  updateNovel: (updates: Partial<Novel>) => 
    set(state => ({ currentNovel: { ...state.currentNovel, ...updates } })),
  updateAgentState: (agentId: string, state: AgentState) =>
    set(state => ({ agentStates: { ...state.agentStates, [agentId]: state } }))
}));
```

### Data Flow Patterns
- **TanStack Query**: Server state management with intelligent caching and background updates
- **SSE Integration**: Real-time workflow status updates from backend via Server-Sent Events
- **Optimistic Updates**: Immediate UI updates with automatic rollback on errors
- **Event-Driven UI**: Frontend reacts to backend events pushed via SSE stream

## Backend Architectural Patterns

### API Gateway Pattern
```python
# Centralized routing and middleware
class APIGateway:
    def __init__(self):
        self.auth_middleware = AuthMiddleware()
        self.rate_limiter = RateLimiter()
        self.service_registry = ServiceRegistry()
    
    async def route_request(self, request: Request) -> Response:
        # Authentication, rate limiting, service discovery
        pass
```

### Service Layer Pattern
```python
# Business logic encapsulation
class NovelService:
    def __init__(self, novel_repo: NovelRepository, ai_service: AIService):
        self.novel_repo = novel_repo
        self.ai_service = ai_service
    
    async def generate_chapter(self, novel_id: str, prompt: str) -> Chapter:
        # Orchestrates data access and AI generation
        pass
```

### Observer Pattern for Events
```python
# Event-driven architecture
class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
    
    async def publish(self, event: Event):
        for handler in self.subscribers.get(event.type, []):
            await handler(event)
```

## Multi-Agent Coordination Patterns

### Agent Orchestration
- **Workflow Engine**: Prefect-based pipeline management
- **Agent Registry**: Dynamic agent discovery and capability matching
- **Context Passing**: Shared context object through agent pipeline
- **Error Handling**: Graceful failure and retry mechanisms

### Communication Patterns
```python
class AgentCoordinator:
    async def execute_novel_generation_workflow(self, context: GenerationContext):
        # Sequential agent execution with context accumulation
        context = await self.world_building_agent.process(context)
        context = await self.character_agent.process(context) 
        context = await self.plot_agent.process(context)
        context = await self.writing_agent.process(context)
        return context.result
```

## Data Architecture Patterns

### Multi-Database Strategy
- **PostgreSQL**: Transactional data (users, novels, chapters)
- **Redis**: Session management and caching
- **Neo4j**: Relationship modeling (character connections, plot threads)
- **Milvus**: Vector embeddings for semantic search and similarity

### CQRS (Command Query Responsibility Segregation)
```python
# Separate read and write models
class NovelCommand:
    async def create_novel(self, command: CreateNovelCommand) -> NovelId:
        # Write operations with full validation
        pass

class NovelQuery:
    async def get_novel_summary(self, novel_id: NovelId) -> NovelSummary:
        # Optimized read operations
        pass
```

### Event Sourcing (Future Pattern)
- **Event Store**: Immutable log of all domain events
- **Projection Building**: Read models built from events
- **Time Travel**: Ability to replay events to any point
- **Audit Trail**: Complete history of all changes

## Security Patterns

### JWT Authentication Pattern
```python
class AuthenticationService:
    async def authenticate_request(self, token: str) -> User:
        # JWT validation with Redis session checking
        payload = self.jwt_service.decode_token(token)
        session = await self.session_store.get_session(payload.session_id)
        return await self.user_service.get_user(payload.user_id)
```

### Authorization Pattern (RBAC)
```python
@requires_permission("novel.write")
async def create_chapter(user: User, novel_id: str, chapter_data: ChapterData):
    # Role-based access control with decorators
    pass
```

## Error Handling Patterns

### Result Pattern
```typescript
type Result<T, E = Error> = 
  | { success: true; data: T }
  | { success: false; error: E };

async function generateText(prompt: string): Promise<Result<string>> {
  try {
    const text = await aiService.generate(prompt);
    return { success: true, data: text };
  } catch (error) {
    return { success: false, error };
  }
}
```

### Circuit Breaker Pattern
```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int, timeout: int):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable):
        if self.state == "OPEN":
            raise CircuitBreakerOpenError()
        # Execute with failure tracking
```

## Development Patterns

### Test-Driven Development
- **Red-Green-Refactor**: Write failing test, implement, refactor
- **Test Pyramid**: Unit tests (many) > Integration tests > E2E tests (few)
- **Test Doubles**: Mocks, stubs, and fakes for isolation
- **Behavior-Driven Development**: Given-When-Then test structure

### Continuous Integration Patterns
- **Pipeline as Code**: GitHub Actions workflow definitions
- **Quality Gates**: Automated linting, testing, and security checks
- **Feature Toggles**: Runtime feature flag management
- **Blue-Green Deployment**: Zero-downtime deployment strategy

### Configuration Management
```python
class Settings:
    # Environment-based configuration
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL") 
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    
    class Config:
        env_file = ".env"
```

## Scalability Patterns

### Horizontal Scaling
- **Stateless Services**: No server-side session storage
- **Load Balancing**: Request distribution across instances
- **Database Sharding**: Data partitioning strategies
- **Cache-Aside**: Application-managed caching pattern

### Performance Optimization
- **Lazy Loading**: On-demand resource loading
- **Batch Processing**: Grouped operations for efficiency
- **Connection Pooling**: Reuse database connections
- **Async Processing**: Non-blocking I/O operations

## Update History
- 2025-08-28: Major update based on comprehensive architecture documentation
  - Added event-driven microservices architecture patterns
  - Added core implementation patterns (CQRS, Event Sourcing, Transactional Outbox, Command Inbox)
  - Added Pause and Resume workflow pattern for Prefect orchestration
  - Added comprehensive multi-agent coordination patterns with 10 specialized agents
  - Updated frontend patterns to reflect Zustand and TanStack Query usage
  - Added SSE integration and event-driven UI patterns