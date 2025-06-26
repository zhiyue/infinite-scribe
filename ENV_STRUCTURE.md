# Environment Variables Structure

## Quick Start

```bash
# For infrastructure deployment (Docker Compose)
cp .env.example .env.infrastructure
# Edit .env.infrastructure with your values
pnpm infra:up

# For frontend development
cd apps/frontend
cp .env.frontend.example .env.frontend
# Edit .env.frontend

# For backend development
cd apps/api-gateway
cp .env.backend.example .env.backend
# Edit .env.backend

# For agent development
cd apps/worldsmith-agent
cp .env.agents.example .env.agents
# Edit .env.agents
```

## File Structure

```
.env                    → Symlink to .env.infrastructure (for docker-compose)
.env.infrastructure     → Core services configuration
.env.frontend          → Frontend app configuration
.env.backend           → Backend services configuration
.env.agents            → AI agents configuration
.env.*.example         → Templates (safe to commit)
```

## Why Separate?

1. **Security** - Different access levels for different teams
2. **Deployment** - Services can be deployed independently  
3. **Development** - Developers only need relevant configs
4. **Maintenance** - Easier to manage and update

## Commands

```bash
# Infrastructure
pnpm infra:up          # Start all services
pnpm infra:down        # Stop all services
pnpm infra:logs        # View service logs
pnpm infra:deploy      # Deploy to dev server

# Check health
pnpm check:services    # Quick health check
```

## Details

See [docs/deployment/environment-variables.md](docs/deployment/environment-variables.md) for complete documentation.