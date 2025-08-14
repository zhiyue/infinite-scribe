# Testing Best Practices for Database Integration Tests

## Overview

This document outlines the best practices for writing database integration tests that work seamlessly across different environments (local development, CI/CD, staging).

## The Problem with Environment-Specific Test Code

Having environment detection logic directly in test code (like checking `if is_ci_environment()`) is an anti-pattern because:

1. **Violates Single Responsibility Principle**: Tests should focus on testing behavior, not managing environment differences
2. **Reduces Maintainability**: Environment-specific logic scattered throughout tests makes them harder to maintain
3. **Limits Flexibility**: Hard-coded environment checks don't allow for other scenarios (e.g., running tests against a staging database)

## Recommended Approach: Configuration-Based Testing

### 1. Use Environment Variables

Configure your tests through environment variables, not through code logic:

```bash
# Local development (uses testcontainers)
USE_EXTERNAL_SERVICES=false pytest

# CI environment (uses service containers)
USE_EXTERNAL_SERVICES=true pytest

# Testing against staging
USE_EXTERNAL_SERVICES=true \
POSTGRES_HOST=staging.example.com \
POSTGRES_PORT=5432 \
pytest
```

### 2. Centralize Configuration in Fixtures

Keep all environment-specific logic in `conftest.py` fixtures:

```python
@pytest.fixture(scope="session")
def postgres_service(use_external_services):
    """Provide PostgreSQL connection configuration."""
    if use_external_services:
        # Configuration from environment variables
        yield {
            "host": os.environ.get("POSTGRES_HOST", "localhost"),
            "port": int(os.environ.get("POSTGRES_PORT", "5432")),
            # ... other config
        }
    else:
        # Use testcontainers
        with PostgresContainer("postgres:16") as postgres:
            yield {
                "host": postgres.get_container_host_ip(),
                "port": postgres.get_exposed_port(5432),
                # ... other config
            }
```

### 3. Write Environment-Agnostic Tests

Tests should only care about the service configuration, not where it comes from:

```python
async def test_postgres_connection(postgres_service):
    """Test PostgreSQL connection - works in any environment."""
    config = postgres_service
    # Use config without caring if it's from testcontainers or external service
    postgres_url = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    # ... test logic
```

## Benefits of This Approach

1. **Separation of Concerns**: Tests focus on testing, fixtures handle environment configuration
2. **Flexibility**: Easy to add new environments or change configurations
3. **Maintainability**: All environment logic is in one place
4. **Reusability**: Same tests work everywhere without modification
5. **Explicit Configuration**: Clear what configuration is being used

## Alternative Approaches

### 1. Docker Compose for All Environments

Use docker-compose for both local and CI:

```yaml
# docker-compose.test.yml
version: '3.8'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: testpass
    ports:
      - "5432:5432"
```

**Pros**: Consistent environment everywhere  
**Cons**: Slower in CI, requires Docker-in-Docker

### 2. Separate Test Suites

Maintain separate test files for different environments:

```
tests/
  unit/
  integration_local/    # Uses testcontainers
  integration_ci/       # Uses external services
```

**Pros**: Clear separation  
**Cons**: Code duplication, maintenance overhead

### 3. Test Profiles

Use pytest markers and configuration files:

```python
@pytest.mark.local
async def test_with_testcontainers():
    # ...

@pytest.mark.ci
async def test_with_external_services():
    # ...
```

**Pros**: Flexible test selection  
**Cons**: Still has environment logic in tests

## Recommended Setup

### For New Projects

1. Use the configuration-based approach with fixtures
2. Keep all environment logic in `conftest.py`
3. Use environment variables for configuration
4. Document required environment variables

### For Existing Projects

1. Gradually refactor tests to use shared fixtures
2. Extract environment logic to fixtures
3. Replace direct environment checks with configuration
4. Update CI/CD pipelines to set appropriate environment variables

## CI/CD Configuration

### GitHub Actions Example

```yaml
- name: Run integration tests
  env:
    USE_EXTERNAL_SERVICES: true
    POSTGRES_HOST: localhost
    POSTGRES_PORT: 5432
    # ... other config
  run: |
    pytest tests/integration/
```

### GitLab CI Example

```yaml
test:
  variables:
    USE_EXTERNAL_SERVICES: "true"
    POSTGRES_HOST: postgres
  services:
    - postgres:16
  script:
    - pytest tests/integration/
```

## Conclusion

The best practice is to:

1. **Keep tests environment-agnostic**
2. **Use fixtures for environment-specific configuration**
3. **Configure through environment variables**
4. **Avoid environment detection in test code**

This approach ensures your tests are maintainable, flexible, and work consistently across all environments.