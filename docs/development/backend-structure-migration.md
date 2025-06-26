# Backend Structure Migration Guide

## Overview

This document describes the new unified backend structure that consolidates all backend services (API Gateway and Agent services) into a single codebase under `apps/backend`.

## Key Changes

### 1. Directory Structure

**Old Structure:**
```
apps/
├── api-gateway/
├── worldsmith-agent/
├── plotmaster-agent/
└── ... (each agent as separate app)
```

**New Structure:**
```
apps/
├── frontend/
└── backend/
    ├── src/
    │   ├── api/        # API Gateway
    │   ├── agents/     # All agent services
    │   ├── core/       # Shared core functionality
    │   └── common/     # Shared business logic
    ├── pyproject.toml  # Unified dependencies
    └── Dockerfile      # Single Dockerfile
```

### 2. Unified Dependencies

All backend services now share a single `pyproject.toml` file at `apps/backend/pyproject.toml`. This simplifies dependency management and ensures consistency across services.

### 3. Flexible Deployment

The backend uses a single Dockerfile with parameterized service selection:

```bash
# Deploy API Gateway
docker build -t infinite-scribe-backend ./apps/backend
docker run -e SERVICE_TYPE=api-gateway infinite-scribe-backend

# Deploy Worldsmith Agent
docker run -e SERVICE_TYPE=agent-worldsmith infinite-scribe-backend

# Deploy Plotmaster Agent
docker run -e SERVICE_TYPE=agent-plotmaster infinite-scribe-backend
```

## Development Workflow

### Local Development

1. Navigate to the backend directory:
   ```bash
   cd apps/backend
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Run specific services:
   ```bash
   # API Gateway
   uvicorn src.api.main:app --reload
   
   # Agent services
   python -m src.agents.worldsmith.main
   python -m src.agents.plotmaster.main
   ```

### Docker Compose

Use the new `docker-compose.backend.yml` overlay:

```bash
docker-compose -f docker-compose.yml -f docker-compose.backend.yml up
```

## Benefits

1. **Simplified Dependency Management**: One `pyproject.toml` for all backend services
2. **Code Reuse**: Agents can easily share common functionality
3. **Easier Maintenance**: Single codebase to maintain
4. **Flexible Deployment**: Same Docker image can run different services
5. **Development Efficiency**: No need to switch between multiple virtual environments

## Migration Steps

1. Update your local development environment to use the new structure
2. Update CI/CD pipelines to build from `apps/backend`
3. Update deployment configurations to use the `SERVICE_TYPE` environment variable
4. Remove old agent directories after confirming the new structure works

## Environment Variables

Each service can be configured through environment variables:

- `SERVICE_TYPE`: Determines which service to run (e.g., `api-gateway`, `agent-worldsmith`)
- Database connections, API keys, and other configs remain the same

## Example Service Implementation

Each agent should have a main entry point at `src/agents/<agent-name>/main.py`:

```python
# src/agents/worldsmith/main.py
from ...core.config import settings
from ...common.services import kafka_service

def run():
    """Main entry point for the Worldsmith agent."""
    # Agent implementation
    pass

if __name__ == "__main__":
    run()
```