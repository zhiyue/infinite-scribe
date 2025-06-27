# Infinite Scribe - Development Environment

## Project Overview
Infinite Scribe is a full-stack application with:
- Frontend: Next.js/React (TypeScript)
- Backend: FastAPI (Python)
- Databases: PostgreSQL, Neo4j
- Cache: Redis
- Package Management: pnpm (frontend), uv (backend)

## Remote Container Services (192.168.2.201)
All database and cache services are deployed on the remote server:
- **Host**: 192.168.2.201
- **User**: zhiyue (SSH access available)
- **Services**:
  - PostgreSQL: Port 5432 (user: postgres, password: devPostgres123!, db: infinite_scribe)
  - Neo4j: Port 7687 (user: neo4j, password: devNeo4j123!, Web UI: 7474)
  - Redis: Port 6379 (password: devRedis123!)
  - Docker environment for running containers

### SSH Access
```bash
ssh zhiyue@192.168.2.201
```

### Testing

The project uses a unified test script with various options:

```bash
# Show help
./scripts/run-tests.sh --help

# Run unit tests only (default)
./scripts/run-tests.sh
./scripts/run-tests.sh --unit

# Run integration tests only
./scripts/run-tests.sh --integration

# Run all tests (unit + integration)
./scripts/run-tests.sh --all

# Run tests with coverage report
./scripts/run-tests.sh --all --coverage

# Run only code quality checks (linting, formatting, type checking)
./scripts/run-tests.sh --lint

# Skip code quality checks
./scripts/run-tests.sh --all --no-lint
```

#### Testing with Remote Services
Use remote containers at 192.168.2.201:
```bash
# Run all tests with remote services
./scripts/run-tests.sh --all --remote

# Run specific integration tests
cd apps/backend && uv run pytest tests/integration/test_remote_databases.py -v
```

#### Testing with Remote Docker Host
Use a remote Docker host for testcontainers:
```bash
# Run all tests using remote Docker host (default: 192.168.2.202:2375)
./scripts/run-tests.sh --all --docker-host

# Use a custom Docker host
export DOCKER_HOST_IP=192.168.2.100
export DOCKER_HOST_PORT=2375
./scripts/run-tests.sh --all --docker-host

# Or set environment variables manually
export USE_REMOTE_DOCKER=true
export REMOTE_DOCKER_HOST=tcp://192.168.2.202:2375
./scripts/run-tests.sh --all

# Or use the .env.remote-docker configuration
export $(cat .env.remote-docker | xargs)
./scripts/run-tests.sh --all
```

**Remote Docker Configuration Options:**
- `DOCKER_HOST_IP` - Docker host IP address (default: 192.168.2.202)
- `DOCKER_HOST_PORT` - Docker daemon port (default: 2375)
- `USE_REMOTE_DOCKER=true` - Enable remote Docker host for testcontainers
- `REMOTE_DOCKER_HOST=tcp://192.168.2.202:2375` - Docker daemon URL
- `DISABLE_RYUK=true` - Only set if experiencing Ryuk issues (not recommended)

**Docker Host Setup (on DOCKER_HOST_IP, default 192.168.2.202):**
```bash
# Ensure Docker daemon is listening on TCP
# Edit /etc/docker/daemon.json to include:
# {
#   "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
# }
# Then restart Docker service
```

## Project Structure
```
infinite-scribe/
├── apps/
│   ├── backend/         # FastAPI Python backend
│   │   ├── src/        # Source code
│   │   └── tests/      # Unit and integration tests
│   └── frontend/       # Next.js frontend
├── packages/           # Shared packages
├── .github/           # GitHub Actions workflows
├── pyproject.toml     # Python project configuration
├── uv.lock           # Python dependency lock file
├── package.json      # Node.js project configuration  
├── pnpm-lock.yaml   # Frontend dependency lock file
└── .env.test        # Test environment configuration
```

## Common Commands

### Backend Development
```bash
# Install dependencies
uv sync --all-extras

# Run backend server
cd apps/backend && uv run uvicorn src.main:app --reload

# Run tests
cd apps/backend && uv run pytest tests/unit/ -v  # Unit tests only
cd apps/backend && uv run pytest tests/ -v       # All tests

# Linting and formatting
cd apps/backend && uv run ruff check src/
cd apps/backend && uv run ruff format src/

# Type checking
uv run mypy apps/backend/src/ --ignore-missing-imports
```

### Frontend Development
```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev

# Build
pnpm build

# Run tests
pnpm test
```

## CI/CD
- GitHub Actions workflows in `.github/workflows/`
- Trivy security scanning configured (CRITICAL vulnerabilities only)
- Automated testing on push/PR to main/develop branches

## Important Notes
- Always use remote containers at 192.168.2.201 for database operations
- Integration tests require connectivity to remote services
- Use `.env.test` for test environment configuration
- Local development does not require Docker