# Essential Commands

## Development Commands

### Backend Development
```bash
# Setup and dependencies
pnpm backend install                 # Install Python dependencies (uv sync)
uv sync --all-extras                 # Direct uv command

# Running services
pnpm backend run                     # Start API Gateway (uvicorn)
pnpm backend api:simple              # Simple API gateway
pnpm backend api:local               # Local API gateway
pnpm backend api:dev                 # Development API gateway

# Code quality
pnpm backend lint                    # Ruff check
pnpm backend format                  # Ruff format 
pnpm backend typecheck               # mypy type checking
uv run ruff check src/               # Direct ruff check
uv run ruff format src/              # Direct ruff format
uv run mypy src/ --ignore-missing-imports  # Direct mypy

# Testing
pnpm backend test                    # Unit tests
uv run pytest tests/unit/ -v        # Direct unit tests
uv run pytest tests/integration/ -v # Integration tests
uv run pytest tests/ --cov=src --cov-report=html  # Coverage report
```

### Frontend Development
```bash
# Setup and dependencies
pnpm frontend install               # Install npm dependencies
pnpm install                        # Direct pnpm install (in frontend dir)

# Running
pnpm frontend run                   # Start dev server (Vite)
pnpm dev                            # Direct dev command (in frontend dir)
pnpm frontend build                 # Build for production

# Testing
pnpm frontend test                  # Unit tests (Vitest)
pnpm frontend e2e                   # E2E tests (Playwright)
pnpm frontend e2e:ui                # E2E with UI
pnpm frontend e2e:debug             # E2E debug mode
pnpm frontend e2e:auth              # Auth-specific E2E tests
```

### Unified Testing Commands
```bash
# Parameterized testing system
pnpm test all                       # All tests (local Docker)
pnpm test all --remote              # Remote tests (192.168.2.202)
pnpm test unit                      # Unit tests only
pnpm test coverage                  # Tests with coverage
```

## Infrastructure Management

### Local Services
```bash
# Infrastructure
pnpm infra up                       # Start all local services
pnpm infra down                     # Stop all local services
pnpm infra status                   # Check service status

# Service health checks
pnpm check services                 # Quick health check (local)
pnpm check services --remote        # Quick health check (dev server)
pnpm check services:full            # Full health check (local)
pnpm check services:full --remote   # Full health check (dev server)
```

### Deployment
```bash
# Infrastructure deployment
pnpm infra deploy                   # Deploy to dev server (192.168.2.201)
pnpm infra deploy --local           # Local deployment
pnpm infra deploy --local --clean   # Clean local deployment

# Application deployment
pnpm app                            # Deploy all services
pnpm app --build                    # Build and deploy all
pnpm app --type backend             # Deploy backend only
pnpm app --service api-gateway      # Deploy specific service
```

## Utilities

### SSH Access
```bash
pnpm ssh dev                        # SSH to dev server (192.168.2.201)
pnpm ssh test                       # SSH to test server (192.168.2.202)
```

### API Tools
```bash
pnpm api export                     # Export local API definition
pnpm api export:dev                 # Export dev environment API
```

### Database Management (Backend)
```bash
# Migrations (run from apps/backend/)
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                              # Apply migrations
alembic current                                   # Check status
alembic downgrade -1                              # Rollback one migration
```

## Help System
```bash
pnpm run                            # Main help system
pnpm backend                        # Backend operations help
pnpm frontend                       # Frontend operations help
pnpm test                           # Testing operations help
pnpm ssh                            # SSH connection help
pnpm check                          # Service check help
pnpm api                            # API tools help
```