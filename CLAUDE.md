# Infinite Scribe - Development Environment

## Project Overview
Infinite Scribe is a full-stack application with:
- Frontend: Next.js/React (TypeScript)
- Backend: FastAPI (Python)
- Databases: PostgreSQL, Neo4j
- Cache: Redis
- Package Management: pnpm (frontend), uv (backend)

## Remote Infrastructure

### Development Machine (192.168.2.201)
**Purpose**: Long-running development infrastructure services. NOT FOR TESTING.
- **Host**: 192.168.2.201
- **User**: zhiyue (SSH access available)
- **Services**:
  - PostgreSQL: Port 5432 (user: postgres, password: devPostgres123!, db: infinite_scribe)
  - Neo4j: Port 7687 (user: neo4j, password: devNeo4j123!, Web UI: 7474)  
  - Redis: Port 6379 (password: devRedis123!)
- **Important**: This machine is for development use ONLY - NO tests should be run against these services

### Test Machine (default: 192.168.2.202)
**Purpose**: Test environment for running tests including destructive data tests.
- **Host**: Configurable via `TEST_MACHINE_IP` env var (default: 192.168.2.202)
- **User**: zhiyue (SSH access available)
- **Features**:
  - Docker installed with TCP endpoint exposed on port 2375
  - Safe for destructive testing
  - Used by testcontainers for integration tests

### SSH Access
```bash
# Development machine
ssh zhiyue@192.168.2.201

# Test machine (default)
ssh zhiyue@192.168.2.202

# Test machine (custom)
ssh zhiyue@${TEST_MACHINE_IP}
```

### Testing

ALL tests must be run on the test machine. The development machine (192.168.2.201) is NOT for testing.

**Recommended approach**: Use `--docker-host` for testing with Docker containers on the test machine.

To use a custom test machine:
```bash
export TEST_MACHINE_IP=192.168.2.100
./scripts/run-tests.sh --all --docker-host
```

The project supports two testing approaches on the test machine:

#### Option 1: Using Docker Containers (--docker-host) [RECOMMENDED]
Use Docker on the test machine to spin up isolated containers:

```bash
# Run all tests with Docker containers
./scripts/run-tests.sh --all --docker-host

# Run unit tests only
./scripts/run-tests.sh --unit --docker-host

# Run integration tests only
./scripts/run-tests.sh --integration --docker-host
```

#### Option 2: Using Pre-deployed Services (--remote)
Connect to manually deployed services on the test machine (less commonly used):

```bash
# Run all tests with pre-deployed services
./scripts/run-tests.sh --all --remote

# Run unit tests only
./scripts/run-tests.sh --unit --remote

# Run integration tests only
./scripts/run-tests.sh --integration --remote
```

#### Other Options

```bash
# Show help
./scripts/run-tests.sh --help

# Run tests with coverage report
./scripts/run-tests.sh --all --docker-host --coverage
./scripts/run-tests.sh --all --remote --coverage

# Run only code quality checks (linting, formatting, type checking)
./scripts/run-tests.sh --lint

# Skip code quality checks
./scripts/run-tests.sh --all --docker-host --no-lint
./scripts/run-tests.sh --all --remote --no-lint
```


#### Test Machine Configuration Details

##### Docker Host Setup (--docker-host) [RECOMMENDED]
To use Docker containers on the test machine:

```bash
# Use default test machine Docker host
./scripts/run-tests.sh --all --docker-host

# Use a custom test machine
export TEST_MACHINE_IP=192.168.2.100
./scripts/run-tests.sh --all --docker-host

# Override Docker port if different from default
export DOCKER_HOST_PORT=2376
./scripts/run-tests.sh --all --docker-host

# Or set environment variables manually
export USE_REMOTE_DOCKER=true
export REMOTE_DOCKER_HOST=tcp://${TEST_MACHINE_IP:-192.168.2.202}:2375
./scripts/run-tests.sh --all

# Or use the .env.remote-docker configuration
export $(cat .env.remote-docker | xargs)
./scripts/run-tests.sh --all
```

**Docker Configuration Options:**
- `TEST_MACHINE_IP` - Test machine IP address (default: 192.168.2.202)
- `DOCKER_HOST_IP` - Docker host IP (default: uses TEST_MACHINE_IP)
- `DOCKER_HOST_PORT` - Docker daemon port (default: 2375)
- `USE_REMOTE_DOCKER=true` - Enable remote Docker host for testcontainers
- `REMOTE_DOCKER_HOST` - Full Docker daemon URL
- `DISABLE_RYUK=true` - Only set if experiencing Ryuk issues (not recommended)

**Docker Daemon Setup (on test machine):**
```bash
# Ensure Docker daemon is listening on TCP
# Edit /etc/docker/daemon.json to include:
# {
#   "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
# }
# Then restart Docker service
```

##### Pre-deployed Services Setup (--remote)
To use pre-deployed services on the test machine (less common approach):

1. Deploy PostgreSQL, Neo4j, and Redis on your test machine
2. Use the same ports and credentials as defined in `.env.test`
3. Run tests with `--remote` flag to connect to these services

**Service Configuration** (from `.env.test`):
- Host: Uses TEST_MACHINE_IP env var (default: 192.168.2.202)
- PostgreSQL: Port 5432, database: `infinite_scribe_test`
- Neo4j: Port 7687
- Redis: Port 6379

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

# Run tests (recommended: use test script with Docker containers)
./scripts/run-tests.sh --all --docker-host        # All tests with Docker
./scripts/run-tests.sh --unit --docker-host       # Unit tests only
./scripts/run-tests.sh --integration --docker-host # Integration tests only

# Or run tests directly (local only, no external services)
cd apps/backend && uv run pytest tests/unit/ -v  # Unit tests only
cd apps/backend && uv run pytest tests/ -v       # All tests (requires services)

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

## Coding Guidelines

### Configuration Management
- **NEVER hardcode values** - Always use environment variables or configuration files
- IP addresses, ports, passwords, and other environment-specific values must be configurable
- Use sensible defaults with the ability to override via environment variables
- Example: `TEST_MACHINE_IP="${TEST_MACHINE_IP:-192.168.2.202}"` instead of hardcoding `192.168.2.202`

## Important Notes
- Development machine (192.168.2.201): ONLY for development - NO tests of any kind
- Test machine (configurable, default 192.168.2.202): Use for ALL testing
  - **Recommended**: `--docker-host` - Use Docker containers on test machine for isolated testing
  - Alternative: `--remote` - Connect to pre-deployed services on test machine (less common)
- `.env.test` contains test machine service configuration (hosts are overridden by TEST_MACHINE_IP)
- Configure test machine with: `export TEST_MACHINE_IP=your.test.machine.ip`
- Local development does not require Docker
- DISABLE_RYUK is available but not recommended - only use if experiencing Ryuk cleanup issues