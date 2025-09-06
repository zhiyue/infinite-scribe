# OutboxRelayService Tests

This document describes the comprehensive test suite for the OutboxRelayService, which implements the Transactional Outbox Pattern for reliable event publishing from database to Kafka.

## Test Structure

### 1. Unit Tests (`tests/unit/services/test_outbox_relay_service.py`)
- **Mocked Dependencies**: All external dependencies (Kafka, Database) are mocked
- **Focused Testing**: Tests individual methods and logic paths in isolation
- **Fast Execution**: No external service dependencies, suitable for CI/CD
- **Coverage**: Configuration validation, error handling, retry logic, producer lifecycle

**Key Test Categories:**
- Configuration validation with various invalid settings
- Service lifecycle (start/stop) with different scenarios
- Message processing success and failure paths
- Exponential backoff calculations and overflow protection
- Row locking and database query logic
- Producer availability and shutdown scenarios
- JSON serialization and header encoding edge cases

### 2. Integration Tests (`tests/integration/test_outbox_relay_service.py`)
- **Testcontainers Database**: Uses real PostgreSQL via testcontainers (Docker)
- **Mocked Kafka**: Kafka producer is mocked but with realistic behavior  
- **End-to-End Flows**: Tests complete message processing pipelines
- **Database State Verification**: Verifies actual database state changes in testcontainer

### 3. Real Kafka Integration Tests (`tests/integration/test_outbox_relay_with_kafka.py`)
- **Full Testcontainers**: Uses both real PostgreSQL and Kafka via testcontainers
- **Real Kafka Producer/Consumer**: Actual Kafka message publishing and consumption
- **Complete E2E Verification**: Verifies messages are actually sent to and received from Kafka
- **Production-like Testing**: Most realistic testing environment

**Key Test Scenarios:**
- Single and multiple message processing
- Retry logic with real database state transitions
- Scheduled message processing timing
- Race condition prevention between processing phases
- Complex JSON payload and header handling
- Batch size limiting and processing order
- Graceful shutdown during active processing

**Key Test Scenarios:**
- Single and multiple message processing with real Kafka verification
- Large payload handling through Kafka
- Message headers transmission and encoding
- Scheduled message processing with timing verification
- End-to-end producer configuration validation
- Graceful shutdown during Kafka operations

### 4. Concurrency Tests (`tests/integration/test_outbox_relay_concurrency.py`)
- **High Concurrency**: Multiple concurrent workers processing simultaneously
- **Real Kafka Verification**: Some tests use actual Kafka containers for verification
- **Race Condition Testing**: Verifies SKIP LOCKED prevents duplicate processing
- **Performance Under Load**: Tests behavior with high message volumes
- **Failure Resilience**: Worker failures don't affect other concurrent workers

**Key Concurrency Scenarios:**
- Multiple workers with no message duplication (verified via real Kafka)
- Variable processing times with high concurrency
- Worker failures during concurrent processing
- Race conditions between immediate and scheduled messages
- Database deadlock prevention
- Graceful shutdown under high load
- Memory efficiency with large payloads

## Running the Tests

### Prerequisites
```bash
# Ensure services are running
pnpm check services

# Install test dependencies  
cd apps/backend
uv sync
```

### Unit Tests (Fast - No External Dependencies)
```bash
# Run all unit tests
timeout 10 uv run pytest tests/unit/services/test_outbox_relay_service.py -v

# Run specific test categories
timeout 10 uv run pytest tests/unit/services/test_outbox_relay_service.py::TestOutboxRelayService::test_init_valid_settings -v

# Run with coverage
timeout 15 uv run pytest tests/unit/services/test_outbox_relay_service.py --cov=src.services.outbox.relay --cov-report=html -v
```

### Integration Tests (Require Database)
```bash
# Run all integration tests (mocked Kafka)
timeout 30 uv run pytest tests/integration/test_outbox_relay_service.py -v -m integration

# Run specific integration test
timeout 30 uv run pytest tests/integration/test_outbox_relay_service.py::TestOutboxRelayServiceIntegration::test_single_message_processing_success -v

# Run with database cleanup verification
timeout 30 uv run pytest tests/integration/test_outbox_relay_service.py -v --tb=short
```

### Real Kafka Integration Tests (Require Database + Kafka)
```bash
# Run all real Kafka tests (most comprehensive)
timeout 60 uv run pytest tests/integration/test_outbox_relay_with_kafka.py -v -m integration

# Run specific real Kafka test
timeout 60 uv run pytest tests/integration/test_outbox_relay_with_kafka.py::TestOutboxRelayServiceRealKafka::test_single_message_end_to_end_kafka -v

# Run end-to-end verification tests only
timeout 60 uv run pytest tests/integration/test_outbox_relay_with_kafka.py -k "end_to_end" -v
```

### Concurrency Tests (High Load Testing)
```bash
# Run concurrency tests
timeout 60 uv run pytest tests/integration/test_outbox_relay_concurrency.py -v -m integration

# Run specific concurrency scenario
timeout 60 uv run pytest tests/integration/test_outbox_relay_concurrency.py::TestOutboxRelayServiceConcurrency::test_multiple_concurrent_workers_no_duplication -v
```

### All OutboxRelay Tests
```bash
# Run complete test suite (without real Kafka)
timeout 90 uv run pytest tests/unit/services/test_outbox_relay_service.py tests/integration/test_outbox_relay_service.py tests/integration/test_outbox_relay_concurrency.py -v

# Run complete test suite INCLUDING real Kafka tests (comprehensive)
timeout 120 uv run pytest tests/unit/services/test_outbox_relay_service.py tests/integration/test_outbox_relay*.py -v

# Run with parallel execution (if pytest-xdist is installed) - excludes Kafka tests for stability
timeout 90 uv run pytest tests/unit/services/test_outbox_relay_service.py tests/integration/test_outbox_relay_service.py tests/integration/test_outbox_relay_concurrency.py -v -n auto

# Production-Ready Test Suite (recommended for CI/CD)
timeout 120 uv run pytest tests/integration/test_outbox_relay_with_kafka.py -v -m integration
```

## Test Configuration

### Environment Variables
```bash
# All tests use testcontainers (default)
# No configuration needed for local Docker

# For remote Docker testing with testcontainers
export USE_REMOTE_DOCKER=true
export REMOTE_DOCKER_HOST="tcp://192.168.2.202:2375"
```

### Testcontainer Architecture

**All tests use testcontainers**:
- ✅ **Complete Isolation**: Each test run gets fresh database and Kafka containers
- ✅ **Consistency**: Same PostgreSQL and Kafka versions across all environments
- ✅ **No Conflicts**: No interference with local service instances
- ✅ **CI/CD Ready**: Works in CI environments without external service setup
- ✅ **Real Integration**: Tests against actual Kafka for true end-to-end verification
- ⚠️ **Requirements**: Requires Docker and may be slower to start (especially Kafka)
- ⚠️ **Resource Usage**: Kafka containers require more memory and startup time

**External Services**: 
- ✅ **Speed**: Faster test execution (no container startup)
- ✅ **Local Development**: Use existing local database
- ⚠️ **Cleanup Required**: Tests must clean up data manually
- ⚠️ **State Leakage**: Risk of test pollution between runs

### Test Settings Override
The tests use mock settings with optimized values for testing:
- Fast polling intervals (0.1s vs 5s in production)
- Small batch sizes (5 vs 100 in production)  
- Short retry backoffs (100ms vs 1000ms in production)
- Lower max retries (2 vs 5 in production)

## Test Coverage Areas

### ✅ **Comprehensive Coverage**

**Configuration Validation:**
- All relay settings bounds checking
- Invalid parameter combinations
- Suboptimal configuration warnings

**Core Processing Logic:**
- Two-phase processing (ID selection → row processing)
- Row locking with revalidation
- Producer lifecycle management
- Message state transitions (PENDING → SENT/FAILED)

**Error Handling & Resilience:**
- Kafka send failures and retries
- Database connection errors
- JSON serialization errors
- Header encoding failures
- Graceful shutdown scenarios

**Concurrency & Race Conditions:**
- Multiple worker coordination
- SKIP LOCKED behavior verification
- Race condition prevention between processing phases
- Database deadlock prevention

**Performance & Scalability:**
- Exponential backoff with overflow protection
- Batch size limiting
- Memory efficiency with large payloads
- High concurrency processing

### **Edge Cases Covered**
- Invalid JSON payloads
- Complex header encoding scenarios
- Scheduled messages with timing precision
- Producer unavailability during processing
- Worker failures in concurrent environments
- Database connection failures
- Service shutdown during active processing

## Debugging Failed Tests

### Common Issues

**1. Database Connection Failures**
```bash
# Check database status
pnpm check services

# Verify test database exists
psql -h localhost -U postgres -c "SELECT 1;"
```

**2. Kafka Container Startup Issues**
```bash
# Check Docker is running and has sufficient resources
docker info

# Check if Kafka testcontainer image is available
docker images | grep confluent

# For real Kafka tests, ensure adequate memory (minimum 4GB)
# Kafka containers require more resources than database containers
```

**2. Test Timeouts**
- Unit tests should complete in <10 seconds
- Integration tests should complete in <30 seconds  
- Concurrency tests may take up to 60 seconds
- Increase timeout values if needed for slower environments

**3. Race Condition Test Failures**
- These tests are timing-sensitive by design
- Occasional failures may occur on very fast or slow systems
- Rerun failing tests to verify consistency

**4. Mock Configuration Issues**
```bash
# Verify mock settings match actual configuration structure
uv run python -c "from src.core.config import get_settings; print(get_settings().relay.__dict__)"
```

## Test Maintenance

### Adding New Tests
1. **Unit Tests**: Add to `test_outbox_relay_service.py` with appropriate mocking
2. **Integration Tests**: Add to main integration file for database-dependent tests  
3. **Concurrency Tests**: Add to concurrency file for multi-worker scenarios

### Test Naming Convention
- `test_[method_name]_[scenario]` for unit tests
- `test_[feature]_[scenario]` for integration tests
- Include success/failure path in test name

### Mock Updates
When updating the OutboxRelayService:
1. Update mock settings fixtures if new configuration is added
2. Update mock producer behavior if Kafka interaction changes
3. Ensure mock database sessions match actual session usage patterns

## Performance Benchmarks

Expected test execution times:
- **Unit Tests**: 5-10 seconds (70+ tests)
- **Integration Tests (Mocked Kafka)**: 15-30 seconds (25+ tests)  
- **Real Kafka Integration Tests**: 45-90 seconds (15+ tests) - includes container startup
- **Concurrency Tests**: 30-60 seconds (10+ tests)
- **Full Suite (with Kafka)**: 90-120 seconds
- **Full Suite (without Kafka)**: 60-90 seconds

**Notes:**
- Real Kafka tests take longer due to container startup (Kafka ~10-15s, PostgreSQL ~2-3s)
- First run may be slower due to Docker image pulls
- Concurrent Kafka tests may require more time for message consumption verification
- Use mocked Kafka tests for faster feedback during development
- Use real Kafka tests for comprehensive pre-deployment validation

These benchmarks help identify performance regressions in the test suite itself.