# CLAUDE.md - Contract Tests

Contract tests verify API interactions between our application (consumer) and
**external services** (providers) using Pact. Focus on **外部API合约校验** -
ensuring external service interfaces match our client expectations.

## Core Principles

### What to Test

- **Service availability** - Health checks and basic connectivity
- **Core business operations** - Primary API workflows your application depends
  on
- **Critical error scenarios** - Business logic failures that affect application
  flow
- **Data structure contracts** - Response/request schemas your code expects

### What NOT to Test

- **Infrastructure failures** (500, 503, network timeouts)
- **Performance characteristics** (latency, throughput)
- **Edge cases** (special characters, encoding, malformed data)
- **Resilience patterns** (retries, circuit breakers, rate limiting)

## Essential Patterns

### 1. Module Structure - Standard Pattern

```python
import pytest
from pact import match  # pact-python v3 (FFI)

from src.external.clients.errors import ExternalServiceError

pytestmark = [
    pytest.mark.contract,
    pytest.mark.pact_pair(provider="your-service-name"),
    pytest.mark.asyncio,
]
```

### 2. Basic Contract Test Structure

```python
async def test_core_operation_contract(pact, external_client_builder):
    """Test core business operation - HTTP_METHOD /endpoint."""

    (
        pact.upon_receiving("a request for core business operation")
        .given("Service is available and configured")
        .with_request("POST", "/api/operation")
        .with_header("Content-Type", match.regex("application/json", regex=r"^application/json(;.*)?$"), part="Request")
        .with_body({"parameter": "expected_value"}, part="Request")
        .will_respond_with(200)
        .with_header("Content-Type", match.regex("application/json", regex=r"^application/json(;.*)?$"))
        .with_body({"result": match.like("success"), "data": match.each_like({"id": 1}, min=1)})
    )

    with pact.serve() as srv:
        client = external_client_builder(str(srv.url))
        async with client.session():
            result = await client.perform_operation(parameter="expected_value")
            assert result
```

### 3. Health Check Pattern

```python
async def test_health_check_contract(pact, external_client_builder):
    """Test service availability - GET /health."""

    (
        pact.upon_receiving("a health check request")
        .given("Service is running")
        .with_request("GET", "/health")
        .will_respond_with(200)
        .with_header("Content-Type", match.regex("application/json", regex=r"^application/json(;.*)?$"))
        .with_body({
            "status": match.like("ok"),
            "timestamp": match.regex("2024-01-01T00:00:00Z", regex=r"^\d{4}-\d{2}-\d{2}T"),
        })
    )

    with pact.serve() as srv:
        client = external_client_builder(str(srv.url))
        async with client.session():
            assert await client.check_health() is True
```

### 4. Error Scenario Pattern

```python
async def test_business_error_contract(pact, external_client_builder):
    """Test business logic error handling."""

    (
        pact.upon_receiving("a request for non-existent resource")
        .given("Resource does not exist")
        .with_request("GET", "/api/resource/invalid-id")
        .will_respond_with(404)
        .with_header("Content-Type", match.regex("application/json", regex=r"^application/json(;.*)?$"))
        .with_body({"error": match.like("Resource not found"), "code": match.like("RESOURCE_NOT_FOUND")})
    )

    with pact.serve() as srv:
        client = external_client_builder(str(srv.url))
        async with client.session():
            with pytest.raises(ExternalServiceError):
                await client.get_resource("invalid-id")
```

### 5. Authentication Pattern

```python
async def test_authenticated_operation_contract(pact, external_client_builder):
    """Test operation requiring authentication."""

    (
        pact.upon_receiving("an authenticated request")
        .given("Valid API key is provided")
        .with_request("POST", "/api/secure-operation")
        .with_header("Authorization", match.regex("Bearer valid-token", regex=r"^Bearer .+"), part="Request")
        .with_header("Content-Type", match.regex("application/json", regex=r"^application/json(;.*)?$"), part="Request")
        .with_body({"action": "perform"}, part="Request")
        .will_respond_with(200)
        .with_body({"result": match.like("authorized"), "user_id": match.like(123)})
    )

    with pact.serve() as srv:
        client = external_client_builder(str(srv.url))
        async with client.session():
            result = await client.secure_operation("perform")
            assert result.get("result") == "authorized"
```

## Pact Matchers for External APIs

### Essential Matchers

- `match.like(value)` - 类型匹配（示例值）
- `match.regex(example, regex=...)` - 正则匹配
- `match.each_like(value, min=1)` - 数组元素匹配
- Content-Type 匹配：`match.regex("application/json", regex=r"^application/json(;.*)?$")`

### Common External API Patterns

```python
# API versioning in headers
"API-Version": match.regex("v1", regex=r"^v\d+$")

# Authentication tokens
"Authorization": match.regex("Bearer abc123", regex=r"^Bearer .+")

# Standard timestamps
"created_at": match.regex("2024-01-01T00:00:00Z", regex=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z$")

# UUID patterns
"id": match.regex("123e4567-e89b-12d3-a456-426614174000", regex=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

# Enum values
"status": match.regex("active", regex=r"^(active|inactive|pending)$")
```

## Client Session Management

**CRITICAL**: Always use proper session lifecycle with external clients:

```python
# ✅ Correct pattern (v3)
with pact.serve() as srv:
    client = external_client_builder(str(srv.url))
    async with client.session():
        result = await client.call_api()

# ❌ Wrong - missing session management / not using pact.serve()
with pact.serve() as srv:
    client = external_client_builder(str(srv.url))
    result = await client.call_api()  # May cause connection issues
```

## Testing External API Contracts

```bash
# Run all external API contract tests
pytest tests/contract/external/ -m contract -v

# Test specific external service
pytest tests/contract/external/clients/pact/consumer_tests/test_service_consumer.py -v

# Debug contract failures
pytest tests/contract/ -m contract -vv -s --tb=long

# Generate pact files for sharing with external teams
pytest tests/contract/external/ -m contract
# Check generated files in: tests/contract/external/clients/pact/pacts/
```

```bash
# 从 backend 目录运行（加载 v3 夹具与依赖）
cd apps/backend
uv run pytest tests/contract/external -m contract -v
```

## Best Practices for External APIs

### 1. Focus on Interface Contracts

- Test **what your client actually uses** from external APIs
- Validate **response structure** your code depends on
- Verify **error formats** that affect your business logic

### 2. Provider State Management

```python
# ✅ Good - realistic provider states
pact.given("User account exists and is active")
pact.given("API rate limit not exceeded")
pact.given("Service has required data available")

# ❌ Avoid - infrastructure states
pact.given("Database is running")
pact.given("Load balancer is healthy")
```

### 3. Error Contract Testing

```python
# Test business-relevant errors that your app handles
async def test_rate_limit_error_contract(pact, external_client):
    (pact.given("API rate limit exceeded")
     .upon_receiving("request when rate limited")
     .will_respond_with(429, body={"error": Like("Rate limit exceeded")}))
```

### 4. Contract Sharing

- Generated pact files can be shared with external service teams
- Use meaningful consumer/provider names
- Version your contracts with application releases

## Directory Structure

```
tests/contract/external/clients/pact/
├── consumer_tests/          # Your contract test files
│   ├── test_service_a_consumer.py
│   └── test_service_b_consumer.py
├── pacts/                   # Generated contract files for sharing
│   ├── your-app-service-a.json
│   └── your-app-service-b.json
└── conftest.py             # Shared fixtures and client builders
```

External API contract tests ensure **interface stability** and prevent breaking
changes from affecting your application.
