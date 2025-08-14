# InfiniteScribe Scripts

This directory contains utility scripts for managing the InfiniteScribe development environment, organized by category.

## 📁 Directory Structure

### Development & Setup (`development/`)
Scripts for setting up and configuring the development environment.

#### `setup-dev.sh`
Set up the complete development environment including Python virtual environment and dependencies.

```bash
# Run development environment setup script
./scripts/development/setup-dev.sh
```

#### `setup-pre-commit.sh`
Configure pre-commit hooks for code quality checks.

```bash
# Setup pre-commit hooks
./scripts/development/setup-pre-commit.sh
```

#### `dev.py`
Development helper script for running services, tests, and code quality checks.

```bash
# Run API Gateway
python scripts/development/dev.py run api-gateway

# Run specific agent
python scripts/development/dev.py run worldsmith-agent

# Run tests with coverage
python scripts/development/dev.py test --coverage

# Format code
python scripts/development/dev.py format
```

#### `verify-ruff.sh`
Verify Ruff installation and configuration.

```bash
# Verify Ruff setup
./scripts/development/verify-ruff.sh
```

#### `install-check-deps.sh`
Install dependencies for full service health checks.

```bash
# Install health check dependencies
./scripts/development/install-check-deps.sh
```

### Testing (`testing/`)
Scripts for running tests and validating project structure.

#### `run-tests.sh`
Comprehensive test runner supporting unit tests, integration tests, and code quality checks.

```bash
# Run unit tests + linting (default)
./scripts/testing/run-tests.sh

# Run all tests using remote services
./scripts/testing/run-tests.sh --all --remote

# Run integration tests with Docker
./scripts/testing/run-tests.sh --integration --docker-host

# Generate coverage report
./scripts/testing/run-tests.sh --all --remote --coverage
```

#### `test-project-structure.js`
Validate the project structure meets requirements.

```bash
# Test project structure
node scripts/testing/test-project-structure.js
# Or using pnpm
pnpm test:structure
```

### Deployment (`deployment/`)
Scripts for deploying services to development and production environments.

> 📖 **简化版部署指南**: 参考 [docs/deployment/DEPLOY_SIMPLE.md](../docs/deployment/DEPLOY_SIMPLE.md) 
> 只需要记住 5 个最常用的命令！

#### `deploy-to-dev.sh`
Deploy the complete InfiniteScribe project to the development server.

```bash
# ⭐ 最常用的 5 个部署命令：
make deploy                  # 日常代码部署（90% 的时候用这个）
make deploy-build            # 重新构建并部署（更新依赖后）
make deploy-api              # 只部署 API Gateway
make deploy-backend          # 部署所有后端服务
make ssh-dev                 # 连接到开发服务器

# 或使用脚本直接调用
./scripts/deployment/deploy-to-dev.sh
pnpm deploy:dev

# Deploy to custom server
DEV_SERVER=your.server.ip ./scripts/deployment/deploy-to-dev.sh
```

#### `deploy-infrastructure.sh`
Deploy only the infrastructure services using Docker Compose.

```bash
# Deploy to remote server
./scripts/deployment/deploy-infrastructure.sh
# Or using pnpm
pnpm infra:deploy

# Deploy locally
./scripts/deployment/deploy-infrastructure.sh --local
pnpm infra:deploy:local
```

### Monitoring & Maintenance (`monitoring/`)
Scripts for monitoring service health, viewing logs, and backing up data.

#### `check-services.js` / `check-services-simple.js`
Check the health status of all InfiniteScribe services.

```bash
# Simple connectivity check (no dependencies)
node scripts/monitoring/check-services-simple.js
# Or using pnpm
pnpm check:services

# Full health check with detailed service info (requires npm packages)
node scripts/monitoring/check-services.js
# Or using pnpm
pnpm check:services:full
```

#### `remote-logs.sh`
View logs from services running on the development server.

```bash
# View all logs (last 100 lines)
./scripts/monitoring/remote-logs.sh
# Or using pnpm
pnpm logs:remote

# Follow specific service logs
./scripts/monitoring/remote-logs.sh -f postgres
pnpm logs:remote -- -f postgres

# View last 50 lines of Kafka logs
./scripts/monitoring/remote-logs.sh -n 50 kafka
pnpm logs:remote -- -n 50 kafka

# Get help
./scripts/monitoring/remote-logs.sh --help
```

#### `backup-dev-data.sh`
Create a complete backup of all development data.

```bash
# Create backup (saved to ./backups/)
./scripts/monitoring/backup-dev-data.sh
# Or using pnpm
pnpm backup:dev

# Backup with custom server
DEV_SERVER=your.server.ip ./scripts/monitoring/backup-dev-data.sh
```

Backs up:
- PostgreSQL databases (all)
- Redis data
- Neo4j graph database
- MinIO object storage (novels bucket)
- Environment configuration files

### Backend Scripts (`../apps/backend/scripts/`)
Backend-specific scripts for running services and utilities.

#### API Gateway Startup Scripts
Located in `apps/backend/scripts/`:

- **`run-api-gateway-simple.sh`**: Simple startup without external service checks
  ```bash
  ./apps/backend/scripts/run-api-gateway-simple.sh
  # Or using pnpm
  pnpm backend:api:simple
  ```

- **`run-api-gateway-local.sh`**: Local development with `.env.local` configuration
  ```bash
  ./apps/backend/scripts/run-api-gateway-local.sh
  # Or using pnpm
  pnpm backend:api:local
  ```

- **`run-api-gateway-dev.sh`**: Development mode connecting to remote services (192.168.2.201)
  ```bash
  ./apps/backend/scripts/run-api-gateway-dev.sh
  # Or using pnpm
  pnpm backend:api:dev
  ```

See `apps/backend/scripts/README_API_GATEWAY.md` for detailed documentation.

#### Database Utilities
Located in `apps/backend/scripts/`:

- **`verify_tables.py`**: Verify database table structure and constraints
  ```bash
  cd apps/backend && python scripts/verify_tables.py
  ```

- **`apply_db_functions.py`**: Apply database functions and triggers
  ```bash
  cd apps/backend && python scripts/apply_db_functions.py
  ```

### API Documentation (`hoppscotch-integration.sh`)
Generate API documentation and Hoppscotch collections for API testing.

```bash
# Export API docs for local backend
./scripts/hoppscotch-integration.sh
# Or using pnpm
pnpm api:export

# Export API docs for development server
./scripts/hoppscotch-integration.sh --url http://192.168.2.201:8000
# Or using pnpm
pnpm api:export:dev

# Export and show import instructions
pnpm api:hoppscotch
```

Generates:
- OpenAPI specification in JSON format
- Hoppscotch environment configuration
- Import guide for API testing tools

### Archived Scripts (`archived/`)
Scripts that are no longer actively used but kept for reference. See `archived/README.md` for details.

## 🚀 Quick Start Commands

For convenience, most scripts are also available as pnpm commands:

```bash
# Development setup
pnpm setup:dev              # Run setup-dev.sh
pnpm setup:pre-commit       # Run setup-pre-commit.sh

# Testing
pnpm test                    # Run tests
pnpm test:structure          # Test project structure

# Infrastructure management
pnpm infra:up                # Start all services locally
pnpm infra:down              # Stop all services
pnpm infra:deploy            # Deploy to dev server
pnpm check:services          # Check service health

# Monitoring
pnpm logs:remote             # View remote logs
pnpm backup:dev              # Backup development data
```

## Environment Variables

All deployment and monitoring scripts support these environment variables:

- `DEV_SERVER`: Target server IP (default: 192.168.2.201)
- `TEST_MACHINE_IP`: Test server IP (default: 192.168.2.202)
- `DEV_USER`: SSH user (default: zhiyue)

## Requirements

- SSH access to development/test servers
- Docker and Docker Compose on target servers
- Node.js for health check scripts
- Python 3.11+ with uv for development scripts
- Proper environment files (.env.infrastructure, .env.backend, etc.)

## Troubleshooting

### SSH Connection Failed
- Ensure you have SSH key access to the target server
- Check network connectivity
- Verify SSH user has necessary permissions

### Service Health Checks Fail
- Run `pnpm infra:up` to start services
- Check individual service logs with `pnpm logs:remote -- [service-name]`
- Verify environment variables in `.env.infrastructure`

### Test Failures
- For unit tests: Check Python environment and dependencies
- For integration tests: Ensure test services are running on test server
- Use `--remote` flag for pre-deployed services or `--docker-host` for isolated testing

### Development Environment Issues
- Run `./scripts/development/setup-dev.sh` to reset environment
- Verify Ruff configuration with `./scripts/development/verify-ruff.sh`
- Check pre-commit hooks with `pre-commit run --all-files`