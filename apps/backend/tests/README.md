# Backend Tests

This directory contains tests for the backend application.

## Structure

```
tests/
├── unit/              # Unit tests (no external dependencies)
├── integration/       # Integration tests (may use external services)
├── conftest.py        # Shared fixtures and configuration
└── README.md          # This file
```

## Running Tests

### Local Development

```bash
# Run all tests (uses testcontainers for databases)
cd apps/backend
pytest

# Run only unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/
```

### Using External Services

You can run tests against external services (e.g., in CI or against remote databases):

```bash
# Set environment variable to use external services
USE_EXTERNAL_SERVICES=true \
POSTGRES_HOST=localhost \
POSTGRES_PORT=5432 \
POSTGRES_USER=postgres \
POSTGRES_PASSWORD=postgres \
POSTGRES_DB=test_db \
NEO4J_HOST=localhost \
NEO4J_PORT=7687 \
NEO4J_USER=neo4j \
NEO4J_PASSWORD=neo4jtest \
REDIS_HOST=localhost \
REDIS_PORT=6379 \
pytest tests/integration/
```

### Environment Configuration

- `.env.test` - Default test configuration (uses testcontainers)
- `.env.ci` - CI environment configuration (uses service containers)
- `.env.test.local` - Local overrides (gitignored)

## Test Architecture

Tests follow a clean architecture pattern:

1. **Tests are environment-agnostic**: They don't contain environment detection logic
2. **Configuration via fixtures**: All service configurations come from `conftest.py` fixtures
3. **Dependency injection**: Services receive configuration as parameters

Example:

```python
async def test_postgres_connection(postgres_service):
    """Test uses postgres_service fixture for configuration."""
    config = postgres_service
    # Test logic uses config without knowing the source
```

## Fixtures

Key fixtures defined in `conftest.py`:

- `postgres_service` - PostgreSQL connection configuration
- `neo4j_service` - Neo4j connection configuration  
- `redis_service` - Redis connection configuration
- `use_external_services` - Determines whether to use testcontainers or external services

## CI/CD Integration

GitHub Actions automatically runs tests with service containers:

1. Sets `USE_EXTERNAL_SERVICES=true`
2. Provides service containers (PostgreSQL, Neo4j, Redis)
3. Tests use these services instead of testcontainers

## Best Practices

1. Keep tests focused on behavior, not environment
2. Use fixtures for all external dependencies
3. Mock at the service boundary, not deep in the code
4. Write tests that work in all environments
5. Use clear, descriptive test names