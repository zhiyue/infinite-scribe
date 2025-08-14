# Docker Architecture

## Overview

InfiniteScribe uses Docker and Docker Compose for consistent development and deployment across different environments. The architecture supports three deployment scenarios: local development, shared development server, and isolated testing.

## File Structure

```
infinite-scribe/
├── docker-compose.yml              # Infrastructure services
├── docker-compose.backend.yml      # Application services
├── .dockerignore                   # Build context optimization
├── .env                           # Symlink to active environment
├── .env.local                     # Local development config
├── .env.dev                       # Dev server config (192.168.2.201)
├── .env.test                      # Test environment config
├── .env.example                   # Template with all variables
├── apps/
│   └── backend/
│       └── Dockerfile             # Unified backend Dockerfile
└── scripts/
    └── deployment/
        └── deploy-infrastructure.sh  # Deployment automation
```

## Architecture Layers

### 1. Infrastructure Layer (`docker-compose.yml`)

Core services required by the application:

- **Databases**: PostgreSQL, Neo4j, Redis
- **Optional Services**: Milvus, MinIO, Kafka, Prefect
- **Network**: `infinite-scribe-network`
- **Volumes**: Persistent data storage

### 2. Application Layer (`docker-compose.backend.yml`)

Application services (when containerized):

- **API Gateway**: Main REST API
- **Agent Services**: Worldsmith, Plotmaster, etc.
- **Build Context**: Root directory for monorepo access

## Environment-Based Configuration

### Local Development
```yaml
# Uses .env.local
services:
  postgres:
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    environment:
      POSTGRES_HOST: localhost
```

### Development Server
```yaml
# Uses .env.dev
services:
  postgres:
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    environment:
      POSTGRES_HOST: 192.168.2.201
```

### Test Environment
```yaml
# Uses .env.test
services:
  postgres:
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    environment:
      POSTGRES_HOST: ${TEST_MACHINE_IP}
      POSTGRES_DB: infinite_scribe_test
```

## Service Architecture

### Database Services

```yaml
postgres:
  image: postgres:16
  volumes:
    - postgres-data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]

redis:
  image: redis:7.2-alpine
  command: redis-server --requirepass ${REDIS_PASSWORD}

neo4j:
  image: neo4j:5
  environment:
    NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
```

### Networking

All services connect through a bridge network:

```yaml
networks:
  infinite-scribe-network:
    driver: bridge
```

Services can communicate using service names as hostnames.

### Volume Management

Persistent volumes for data storage:

```yaml
volumes:
  postgres-data:     # PostgreSQL databases
  redis-data:        # Redis persistence
  neo4j-data:        # Graph database
  milvus-data:       # Vector embeddings
  minio-data:        # Object storage
```

## Deployment Patterns

### 1. Local Development

```bash
# Switch to local environment
pnpm env:local

# Start infrastructure
docker compose up -d

# Or use pnpm command
pnpm infra:up
```

### 2. Development Server Deployment

```bash
# Deploy to 192.168.2.201
./scripts/deploy/deploy-infrastructure.sh

# This will:
# 1. Sync files to server
# 2. Use .env.dev configuration
# 3. Start services remotely
```

### 3. Manual Deployment

```bash
# On target server
docker compose --env-file .env.dev up -d
```

## Build Optimization

### Docker Ignore

The `.dockerignore` file excludes:
```
node_modules/
.git/
.env*
!.env.example
__pycache__/
*.pyc
.pytest_cache/
.coverage
```

### Multi-Stage Builds

Backend Dockerfile uses multi-stage builds:

```dockerfile
# Stage 1: Dependencies
FROM python:3.11-slim as builder
COPY pyproject.toml .
RUN pip install uv && uv pip install --system .

# Stage 2: Runtime
FROM python:3.11-slim
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
```

## Service Dependencies

### Startup Order

Services have health checks and dependencies:

```yaml
milvus:
  depends_on:
    etcd:
      condition: service_healthy
    minio:
      condition: service_healthy
```

### Health Checks

All services include health checks:

```yaml
healthcheck:
  test: ["CMD", "command"]
  interval: 10s
  timeout: 5s
  retries: 5
```

## Environment Variables

### Variable Resolution Order

1. Shell environment variables
2. `.env` file (symlink to active environment)
3. docker-compose.yml defaults

### Service-Specific Variables

```yaml
environment:
  # Direct value
  POSTGRES_DB: infinite_scribe

  # From .env file
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

  # With default
  POSTGRES_PORT: ${POSTGRES_PORT:-5432}
```

## Best Practices

### 1. Environment Management
- Use appropriate `.env.*` file for each environment
- Never commit sensitive credentials
- Keep `.env.example` updated

### 2. Resource Limits
```yaml
deploy:
  resources:
    limits:
      memory: 1G
    reservations:
      memory: 512M
```

### 3. Logging
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 4. Security
- Use specific image versions (not `latest`)
- Run containers as non-root when possible
- Limit network exposure with proper port binding

## Troubleshooting

### Common Issues

1. **Port conflicts**: Check with `lsof -i :PORT`
2. **Volume permissions**: Ensure proper ownership
3. **Network issues**: Verify service names and ports
4. **Memory issues**: Check Docker resource limits

### Debugging Commands

```bash
# View logs
docker compose logs -f [service]

# Execute commands
docker compose exec [service] [command]

# Inspect service
docker inspect [container]

# Check resources
docker stats
```

## Maintenance

### Updating Services

```bash
# Pull latest images
docker compose pull

# Recreate with new images
docker compose up -d --force-recreate
```

### Cleanup

```bash
# Remove stopped containers
docker compose rm

# Clean volumes (WARNING: data loss)
docker compose down -v

# System cleanup
docker system prune -a
```

## Integration with CI/CD

The Docker setup supports:
- Automated testing with isolated containers
- Multi-environment deployments
- Health-based readiness checks
- Rolling updates with zero downtime

For more details:
- [Infrastructure Deployment Guide](../deployment/infrastructure-deployment.md)
- [Environment Structure](../deployment/environment-structure.md)
- [Development Server Setup](../deployment/development-server-setup.md)
