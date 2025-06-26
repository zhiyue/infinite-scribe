# InfiniteScribe Scripts

This directory contains utility scripts for managing the InfiniteScribe development environment.

## Available Scripts

### Service Management

#### `check-services.js` / `check-services-simple.js`
Check the health status of all InfiniteScribe services.

```bash
# Simple connectivity check (no dependencies)
pnpm check:services

# Full health check with detailed service info (requires npm packages)
pnpm check:services:full
```

### Deployment Scripts

#### `deploy-to-dev.sh`
Deploy the InfiniteScribe project to the development server.

```bash
# Deploy to default server (192.168.2.201)
pnpm deploy:dev

# Deploy to custom server
DEV_SERVER=your.server.ip pnpm deploy:dev
```

#### `deploy-infrastructure.sh`
Deploy only the infrastructure services using Docker Compose.

```bash
# Deploy to remote server
pnpm infra:deploy

# Deploy locally
pnpm infra:deploy:local
```

### Monitoring Scripts

#### `remote-logs.sh`
View logs from services running on the development server.

```bash
# View all logs (last 100 lines)
pnpm logs:remote

# Follow specific service logs
pnpm logs:remote -- -f postgres

# View last 50 lines of Kafka logs
pnpm logs:remote -- -n 50 kafka

# Get help
./scripts/remote-logs.sh --help
```

### Backup Scripts

#### `backup-dev-data.sh`
Create a complete backup of all development data.

```bash
# Create backup (saved to ./backups/)
pnpm backup:dev

# Backup with custom server
DEV_SERVER=your.server.ip pnpm backup:dev
```

Backs up:
- PostgreSQL databases (all)
- Redis data
- Neo4j graph database
- MinIO object storage (novels bucket)
- Environment configuration files

### Environment Scripts

#### `migrate-env-structure.sh`
Migrate from single `.env` file to layered environment structure.

```bash
./scripts/migrate-env-structure.sh
```

### Testing Scripts

#### `test-project-structure.js`
Validate the project structure meets requirements.

```bash
pnpm test:structure
```

## Environment Variables

All deployment scripts support these environment variables:

- `DEV_SERVER`: Target server IP (default: 192.168.2.201)
- `DEV_USER`: SSH user (default: zhiyue)

## Requirements

- SSH access to development server
- Docker and Docker Compose on development server
- Node.js for health check scripts
- Proper environment files (.env.infrastructure)

## Troubleshooting

### SSH Connection Failed
- Ensure you have SSH key access to the development server
- Check network connectivity
- Verify SSH user has necessary permissions

### Service Health Checks Fail
- Run `pnpm infra:up` to start services
- Check individual service logs with `pnpm logs:remote -- [service-name]`
- Verify environment variables in `.env.infrastructure`

### Backup Issues
- Ensure sufficient disk space on both local and remote machines
- Check that all services are running before backup
- Verify Docker container names match expected values