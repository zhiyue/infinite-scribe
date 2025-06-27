# Migration Example: From Environment-Specific to Configuration-Based Tests

## Before (Anti-Pattern) ❌

```python
# test_database_connections.py
def is_ci_environment():
    """Check if running in CI environment."""
    return os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"

@pytest.fixture
def postgres_container():
    if is_ci_environment():
        # CI-specific logic
        class CIPostgresContainer:
            @property
            def username(self):
                return os.environ.get("POSTGRES_USER", "postgres")
            # ... more CI-specific code
        yield CIPostgresContainer()
    else:
        # Local development logic
        with PostgresContainer("postgres:16") as postgres:
            yield postgres

async def test_postgres_connection(postgres_container):
    # Test has to handle different container types
    if hasattr(postgres_container, 'get_container_host_ip'):
        host = postgres_container.get_container_host_ip()
    else:
        host = 'localhost'
    # ... complex logic to handle differences
```

**Problems:**
- Environment detection logic in test code
- Complex fixture with multiple responsibilities
- Test needs to know about environment differences
- Hard to add new environments

## After (Best Practice) ✅

```python
# conftest.py (centralized configuration)
@pytest.fixture(scope="session")
def postgres_service(use_external_services):
    """Provide PostgreSQL connection configuration."""
    if use_external_services:
        yield {
            "host": os.environ.get("POSTGRES_HOST", "localhost"),
            "port": int(os.environ.get("POSTGRES_PORT", "5432")),
            "user": os.environ.get("POSTGRES_USER", "postgres"),
            "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
            "database": os.environ.get("POSTGRES_DB", "test_db"),
        }
    else:
        from testcontainers.postgres import PostgresContainer
        with PostgresContainer("postgres:16") as postgres:
            yield {
                "host": postgres.get_container_host_ip(),
                "port": postgres.get_exposed_port(5432),
                "user": postgres.username,
                "password": postgres.password,
                "database": postgres.dbname,
            }

# test_database_connections_clean.py (clean test code)
async def test_postgres_connection(postgres_service):
    """Test PostgreSQL connection - environment agnostic."""
    config = postgres_service
    postgres_url = f"postgresql+asyncpg://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    
    # Clean test logic without environment concerns
    service = PostgreSQLService()
    await service.connect(postgres_url)
    assert await service.check_connection() is True
```

**Benefits:**
- Clean separation of concerns
- Simple, readable tests
- Easy to add new environments
- Configuration is explicit and centralized

## Usage

### Local Development
```bash
# Uses testcontainers automatically
pytest tests/integration/

# Or explicitly
USE_EXTERNAL_SERVICES=false pytest tests/integration/
```

### CI Environment
```bash
# Uses service containers
USE_EXTERNAL_SERVICES=true \
POSTGRES_HOST=localhost \
POSTGRES_PORT=5432 \
pytest tests/integration/
```

### Testing Against Staging
```bash
# Uses staging database
USE_EXTERNAL_SERVICES=true \
POSTGRES_HOST=staging.db.company.com \
POSTGRES_PORT=5432 \
POSTGRES_USER=test_user \
POSTGRES_PASSWORD=test_pass \
pytest tests/integration/
```

## Key Principles

1. **Tests should be environment-agnostic**: They shouldn't know or care where the database comes from
2. **Configuration should be centralized**: All environment logic belongs in fixtures
3. **Use dependency injection**: Pass configuration as parameters, not through global state
4. **Make it explicit**: Use clear environment variables rather than magic detection

## Summary

The migration from environment-specific test code to configuration-based testing:

- ✅ Improves maintainability
- ✅ Increases flexibility
- ✅ Simplifies test code
- ✅ Follows SOLID principles
- ✅ Makes testing more reliable

This approach scales better as your project grows and needs to support more environments.