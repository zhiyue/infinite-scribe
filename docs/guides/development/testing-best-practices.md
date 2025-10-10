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
pytest

# Remote Docker for CI/CD (uses testcontainers on remote Docker)
USE_REMOTE_DOCKER=true \
REMOTE_DOCKER_HOST=tcp://192.168.2.202:2375 \
pytest
```

### 2. Centralize Configuration in Fixtures

Keep all testcontainer configuration logic in `conftest.py` fixtures:

```python
@pytest.fixture(scope="session")
def postgres_service():
    """Provide PostgreSQL testcontainer configuration."""
    # Always use testcontainers for consistent test environments
    from testcontainers.postgres import PostgresContainer

    postgres = None
    try:
        postgres = PostgresContainer("postgres:16")
        postgres.start()
        yield {
            "host": postgres.get_container_host_ip(),
            "port": postgres.get_exposed_port(5432),
            "user": postgres.username,
            "password": postgres.password,
            "database": postgres.dbname,
        }
    finally:
        if postgres:
            postgres.stop()
```

### 3. Write Testcontainer-Based Integration Tests

Integration tests should use testcontainer fixtures for reliable, isolated testing:

```python
async def test_postgres_connection(postgres_service):
    """Test PostgreSQL connection using testcontainer configuration."""
    config = postgres_service
    # Use testcontainer configuration for consistent test environment
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

### 2. Organized Test Structure

Maintain a clean separation between unit and integration tests:

```
tests/
  unit/           # Fast tests with mocked dependencies
  integration/    # Tests with real testcontainers
```

**Benefits**: 
- Clear separation of concerns
- Fast unit tests for development
- Reliable integration tests with real services

### 3. Test Categories

Use pytest markers for different test types:

```python
@pytest.mark.unit
async def test_business_logic():
    # Fast test with mocked dependencies
    pass

@pytest.mark.integration  
async def test_with_real_database(postgres_service):
    # Test with real testcontainer database
    pass
```

**Benefits**: 
- Flexible test selection (`pytest -m unit` for fast feedback)
- Consistent testcontainer usage for integration tests

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
  run: |
    # Tests automatically use testcontainers
    pytest tests/integration/
    
# Optional: Use remote Docker for testcontainers
- name: Run tests with remote Docker
  env:
    USE_REMOTE_DOCKER: true
    REMOTE_DOCKER_HOST: tcp://192.168.2.202:2375
  run: |
    pytest tests/integration/
```

### GitLab CI Example

```yaml
test:
  # Tests automatically use testcontainers  
  image: python:3.11
  services:
    - docker:dind  # Enable Docker-in-Docker for testcontainers
  variables:
    DOCKER_HOST: tcp://docker:2375
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