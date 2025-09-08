# CLAUDE.md - Backend

This file provides guidance for Claude Code when working with the backend codebase.

## Backend Architecture

### Technology Stack

- **Framework**: FastAPI with Python 3.11
- **Database ORM**: SQLAlchemy 2.0 with typed relationships
- **Package Manager**: `uv` for dependency management
- **Code Quality**: Ruff (linting/formatting), mypy (type checking)
- **Testing**: pytest with **mandatory testcontainers** for all database integration tests

### Service Architecture

InfiniteScribe backend uses a unified service architecture with:

- **API Gateway** (`src/api/`): FastAPI application with authentication and routing
- **Agent Services** (`src/agents/`): AI agents for different novel writing tasks
- **Shared Services** (`src/common/services/`): Business logic services
- **External Clients** (`src/external/clients/`): External service adapters (Clean/Hexagonal architecture)
- **Database Layer** (`src/db/`): Multi-database connection management

### Directory Structure

```
apps/backend/src/
├── api/                    # FastAPI API Gateway
│   ├── main.py            # FastAPI app with lifespan management
│   ├── routes/            # API endpoints
│   │   ├── v1/           # Version 1 API routes
│   │   │   ├── auth*.py  # Authentication endpoints
│   │   │   └── ...
│   │   ├── health.py     # Health check endpoints
│   │   └── docs.py       # API documentation
│   └── schemas/          # API-specific Pydantic schemas
├── agents/                # AI Agent Services
│   ├── base.py           # Base agent class and utilities
│   ├── worldsmith/       # World building agent
│   ├── director/         # Story director agent
│   ├── writer/           # Writing agent
│   └── ...               # Other specialized agents
├── models/                # SQLAlchemy ORM Models
│   ├── base.py           # Base model with common fields
│   ├── user.py           # User authentication model
│   ├── novel.py          # Novel domain model
│   └── ...               # Other domain models
├── schemas/               # Pydantic Schemas (CQRS Pattern)
│   ├── base.py           # Base schema classes
│   ├── novel/            # Novel CRUD schemas
│   │   ├── create.py     # Creation DTOs
│   │   ├── read.py       # Read/Response DTOs
│   │   └── update.py     # Update DTOs
│   └── ...               # Other domain schemas
├── common/
│   ├── services/         # Business Logic Services
│   │   ├── jwt_service.py          # JWT token management
│   │   ├── user_service.py         # User business logic
│   │   ├── email_service.py        # Email service
│   │   ├── novel_service.py        # Novel business logic
│   │   └── ...                     # Other business services
│   └── utils/            # Shared utilities
├── external/             # External Service Clients (Clean/Hexagonal Architecture)
│   └── clients/          # External service adapters
│       ├── base_http.py       # Base HTTP client with retry/monitoring
│       ├── errors.py          # Exception definitions for external services
│       ├── embedding_client.py # Embedding API client
│       └── __init__.py        # Unified exports
├── db/                   # Database Infrastructure Layer
│   ├── sql/              # PostgreSQL connections & services
│   │   └── service.py    # PostgreSQL connection service
│   ├── redis/            # Redis connections & services
│   │   └── service.py    # Redis connection service
│   ├── graph/            # Neo4j connections & services
│   │   └── service.py    # Neo4j connection service
│   └── vector/           # Vector database connections
├── middleware/           # FastAPI middleware
└── core/                 # Core configuration
    ├── config.py         # Settings management
    └── toml_loader.py    # TOML configuration loader
```

## Development Commands

### Local Development

```bash
# Start API Gateway
uv run uvicorn src.api.main:app --reload --port 8000

# Start specific agent service
SERVICE_TYPE=agent-worldsmith python -m src.agents.worldsmith.main

# Alternative service starter
uv run python -m src.agents.main --agent-type worldsmith
```

### Code Quality

```bash
# Lint and format code
uv run ruff check src/              # Check for issues
uv run ruff format src/             # Format code
uv run ruff check --fix src/        # Fix auto-fixable issues

# Type checking
uv run mypy src/ --ignore-missing-imports

# Run all quality checks
make backend-lint && make backend-format && make backend-typecheck
```

### Testing

```bash
# Unit tests only (fast) - with timeout to prevent hanging
timeout 5 uv run pytest tests/unit/ -v

# Integration tests (requires Docker services) - with longer timeout
timeout 30 uv run pytest tests/integration/ -v

# All tests - with comprehensive timeout
timeout 60 uv run pytest tests/ -v

# Coverage report - with timeout
timeout 60 uv run pytest tests/ --cov=src --cov-report=html

# Test specific module - with timeout
timeout 10 uv run pytest tests/unit/services/test_user_service.py -v

# Alternative: Using pytest timeout plugin (install with: uv add pytest-timeout)
uv run pytest tests/ -v --timeout=300 --timeout-method=thread
```

**Important**: Always use timeouts when running tests to:
- Prevent infinite loops in test code
- Avoid long-hanging tests that mask real issues
- Prevent memory leaks from stuck processes
- Enable faster feedback during development
- Ensure CI/CD pipelines don't hang indefinitely

**Timeout Guidelines**:
- Unit tests: 5-10 seconds (should be very fast)
- Integration tests: 30-60 seconds (involve database/external services)
- Full test suite: 60-120 seconds (depending on test count)
- Individual test modules: 10-30 seconds (based on complexity)

### Database Management

```bash
# Create new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Check migration status
alembic current

# Rollback migration
alembic downgrade -1

# Reset database (development only)
alembic downgrade base && alembic upgrade head
```

## Code Patterns & Conventions

### 1. Service Layer Pattern

Business logic lives in `common/services/`. Services are dependency-injected into API routes.

```python
# Good: Service with clear dependencies
class UserService:
    def __init__(self, postgres: PostgresService, redis: RedisService):
        self.postgres = postgres
        self.redis = redis

    async def create_user(self, user_data: UserCreate) -> User:
        # Business logic here
        pass

# Usage in API route
@router.post("/users")
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.create_user(user_data)
```

### 2. CQRS Schema Pattern

Separate schemas for Create, Read, and Update operations:

```python
# schemas/user/create.py
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

# schemas/user/read.py
class UserRead(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

# schemas/user/update.py
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
```

### 3. Database Models

Use SQLAlchemy 2.0 style with typed relationships:

```python
class User(BaseModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)

    # Typed relationships
    sessions: Mapped[list[Session]] = relationship(back_populates="user")
```

### 4. Error Handling

Use FastAPI's HTTPException with consistent error responses:

```python
from fastapi import HTTPException, status

# Service layer
class UserService:
    async def get_user(self, user_id: int) -> User:
        user = await self.postgres.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
```

### 5. Authentication Pattern

JWT tokens with Redis session management:

```python
# Protected route
@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user.to_dict()

# Service method
async def authenticate_user(self, token: str) -> User:
    # Validate JWT and check Redis session
    # Return user or raise authentication error
```

### 6. Datetime Handling

Always use timezone-aware datetime objects to avoid deprecation warnings:

```python
from datetime import datetime, timezone,UTC

# Good: Timezone-aware UTC datetime
def get_current_utc_time() -> datetime:
    return datetime.now(UTC)

# Good: In database models
class User(BaseModel):
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )

# Bad: Deprecated datetime.utcnow()
# created_at = datetime.utcnow()  # Don't use this

# Good: For JWT token expiration
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(hours=1)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

## Agent Development

### Base Agent Pattern

All agents inherit from `BaseAgent`:

```python
from src.agents.base import BaseAgent

class WorldsmithAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_type="worldsmith")

    async def process_request(self, request: WorldBuildingRequest) -> WorldBuildingResponse:
        # Agent-specific logic
        pass
```

### Agent Service Structure

```
agents/worldsmith/
├── __init__.py
├── main.py           # Service entry point
├── agent.py          # Agent implementation
├── schemas.py        # Agent-specific schemas
└── prompts/          # LLM prompts (if applicable)
```

### Running Agents

```bash
# Development mode
SERVICE_TYPE=agent-worldsmith python -m src.agents.worldsmith.main

# Production mode (with proper service discovery)
python -m src.agents.main --agent-type worldsmith --port 8001
```

## Testing Strategy

### 1. Unit Tests

Test individual functions and classes in isolation:

```python
# tests/unit/services/test_user_service.py
@pytest.mark.asyncio
async def test_create_user():
    # Mock dependencies
    mock_postgres = Mock()
    mock_redis = Mock()

    user_service = UserService(mock_postgres, mock_redis)

    # Test business logic
    result = await user_service.create_user(user_data)
    assert result.username == user_data.username
```

### 2. Integration Tests

**MANDATORY**: All integration tests involving databases MUST use testcontainers. Never use real external databases or mocked database connections for integration tests.

```python
# tests/integration/test_user_endpoints.py
@pytest.mark.integration
async def test_create_user_endpoint(test_client, test_db):
    response = test_client.post("/api/v1/users", json=user_data)
    assert response.status_code == 201

    # Verify in database (using testcontainer)
    user = await test_db.get_user_by_email(user_data["email"])
    assert user is not None
```

**Why testcontainers are required**:
- Ensures tests run against real database behavior
- Prevents inconsistencies between mocked and actual database responses
- Provides isolation between test runs
- Catches database-specific issues (constraints, transactions, etc.)

### 3. Test Configuration

Use `conftest.py` for shared testcontainer fixtures. **All database fixtures MUST use testcontainers**:

```python
# tests/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
async def postgres_container():
    """PostgreSQL testcontainer for integration tests."""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture(scope="session")
async def redis_container():
    """Redis testcontainer for integration tests."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis

@pytest.fixture
async def test_db(postgres_container):
    """Database session using testcontainer."""
    # Setup database session from container
    # Return session for tests
    # Cleanup automatically handled by testcontainer
```

**Testcontainer Requirements**:
- Use appropriate container versions matching production
- Clean up containers automatically after tests
- Isolate each test with fresh database state
- Never use real external database connections in tests

## Configuration Management

### Settings Pattern

Use Pydantic settings with environment variables:

```python
# core/config.py
class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret_key: str

    class Config:
        env_file = ".env"

settings = Settings()
```

### TOML Configuration

For complex configurations, use TOML files:

```python
# core/toml_loader.py - Load structured configuration
config = load_toml_config("config.toml")
```

## External Service Integration

### External Client Pattern

External service clients follow Clean/Hexagonal architecture principles:

```python
# src/external/clients/my_service_client.py
from .base_http import BaseHttpClient
from .errors import ServiceValidationError, handle_http_error

class MyServiceClient(BaseHttpClient):
    def __init__(self, base_url: str = None):
        super().__init__(base_url or settings.my_service_url)
    
    async def call_api(self, data: dict) -> dict:
        try:
            response = await self.post("/api/endpoint", json_data=data)
            return response.json()
        except httpx.HTTPStatusError as e:
            raise handle_http_error("MyService", e) from e
```

### Best Practices

- **Inherit from BaseHttpClient** for consistent retry/timeout/monitoring
- **Use structured error handling** with service-specific exceptions
- **Implement health checks** for service discovery
- **Create module-level instances** for backward compatibility
- **Follow naming convention**: `{Service}Client` class, `{service}_client` instance

### Testing Strategy

1. **Unit Tests**: Mock HTTP responses, test logic/error handling
2. **Integration Tests**: Use testcontainers or real service endpoints 
3. **Contract Tests**: Validate API contracts remain compatible

### Adding New External Client

1. Create client class inheriting from `BaseHttpClient`
2. Implement service-specific methods with proper error handling
3. Add exports to `src/external/clients/__init__.py`
4. Write comprehensive unit tests
5. Consider integration tests for critical services

## Common Development Tasks

### Adding New API Endpoint

1. Create route in `src/api/routes/v1/`
2. Define schemas in `src/schemas/`
3. Implement business logic in `src/common/services/`
4. Add tests in `tests/unit/api/` and `tests/integration/api/` (**use testcontainers for integration tests**)
5. Update API documentation

### Adding New Database Model

1. Create model in `src/models/`
2. Create migration: `alembic revision --autogenerate -m "add model"`
3. Apply migration: `alembic upgrade head`
4. Create corresponding schemas
5. Add service methods
6. Write tests (**integration tests MUST use testcontainers**)

### Adding New Agent

1. Create agent directory in `src/agents/`
2. Implement agent class inheriting from `BaseAgent`
3. Create `main.py` for service entry point
4. Define agent-specific schemas
5. Add agent configuration
6. Write agent tests
7. Update agent launcher

### Database Migration Workflow

1. Make model changes
2. Generate migration: `alembic revision --autogenerate`
3. Review generated migration file
4. Test migration: `alembic upgrade head`
5. Test rollback: `alembic downgrade -1`
6. Commit migration with code changes

## Debugging & Troubleshooting

### Common Issues

1. **Import errors**: Check Python path and virtual environment
2. **Database connection**: Verify services are running (`pnpm check services`)
3. **Migration conflicts**: Use `alembic merge` for branch conflicts
4. **Test failures**: Ensure test database is clean between runs
5. **Testcontainer issues**:
   - Docker daemon not running: Start Docker Desktop or Docker service
   - Permission errors: Ensure user is in docker group (Linux)
   - Port conflicts: Let testcontainers auto-assign ports
   - Container startup timeouts: Increase timeout in test configuration
   - Memory issues: Ensure sufficient Docker memory allocation

### Logging

```python
import logging
logger = logging.getLogger(__name__)

# In service methods
logger.info(f"Creating user: {user_data.username}")
logger.error(f"Failed to create user: {error}")
```

### Performance Monitoring

- Use FastAPI's built-in request timing
- Monitor database query performance
- Track agent response times
- Use `pytest-benchmark` for performance tests

## Security Considerations

### Authentication & Authorization

- JWT tokens with short expiration
- Redis session storage for token management
- Rate limiting on authentication endpoints
- Input validation using Pydantic

### Database Security

- Use parameterized queries (SQLAlchemy handles this)
- No sensitive data in logs
- Encrypt sensitive fields if needed
- Regular security updates

### API Security

- CORS configuration in `src/api/main.py`
- Input sanitization through Pydantic
- No secrets in code (use environment variables)
- Rate limiting middleware
