# Infrastructure Quick Start Guide

## First Time Setup

```bash
# 1. Consolidate existing .env files (if upgrading)
pnpm env:consolidate

# 2. Create your environment files
cp .env.example .env.local
cp .env.example .env.dev
cp .env.example .env.test

# 3. Edit the files with your credentials
# - Add API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)
# - Update passwords if needed
```

## Choose Your Environment

### For Local Development

```bash
# Switch to local environment
pnpm env:local

# Start infrastructure locally
pnpm infra:up

# Verify services
pnpm check:services
```

### For Development Server

```bash
# Switch to dev environment
pnpm env:dev

# Deploy to development server (192.168.2.201)
pnpm infra:deploy

# SSH to dev server
pnpm ssh:dev

# Check services remotely
pnpm check:services
```

### For Testing

```bash
# Switch to test environment
pnpm env:test

# Run tests with Docker containers
./scripts/run-tests.sh --all --docker-host

# Use custom test machine
export TEST_MACHINE_IP=192.168.2.100
./scripts/run-tests.sh --all --docker-host
```

## Common Commands

### Environment Management
- `pnpm env:show` - Show current environment
- `pnpm env:local` - Switch to local
- `pnpm env:dev` - Switch to dev server
- `pnpm env:test` - Switch to test

### Infrastructure Control
- `pnpm infra:up` - Start services
- `pnpm infra:down` - Stop services
- `pnpm infra:logs` - View logs
- `pnpm check:services` - Health check

### Remote Access
- `pnpm ssh:dev` - SSH to dev server
- `pnpm ssh:test` - SSH to test machine
- `pnpm deploy:dev` - Deploy to dev
- `pnpm logs:remote` - View remote logs

## Service URLs

### Local Development
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Neo4j UI: `http://localhost:7474`
- MinIO Console: `http://localhost:9001`
- Prefect UI: `http://localhost:4200`

### Development Server
- PostgreSQL: `192.168.2.201:5432`
- Redis: `192.168.2.201:6379`
- Neo4j UI: `http://192.168.2.201:7474`
- MinIO Console: `http://192.168.2.201:9001`
- Prefect UI: `http://192.168.2.201:4200`

## Troubleshooting

### Check Current Environment
```bash
pnpm env:show
ls -la .env
```

### Service Won't Start
```bash
# Check logs
docker compose logs [service-name]

# Check ports
lsof -i :5432  # PostgreSQL example
```

### Connection Issues
1. Verify environment: `pnpm env:show`
2. Check service health: `pnpm check:services`
3. Review `.env.*` file for correct hosts/ports

### Reset Everything
```bash
# Stop all services
docker compose down

# Remove volumes (WARNING: data loss)
docker compose down -v

# Start fresh
pnpm infra:up
```

## Next Steps

1. **Read the full guides**:
   - [Infrastructure Deployment](./infrastructure-deployment.md)
   - [Environment Variables](./environment-variables.md)
   - [Development Server Setup](./development-server-setup.md)

2. **Start developing**:
   ```bash
   cd apps/backend
   uv run uvicorn src.main:app --reload
   ```

3. **Run tests**:
   ```bash
   pnpm test:all
   ```
