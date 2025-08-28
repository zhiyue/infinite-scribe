---
created: 2025-08-28T12:10:36Z
last_updated: 2025-08-28T12:10:36Z
version: 1.0
author: Claude Code PM System
---

# Technology Context

## Core Technology Stack

### Runtime Environments
- **Node.js**: >=20.0.0 (Frontend, Build Tools, Scripts)
- **Python**: 3.11 (Backend Services)
- **Package Managers**: pnpm ~8.15.0, uv (Python)

### Frontend Technology Stack
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite (fast development server and build)
- **State Management**: React Context/Hooks (extensible to Redux if needed)
- **UI Components**: Material-UI or similar design system
- **HTTP Client**: Fetch API or Axios
- **Routing**: React Router v6

### Backend Technology Stack
- **Framework**: FastAPI (async Python web framework)
- **Database ORM**: SQLAlchemy with Alembic migrations
- **Authentication**: JWT tokens with Redis session storage
- **API Documentation**: FastAPI automatic OpenAPI/Swagger
- **Testing**: pytest with comprehensive test suite
- **Async Support**: asyncio and async/await patterns

### Database Architecture
- **Primary Database**: PostgreSQL 15+ (relational data, user accounts, content)
- **Caching Layer**: Redis 7+ (sessions, caching, pub/sub)
- **Graph Database**: Neo4j (relationships, narrative structures)
- **Vector Database**: Milvus (AI embeddings, semantic search)
- **Object Storage**: MinIO (S3-compatible, files and media)

### AI & ML Integration
- **Text Generation**: OpenAI GPT models, Anthropic Claude
- **Embeddings**: OpenAI text-embedding models
- **Vector Storage**: Milvus for similarity search
- **AI Agent Framework**: Custom multi-agent coordination system
- **Workflow Orchestration**: Prefect for AI pipeline management

## Development Tools & Infrastructure

### Code Quality & Linting
- **TypeScript**: ~5.2.2 with strict mode
- **ESLint**: ^8.57.1 with React and accessibility plugins
- **Prettier**: ^3.6.2 for code formatting
- **Pre-commit Hooks**: Husky + lint-staged for automated quality checks

### Testing Framework
- **Frontend**: Jest, React Testing Library, Playwright (E2E)
- **Backend**: pytest with fixtures, async support, integration tests
- **Test Strategy**: Unit tests, integration tests, E2E automation

### Development Environment
- **Containerization**: Docker Compose for all services
- **Environment Management**: Multiple environments (local, dev, test, prod)
- **Service Discovery**: Docker networking with health checks
- **Development Scripts**: Unified parameterized command system

### Monitoring & Operations
- **Health Checks**: Comprehensive service health endpoints
- **Logging**: Structured logging across all services
- **Process Management**: Docker Compose orchestration
- **Deployment**: Multi-environment automated deployment

## Key Dependencies

### Frontend Core Dependencies
```json
{
  "react": "^18.x",
  "typescript": "~5.2.2",
  "vite": "^4.x",
  "react-router-dom": "^6.x"
}
```

### Backend Core Dependencies
```python
# Core framework
fastapi = "^0.104.0"
sqlalchemy = "^2.0.0"
alembic = "^1.12.0"

# Database drivers  
psycopg2-binary = "^2.9.0"
redis = "^5.0.0"

# Authentication & Security
python-jose = "^3.3.0"
passlib = "^1.7.4"
python-multipart = "^0.0.6"

# AI Integration
openai = "^1.0.0"
anthropic = "^0.8.0"
```

### Shared Development Dependencies
- **AWS SDK**: S3-compatible object storage access
- **Database Clients**: PostgreSQL, Redis, Neo4j, Milvus drivers
- **Development Tools**: dotenv, various CLI tools

## Architecture Patterns

### Microservices Architecture
- API Gateway pattern with service routing
- Independent service deployments
- Inter-service communication via HTTP/REST
- Shared database per service pattern (where appropriate)

### Event-Driven Components
- Redis pub/sub for real-time updates
- Async processing for AI generation tasks
- Workflow orchestration for complex multi-step processes

### Security & Authentication
- JWT-based stateless authentication
- Redis-backed session management  
- Role-based access control (RBAC)
- API rate limiting and throttling

## Integration Points

### External Services
- **AI Providers**: OpenAI, Anthropic API integration
- **Storage**: S3-compatible object storage (MinIO)
- **Search**: Vector similarity search via Milvus
- **Analytics**: Structured logging for future analytics integration

### Development Integrations
- **GitHub**: Repository, issues, CI/CD via Actions
- **Docker Hub/Registry**: Container image hosting
- **Deployment Targets**: Multi-environment server infrastructure

## Performance Considerations

### Frontend Optimization
- Code splitting with React lazy loading
- Bundle optimization with Vite
- Asset optimization and CDN-ready builds

### Backend Performance  
- Async/await for I/O operations
- Redis caching for frequently accessed data
- Database query optimization with SQLAlchemy
- Connection pooling for database efficiency

### Infrastructure Scaling
- Horizontal scaling capability for stateless services
- Database read replicas for scaling reads
- Redis clustering for session scaling
- Vector database sharding for AI workloads