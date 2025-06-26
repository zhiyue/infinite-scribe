# Environment Variables Configuration Guide

## Overview

InfiniteScribe uses a layered approach to environment variable management, separating infrastructure concerns from application configuration.

## Environment File Structure

```
.env.infrastructure    # Core services (Docker Compose)
.env.frontend         # Frontend application
.env.backend          # API Gateway & backend services  
.env.agents           # AI Agent services
```

## Layer Details

### 1. Infrastructure Layer (`.env.infrastructure`)

Used by Docker Compose to deploy core services. Managed by DevOps team.

**Key Variables:**
- `POSTGRES_*` - PostgreSQL configuration
- `REDIS_*` - Redis configuration
- `NEO4J_*` - Neo4j configuration
- `MINIO_*` - MinIO object storage
- `KAFKA_*` - Kafka message broker
- `DEV_SERVER_IP` - Development server IP

**Usage:**
```bash
# Default (uses .env if exists, otherwise .env.infrastructure)
docker compose up -d

# Explicit environment file
docker compose --env-file .env.infrastructure up -d

# Using deployment script
./scripts/deploy-infrastructure.sh
```

### 2. Frontend Layer (`.env.frontend`)

Used by the React/Vite frontend application.

**Key Variables:**
- `VITE_API_BASE_URL` - Backend API endpoint
- `VITE_WS_URL` - WebSocket endpoint
- `VITE_ENABLE_*` - Feature flags

**Usage:**
```bash
# Development
cd apps/frontend
cp .env.frontend.example .env.frontend
# Edit .env.frontend with your values
npm run dev

# Production build
npm run build
```

### 3. Backend Layer (`.env.backend`)

Used by the unified backend services (API Gateway and all Agents).

**Key Variables:**
- `SERVICE_TYPE` - Determines which service to run (e.g., `api-gateway`, `agent-worldsmith`)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `*_API_KEY` - External service API keys
- `JWT_SECRET` - Authentication secret

**Usage:**
```bash
# Backend services
cd apps/backend
cp .env.backend.example .env.backend
# Edit .env.backend

# Run specific service via SERVICE_TYPE
SERVICE_TYPE=api-gateway uvicorn src.api.main:app
SERVICE_TYPE=agent-worldsmith python -m src.agents.worldsmith.main
```

### 4. Agent Layer (`.env.agents`)

> **注意:** Agent服务现已整合到后端层。Agent相关的环境变量应包含在 `.env.backend` 中。

**Key Variables (now in `.env.backend`):**
- `LLM_MODEL_*` - Model selection per agent
- `LLM_TEMPERATURE_*` - Model parameters
- `AGENT_*` - Agent-specific settings

**Usage:**
```bash
# Backend services (API Gateway and Agents)
cd apps/backend
cp .env.backend.example .env.backend
# Edit .env.backend

# Run API Gateway
SERVICE_TYPE=api-gateway uvicorn src.api.main:app

# Run specific agent
SERVICE_TYPE=agent-worldsmith python -m src.agents.worldsmith.main
```

## Security Best Practices

1. **Never commit actual `.env` files** - Only commit `.env.*.example` templates
2. **Use strong passwords** - Generate with `openssl rand -base64 32`
3. **Rotate secrets regularly** - Especially API keys
4. **Separate by environment** - Different values for dev/staging/prod
5. **Limit access** - Infrastructure vars only for DevOps team

## Migration from Single .env

If you have an existing `.env` file:

```bash
# Backup existing configuration
cp .env .env.backup

# Copy infrastructure variables
cp .env .env.infrastructure

# Create application configs from examples
cp .env.frontend.example .env.frontend
cp .env.backend.example .env.backend
cp .env.agents.example .env.agents

# Update application configs with values from .env.backup
# Remove application-specific vars from .env.infrastructure
```

## Docker Compose Behavior

Docker Compose looks for environment files in this order:
1. `.env` (if exists)
2. Variables set in shell environment
3. Default values in `docker-compose.yml`

To use `.env.infrastructure` explicitly:
- Rename to `.env`, OR
- Use `docker compose --env-file .env.infrastructure`, OR
- Set `COMPOSE_ENV_FILE=.env.infrastructure` in your shell

## Troubleshooting

### Services can't connect
- Check if services use internal Docker network names (e.g., `postgres` not `localhost`)
- Verify passwords match between layers

### Environment variable not found
- Check correct file is loaded
- Verify variable name matches exactly
- For frontend, remember `VITE_` prefix

### Permission denied
- Ensure `.env.*` files have appropriate permissions: `chmod 600 .env.*`