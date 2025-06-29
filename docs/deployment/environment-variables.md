# Environment Variables Guide

## Overview

InfiniteScribe uses a simplified environment structure with four main configuration files:

1. **`.env`** - Symlink to the active environment configuration
2. **`.env.local`** - Local development with Docker Compose
3. **`.env.dev`** - Development server (192.168.2.201) configuration
4. **`.env.test`** - Test environment configuration
5. **`.env.example`** - Template with all possible variables

## Environment Files Comparison

### Common Variables (All Environments)

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_HOST` | PostgreSQL host | localhost / 192.168.2.201 |
| `POSTGRES_PORT` | PostgreSQL port | 5432 |
| `POSTGRES_USER` | PostgreSQL user | postgres |
| `POSTGRES_PASSWORD` | PostgreSQL password | devPostgres123! |
| `REDIS_HOST` | Redis host | localhost / 192.168.2.201 |
| `REDIS_PORT` | Redis port | 6379 |
| `REDIS_PASSWORD` | Redis password | devRedis123! |
| `NEO4J_HOST` | Neo4j host | localhost / 192.168.2.201 |
| `NEO4J_PORT` | Neo4j port | 7687 |
| `NEO4J_USER` | Neo4j user | neo4j |
| `NEO4J_PASSWORD` | Neo4j password | devNeo4j123! |
| `API_HOST` | API bind host | 0.0.0.0 |
| `API_PORT` | API port | 8000 |
| `SERVICE_NAME` | Service identifier | infinite-scribe-backend |
| `SERVICE_TYPE` | Service type | api-gateway |
| `ALLOWED_ORIGINS` | CORS allowed origins | ["*"] |
| `OPENAI_API_KEY` | OpenAI API key | (your key) |
| `ANTHROPIC_API_KEY` | Anthropic API key | (your key) |

### Environment-Specific Variables

#### Local Development (`.env.local`)
- `NODE_ENV=development`
- `POSTGRES_DB=infinite_scribe`
- All hosts use `localhost`
- `NEXT_PUBLIC_API_URL=http://localhost:8000`

#### Development Server (`.env.dev`)
- `NODE_ENV=development`
- `POSTGRES_DB=infinite_scribe`
- All hosts use `192.168.2.201`
- `NEXT_PUBLIC_API_URL=http://192.168.2.201:8000`
- Used for persistent development infrastructure

#### Test Environment (`.env.test`)
- `NODE_ENV=test`
- `POSTGRES_DB=infinite_scribe_test` (separate test database)
- `TEST_MACHINE_IP=${TEST_MACHINE_IP:-192.168.2.202}`
- All hosts use `${TEST_MACHINE_IP}`
- Additional Docker configuration:
  - `USE_REMOTE_DOCKER=true`
  - `REMOTE_DOCKER_HOST=tcp://${TEST_MACHINE_IP}:2375`
  - `DISABLE_RYUK=false`

## When to Use Each Environment

### `.env.local`
- **Use for**: Local development on your machine
- **Services**: Run with Docker Compose locally
- **Database**: Local `infinite_scribe` database
- **Best for**: Individual development, testing new features

### `.env.dev`
- **Use for**: Shared development infrastructure
- **Services**: Deployed on 192.168.2.201
- **Database**: Shared `infinite_scribe` database
- **Best for**: Team development, integration testing, demos

### `.env.test`
- **Use for**: Running automated tests
- **Services**: Isolated containers on test machine
- **Database**: Separate `infinite_scribe_test` database
- **Best for**: CI/CD, test runs, destructive testing

## Usage

### Switching Environments

```bash
# Show current environment
pnpm env:show

# Switch to local development
pnpm env:local

# Switch to dev server
pnpm env:dev

# Switch to test environment
pnpm env:test
```

### Manual Switching

```bash
# Remove existing symlink
rm .env

# Create new symlink
ln -s .env.local .env    # For local development
ln -s .env.dev .env      # For dev server
ln -s .env.test .env     # For testing
```

## Optional Services

These services can be enabled by uncommenting in your environment file:

### Milvus Vector Database
```bash
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### MinIO Object Storage
```bash
MINIO_HOST=localhost
MINIO_PORT=9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_ENDPOINT=minio:9000
```

### Kafka Message Broker
```bash
KAFKA_HOST=localhost
KAFKA_PORT=9092
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_ADVERTISED_LISTENERS=INTERNAL://kafka:29092,EXTERNAL://localhost:9092
```

### Prefect Workflow Orchestration
```bash
PREFECT_API_URL=http://prefect:4200/api
PREFECT_POSTGRES_USER=prefect
PREFECT_POSTGRES_PASSWORD=your_prefect_password
```

## Complete Variable Reference

### Core Services
- **PostgreSQL**: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- **Redis**: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
- **Neo4j**: `NEO4J_HOST`, `NEO4J_PORT`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_URI`

### Application Configuration
- **API**: `API_HOST`, `API_PORT`
- **Frontend**: `NEXT_PUBLIC_API_URL`, `PORT`
- **Service**: `NODE_ENV`, `SERVICE_NAME`, `SERVICE_TYPE`, `ALLOWED_ORIGINS`

### AI Providers
- **OpenAI**: `OPENAI_API_KEY`
- **Anthropic**: `ANTHROPIC_API_KEY`

### Test Environment Only
- **Docker**: `TEST_MACHINE_IP`, `USE_REMOTE_DOCKER`, `REMOTE_DOCKER_HOST`, `DISABLE_RYUK`
- **Testcontainers**: `TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE`, `TESTCONTAINERS_HOST_OVERRIDE`

### Optional Services
- **Milvus**: `MILVUS_HOST`, `MILVUS_PORT`
- **MinIO**: `MINIO_HOST`, `MINIO_PORT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_ENDPOINT`
- **Kafka**: `KAFKA_HOST`, `KAFKA_PORT`, `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_ADVERTISED_LISTENERS`
- **Prefect**: `PREFECT_API_URL`, `PREFECT_POSTGRES_USER`, `PREFECT_POSTGRES_PASSWORD`

## Best Practices

1. **Never commit** actual API keys or passwords
2. **Use `.env.example`** as a reference for all available variables
3. **Keep environment-specific** variables in their respective files
4. **Use environment variables** instead of hardcoding values in code
5. **Document** any new environment variables you add
6. **Set appropriate defaults** in your application code

## Testing with Custom Test Machine

To use a different test machine:

```bash
# Set custom test machine IP
export TEST_MACHINE_IP=192.168.2.100

# Run tests
./scripts/run-tests.sh --all --docker-host
```

The test environment will automatically use the custom IP for all service connections.
