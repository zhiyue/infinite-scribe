# Backend Tests

This directory contains tests for the backend application.

## Structure

```
tests/
├── unit/              # Unit tests (no external dependencies)
├── integration/       # Integration tests (use testcontainers)
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

# Run integration tests (requires Docker)
pytest tests/integration/
```

### Remote Docker Support

For CI/CD environments, you can use remote Docker:

```bash
# Use remote Docker host for testcontainers
USE_REMOTE_DOCKER=true \
REMOTE_DOCKER_HOST=tcp://192.168.2.202:2375 \
pytest tests/integration/
```

### Environment Configuration

- `.env.test` - Default test configuration (uses testcontainers)
- `.env.test.local` - Local overrides (gitignored)

## Test Architecture

Tests follow a clean testcontainer architecture:

1. **Testcontainers for all integration tests**: All external services use Docker containers
2. **Configuration via fixtures**: All service configurations come from `conftest.py` fixtures
3. **Dependency injection**: Services receive testcontainer configuration as parameters

Example:

```python
async def test_postgres_connection(postgres_service):
    """Test uses postgres_service fixture for testcontainer configuration."""
    config = postgres_service  # Contains testcontainer host/port/credentials
    # Test logic uses testcontainer without environment-specific logic
```

## Fixtures

Key fixtures defined in `conftest.py`:

- `postgres_service` - PostgreSQL testcontainer configuration
- `neo4j_service` - Neo4j testcontainer configuration  
- `redis_service` - Redis testcontainer configuration
- `kafka_service` - Kafka testcontainer configuration
- `milvus_service` - Milvus testcontainer configuration

## CI/CD Integration

CI/CD environments can use remote Docker for testcontainers:

1. Set `USE_REMOTE_DOCKER=true`
2. Configure `REMOTE_DOCKER_HOST` to point to Docker daemon
3. All tests use testcontainers via remote Docker

## Best Practices

1. Keep tests focused on behavior, not infrastructure
2. Use testcontainer fixtures for all external dependencies
3. Mock at the service boundary, not deep in the code
4. Ensure Docker is available for integration tests
5. Use clear, descriptive test names
6. Clean up containers after tests (handled automatically by testcontainers)

## Requirements

- Docker daemon running (local or remote)
- `testcontainers` Python package
- Sufficient Docker resources for parallel containers