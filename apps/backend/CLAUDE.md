# CLAUDE.md - Backend

This file provides guidance for Claude Code when working with the backend codebase.

## Backend Architecture

### Technology Stack

- **Framework**: FastAPI with Python 3.11
- **Database ORM**: SQLAlchemy 2.0 with typed relationships
- **Package Manager**: `uv` for dependency management
- **Code Quality**: Ruff (linting/formatting), mypy (type checking)
- **Testing**: pytest with testcontainers for integration tests

### Service Architecture

InfiniteScribe backend uses a unified service architecture with:

- **API Gateway** (`src/api/`): FastAPI application with authentication and routing
- **Agent Services** (`src/agents/`): AI agents for different novel writing tasks
- **Shared Services** (`src/common/services/`): Business logic and external integrations
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
│   │   ├── postgres_service.py     # PostgreSQL connection
│   │   ├── redis_service.py        # Redis cache/sessions
│   │   ├── neo4j_service.py        # Neo4j graph database
│   │   ├── jwt_service.py          # JWT token management
│   │   ├── user_service.py         # User business logic
│   │   └── ...                     # Other services
│   └── utils/            # Shared utilities
├── db/                   # Database Infrastructure
│   ├── sql/              # PostgreSQL connections
│   ├── graph/            # Neo4j connections
│   └── vector/           # Vector database (future)
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
# Unit tests only (fast)
uv run pytest tests/unit/ -v

# Integration tests (requires Docker services)
uv run pytest tests/integration/ -v

# All tests
uv run pytest tests/ -v

# Coverage report
uv run pytest tests/ --cov=src --cov-report=html

# Test specific module
uv run pytest tests/unit/services/test_user_service.py -v
```

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

Test with real database connections using testcontainers:

```python
# tests/integration/test_user_endpoints.py
@pytest.mark.integration
async def test_create_user_endpoint(test_client, test_db):
    response = test_client.post("/api/v1/users", json=user_data)
    assert response.status_code == 201

    # Verify in database
    user = await test_db.get_user_by_email(user_data["email"])
    assert user is not None
```

### 3. Test Configuration

Use `conftest.py` for shared test fixtures:

```python
# tests/conftest.py
@pytest.fixture
async def test_db():
    # Setup test database container
    # Return database session
    # Cleanup after test
```

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

## Common Development Tasks

### Adding New API Endpoint

1. Create route in `src/api/routes/v1/`
2. Define schemas in `src/schemas/`
3. Implement business logic in `src/common/services/`
4. Add tests in `tests/unit/api/` and `tests/integration/api/`
5. Update API documentation

### Adding New Database Model

1. Create model in `src/models/`
2. Create migration: `alembic revision --autogenerate -m "add model"`
3. Apply migration: `alembic upgrade head`
4. Create corresponding schemas
5. Add service methods
6. Write tests

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
