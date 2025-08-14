# InfiniteScribe Scripts

Utility scripts organized by category for development, testing, deployment and operations.

## Directory Structure

### Development (`dev/`)
Environment setup and development tools.

#### `setup-dev.sh`
Set up the complete development environment including Python virtual environment and dependencies.

```bash
# Run development environment setup script
./scripts/dev/setup-dev.sh
```

#### `setup-pre-commit.sh`
Configure pre-commit hooks for code quality checks.

```bash
# Setup pre-commit hooks
./scripts/dev/setup-pre-commit.sh
```

#### `dev.py`
Development helper script for running services, tests, and code quality checks.

```bash
# Run API Gateway
python scripts/dev/dev.py run api-gateway

# Run specific agent
python scripts/dev/dev.py run worldsmith-agent

# Run tests with coverage
python scripts/dev/dev.py test --coverage

# Format code
python scripts/dev/dev.py format
```

#### `verify-ruff.sh`
Verify Ruff installation and configuration.

```bash
# Verify Ruff setup
./scripts/dev/verify-ruff.sh
```

#### `install-check-deps.sh`
Install dependencies for full service health checks.

```bash
# Install health check dependencies
./scripts/dev/install-check-deps.sh
```

### Testing (`test/`)
Test runners and validation scripts.

- **`run-tests.sh`** - Comprehensive test runner (unit/integration/lint/coverage)
- **`test-project-structure.js`** - Project structure validation
- **`test-frontend-local.sh`** - Frontend-specific local testing

### Deployment (`deploy/`)
Deployment and build scripts.

- **`deploy-to-dev.sh`** - Main deployment script (all services)
- **`deploy-infrastructure.sh`** - Infrastructure-only deployment
- **`build.sh`** - Docker build operations
- **`deploy-frontend*.sh`** - Frontend deployment variants

**Quick Deploy Commands:**
```bash
make deploy                  # 日常代码部署
make deploy-build            # 重新构建并部署
make deploy-api              # 只部署 API Gateway
```

### Operations (`ops/`)
Monitoring, logs, and backup scripts.

- **`check-services*.js`** - Service health monitoring
- **`remote-logs.sh`** - Remote log viewing with filtering
- **`backup-dev-data.sh`** - Development data backup
- **`start-agents.sh`** - Agent service management

**Quick Ops Commands:**
```bash
pnpm check:services          # Health check
pnpm logs:remote             # View logs
pnpm backup:dev              # Backup data
```

### App-Specific Scripts
- **Backend scripts**: `apps/backend/scripts/` (API Gateway startup, DB utilities)
- **Frontend scripts**: `apps/frontend/scripts/` (build and test automation)

### Tools (`tools/`)
Utility and integration scripts.

- **`hoppscotch-integration.sh`** - API documentation and Hoppscotch collection generation

### Database (`db/`)
Database management scripts.

- **`run_migrations.py`** - Execute Alembic migrations
- **`verify_db_migration.py`** - Verify migration status

## Quick Commands

```bash
# Setup
make setup                   # Install dependencies
make dev                     # Start dev servers

# Testing
make test-all                # All tests
make test-coverage           # Tests with coverage

# Deployment
make deploy                  # Deploy to dev server
make ssh-dev                 # SSH to dev server

# Monitoring
pnpm check:services          # Health check
pnpm logs:remote             # View logs
pnpm backup:dev              # Backup data
```

## Environment Variables

- `DEV_SERVER` - Target server IP (default: 192.168.2.201)
- `TEST_MACHINE_IP` - Test server IP (default: 192.168.2.202)
- `DEV_USER` - SSH user (default: zhiyue)

## Requirements

- SSH access to dev/test servers
- Docker and Docker Compose
- Node.js 20+ and Python 3.11+ with uv
- Environment files (.env.*, docker-compose.yml)

## Troubleshooting

- **SSH issues**: Check SSH keys and connectivity
- **Service failures**: Run `pnpm check:services` and view logs
- **Test failures**: Use `make test-all` with Docker containers
- **Environment issues**: Run `./scripts/dev/setup-dev.sh` to reset