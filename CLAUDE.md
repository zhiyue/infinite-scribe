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
  - PostgreSQL: Port 5432 (user: postgres, password: postgres, db: test_db)
  - Neo4j: Port 7687 (user: neo4j, password: neo4jtest, Web UI: 7474)
  - Redis: Port 6379 (no password)
  - Docker environment for running containers

### SSH Access
```bash
ssh zhiyue@192.168.2.201
```

### Local Testing with Remote Services
For integration tests, use the remote containers:
```bash
# Use .env.test configuration
export $(cat .env.test | xargs)

# Run all tests
./test_remote.sh

# Run specific integration tests
cd apps/backend && uv run pytest tests/integration/test_remote_databases.py -v
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