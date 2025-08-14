# Infrastructure Quick Start Guide

> 🚀 **想要更简单的部署方式？** 查看 [DEPLOY_SIMPLE.md](./DEPLOY_SIMPLE.md) - 只需要记住 4 个核心命令！

## First Time Setup

```bash
# 1. Set up development environment
./scripts/dev/setup-dev.sh

# 2. Create local environment file
cp .env.example .env.local

# 3. Edit the file with your credentials
# - Add API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)
# - Update passwords if needed
```

## Choose Your Environment

### For Local Development

```bash
# Start infrastructure locally
pnpm infra up

# Verify services
pnpm check:services
```

### For Development Server

```bash
# Deploy infrastructure to development server (192.168.2.201)
pnpm infra deploy

# Deploy application services
pnpm app

# SSH to dev server
pnpm ssh:dev

# Check services remotely
pnpm check:services
```

### For Testing

```bash
# Run tests with Docker containers
./scripts/test/run-tests.sh --all --docker-host

# Use custom test machine
export TEST_MACHINE_IP=192.168.2.100
./scripts/test/run-tests.sh --all --docker-host
```

## Common Commands

### Infrastructure Management
- `pnpm infra up` - Start local services
- `pnpm infra down` - Stop local services
- `pnpm infra deploy` - Deploy to dev server
- `pnpm infra logs` - View infrastructure logs
- `pnpm infra status` - Check infrastructure status

### Application Deployment
- `pnpm app` - Deploy all services
- `pnpm app --build` - Build and deploy all services
- `pnpm app --type backend` - Deploy backend services only
- `pnpm app --service api-gateway` - Deploy specific service

### Remote Access & Monitoring
- `pnpm ssh:dev` - SSH to dev server
- `pnpm ssh:test` - SSH to test machine
- `pnpm check:services` - Health check
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
# Stop all local services
pnpm infra down

# Remove volumes (WARNING: data loss)
docker compose --env-file deploy/environments/.env.local down -v

# Start fresh
pnpm infra up
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
