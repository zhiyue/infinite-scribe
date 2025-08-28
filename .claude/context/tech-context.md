---
created: 2025-08-28T12:10:36Z
last_updated: 2025-08-28T12:24:28Z
version: 1.1
author: Claude Code PM System
---

# Technology Context

## Complete Technology Stack

Based on comprehensive architecture documentation, InfiniteScribe uses a sophisticated multi-component tech stack optimized for AI-powered novel generation through event-driven multi-agent systems.

### Runtime Environments
- **Node.js**: >=20.0.0 (Frontend, Build Tools, Scripts)
- **Python**: ~3.11 (Backend Services, AI Agents)
- **Package Managers**: pnpm ~8.15.0, uv (Python dependency management)

### Frontend Technology Stack
- **Framework**: React ~18.2.0 with TypeScript ~5.2.2
- **Build Tool**: Vite ~5.2.0 (fast development server and optimized builds)
- **UI Components**: Shadcn UI ~0.8.0 (highly customizable headless components)
- **State Management**: Zustand ~4.5.0 (lightweight, hooks-based global state)
- **Data Fetching**: TanStack Query ~5.25.0 (server state management and caching)
- **Routing**: React Router ~6.22.0 (client-side routing)
- **CSS Framework**: Tailwind CSS ~3.4.1 (atomic CSS with Shadcn UI integration)

### Backend Core Architecture
- **Framework**: FastAPI ~0.115.13 (high-performance async API framework)
- **Data Validation**: Pydantic ~2.11.7 (runtime type enforcement and validation)
- **Database ORM**: SQLAlchemy with Alembic migrations
- **API Documentation**: FastAPI automatic OpenAPI/Swagger generation

### Event-Driven Architecture Components
- **Event Bus**: Apache Kafka 3.7.0 (high-throughput distributed messaging)
- **Workflow Orchestration**: Prefect ~2.19.0 (Python-native workflow management)
- **Message Patterns**: Transactional Outbox, Command Inbox, Event Sourcing
- **Communication**: Asynchronous event-driven microservices communication

### Multi-Database Architecture
- **Primary Database**: PostgreSQL 16 (core metadata, domain events, command inbox)
  - Tables: command_inbox, domain_events, event_outbox, flow_resume_handles
  - CQRS state snapshots and transactional consistency
- **Caching Layer**: Redis 7.2 (sessions, callback handles, temporary data)
- **Graph Database**: Neo4j 5.x (project-level worldview and character relationships)
- **Vector Database**: Milvus 2.4.0 (context retrieval and semantic search)
- **Object Storage**: MinIO LATEST (S3-compatible, novel content storage)

### AI & ML Integration Stack
- **LLM Gateway**: LiteLLM ~1.34.0 (unified multi-provider API with cost control)
- **AI Observability**: Langfuse ~2.25.0 (LLM application tracing and debugging)
- **Model Providers**: OpenAI, Anthropic, and other LLM providers via LiteLLM
- **Multi-Agent System**: 10 specialized AI agents (Worldsmith, PlotMaster, etc.)
- **Context Management**: Vector embeddings and graph-based knowledge persistence

## Development Tools & Infrastructure

### Code Quality & Linting
- **TypeScript**: ~5.2.2 with strict mode
- **ESLint**: ^8.57.1 with React and accessibility plugins
- **Prettier**: ^3.6.2 for code formatting
- **Pre-commit Hooks**: Husky + lint-staged for automated quality checks

### Testing Framework
- **Frontend**: Vitest ~1.4.0, React Testing Library, Playwright (E2E)
- **Backend**: pytest ~8.1.0 with fixtures, async support, integration tests
- **Test Strategy**: Unit tests, integration tests, E2E automation

### Development Environment
- **Containerization**: Docker Compose for all services
- **Repository Structure**: Monorepo with pnpm workspaces
- **Environment Management**: Multiple environments (local, dev, test, prod)
- **Service Discovery**: Docker networking with health checks
- **Development Scripts**: Unified parameterized command system

### Backend Unified Architecture
- **Single Codebase**: All backend services in apps/backend/
- **Shared Dependencies**: Single pyproject.toml for all Python dependencies
- **Service Selection**: SERVICE_TYPE environment variable determines running service
- **Deployment**: Single Docker image, multiple service instances

## Key Dependencies

### Frontend Core Dependencies
```json
{
  "react": "~18.2.0",
  "typescript": "~5.2.2", 
  "vite": "~5.2.0",
  "react-router-dom": "~6.22.0",
  "zustand": "~4.5.0",
  "@tanstack/react-query": "~5.25.0",
  "tailwindcss": "~3.4.1"
}
```

### Backend Core Dependencies
```python
# Core framework
fastapi = "~0.115.13"
pydantic = "~2.11.7"
sqlalchemy = "^2.0.0"
alembic = "^1.12.0"

# Event-driven architecture
prefect = "~2.19.0"
kafka-python = "^2.0.0"

# Database drivers  
psycopg2-binary = "^2.9.0"
redis = "^7.2.0"
neo4j = "^5.0.0"
pymilvus = "^2.4.0"

# AI Integration
litellm = "~1.34.0"
langfuse = "~2.25.0"
openai = "^1.0.0"
anthropic = "^0.8.0"

# Testing
pytest = "~8.1.0"
vitest = "~1.4.0"
```

### Container Images
- **Apache Kafka**: 3.7.0
- **PostgreSQL**: 16
- **Redis**: 7.2
- **Neo4j**: 5.x (latest stable)
- **Milvus**: 2.4.0
- **MinIO**: LATEST

## Architecture Patterns

### Event-Driven Microservices Architecture
- **Pattern**: Event-driven microservices with Kafka as the central event bus
- **API Gateway**: Single entry point for all frontend requests via FastAPI
- **Service Communication**: Async messaging through Kafka, avoiding direct service calls
- **Service Types**: API Gateway, Message Relay, Prefect Orchestrator, Callback Service, AI Agents

### Core Implementation Patterns
- **CQRS (Command Query Responsibility Segregation)**: Strict separation of write operations (commands) and read operations (queries)
- **Event Sourcing**: domain_events table as single source of truth for all state changes
- **Transactional Outbox**: event_outbox table ensures atomic writes and reliable message publishing
- **Command Inbox**: command_inbox table provides idempotent command processing
- **Pause and Resume Workflow**: Prefect workflows can pause and resume based on external events

### Multi-Agent System Architecture
- **Specialized Agents**: 10 distinct agent types (Worldsmith, PlotMaster, Outliner, Director, etc.)
- **Agent Coordination**: Kafka-based async communication with Prefect orchestration
- **Knowledge Persistence**: Multi-database approach (PostgreSQL, Neo4j, Milvus, MinIO)
- **Context Management**: Vector embeddings and graph relationships for narrative consistency

## Integration Points

### External Services
- **LLM Providers**: OpenAI, Anthropic, and other providers via LiteLLM gateway
- **AI Observability**: Langfuse for LLM application tracing and cost monitoring
- **Storage**: S3-compatible object storage (MinIO) for novel content and media
- **Vector Search**: Milvus for semantic similarity and context retrieval

### Development Integrations
- **Version Control**: GitHub with conventional commit messages
- **CI/CD**: GitHub Actions with automated testing and deployment
- **Container Registry**: Docker Hub/Registry for service images
- **Deployment**: Multi-environment server infrastructure (dev: 192.168.2.201, test: 192.168.2.202)

### Service Endpoints (Development Server)
- **PostgreSQL**: 192.168.2.201:5432
- **Redis**: 192.168.2.201:6379  
- **Neo4j**: 192.168.2.201:7474 (Browser), 192.168.2.201:7687 (Bolt)
- **Kafka**: 192.168.2.201:9092
- **Milvus**: 192.168.2.201:19530
- **MinIO**: 192.168.2.201:9000 (API), 192.168.2.201:9001 (Console)
- **Prefect**: 192.168.2.201:4200

## Performance Considerations

### Frontend Optimization
- Code splitting with React lazy loading and Suspense
- Bundle optimization with Vite's tree-shaking and chunking
- TanStack Query for intelligent data caching and background updates
- Asset optimization and CDN-ready builds

### Backend Performance  
- Async/await for I/O operations across all services
- Redis caching for callback handles and frequently accessed data
- Event-driven architecture reduces blocking operations
- Connection pooling for database efficiency across all data stores

### AI Processing Optimization
- LiteLLM for cost optimization and provider load balancing
- Langfuse for performance monitoring and token usage tracking
- Vector database sharding for large-scale embedding storage
- Batch processing for non-critical AI operations

## Update History
- 2025-08-28: Added complete architecture stack from comprehensive documentation including event-driven patterns, multi-agent system details, and specific technology versions