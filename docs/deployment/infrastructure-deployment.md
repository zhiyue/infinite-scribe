# Infrastructure Deployment Guide

## Overview

InfiniteScribe's infrastructure can be deployed in three different environments:
- **Local Development**: Docker Compose on your machine
- **Development Server**: Shared infrastructure on 192.168.2.201
- **Test Environment**: Isolated containers on test machine

## Prerequisites

- Docker and Docker Compose installed
- Access to environment configuration files
- SSH access to remote servers (for dev/test deployment)

## Environment Configuration

### 1. Initial Setup

```bash
# First time setup - consolidate existing .env files
pnpm env:consolidate

# Copy and configure environment files
cp .env.example .env.local   # For local development
cp .env.example .env.dev     # For dev server
cp .env.example .env.test    # For test environment

# Edit the files with appropriate values
```

### 2. Switch to Target Environment

```bash
# For local development
pnpm env:local

# For development server
pnpm env:dev

# For test environment
pnpm env:test

# Verify current environment
pnpm env:show
```

## Deployment Methods

### Local Development Deployment

Deploy infrastructure locally using Docker Compose:

```bash
# Method 1: Using deployment script
./scripts/deployment/deploy-infrastructure.sh --local

# Method 2: Using pnpm command
pnpm infra:up

# Method 3: Direct docker-compose
docker compose --env-file .env.local up -d
```

**Features:**
- All services run on localhost
- Uses `.env.local` configuration
- Data persisted in local Docker volumes
- Ideal for individual development

### Development Server Deployment

Deploy to the shared development server (192.168.2.201):

```bash
# Deploy to dev server (default behavior)
./scripts/deployment/deploy-infrastructure.sh

# This will:
# 1. Sync project files to 192.168.2.201
# 2. Use .env.dev configuration
# 3. Start services with docker-compose on remote server
```

**Features:**
- Services accessible at 192.168.2.201
- Shared development database
- Persistent infrastructure for team use
- **NOT for running tests**

### Manual Deployment Steps

If you prefer manual deployment:

```bash
# 1. SSH to development server
ssh zhiyue@192.168.2.201

# 2. Navigate to project
cd ~/workspace/mvp/infinite-scribe

# 3. Ensure correct environment
ln -sf .env.dev .env

# 4. Start services
docker compose up -d

# 5. Verify services
docker compose ps
```

## Services Overview

### Core Services

| Service | Local Port | Dev Server Port | Description |
|---------|-----------|-----------------|-------------|
| PostgreSQL | 5432 | 5432 | Main database |
| Redis | 6379 | 6379 | Cache & session store |
| Neo4j | 7687/7474 | 7687/7474 | Graph database |

### Optional Services

| Service | Local Port | Dev Server Port | Description |
|---------|-----------|-----------------|-------------|
| Milvus | 19530 | 19530 | Vector database |
| MinIO | 9000/9001 | 9000/9001 | Object storage |
| Kafka | 9092 | 9092 | Message broker |
| Prefect | 4200 | 4200 | Workflow orchestration |

## Service Management

### Basic Commands

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View service status
docker compose ps

# View logs
docker compose logs -f [service-name]

# Restart a service
docker compose restart [service-name]
```

### Health Checks

```bash
# Check all services (from local machine)
pnpm check:services

# Check specific service
docker compose exec [service-name] [health-check-command]
```

## Data Persistence

All data is persisted using Docker volumes:

```yaml
volumes:
  postgres-data:     # PostgreSQL databases
  redis-data:        # Redis persistence
  neo4j-data:        # Neo4j graph data
  milvus-data:       # Vector embeddings
  minio-data:        # Object storage
  kafka-data:        # Message data
  prefect-data:      # Workflow metadata
```

### Backup Procedures

```bash
# Backup PostgreSQL
docker compose exec postgres pg_dump -U postgres infinite_scribe > backup.sql

# Backup all volumes
docker run --rm -v infinite-scribe_postgres-data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz -C /data .
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check port usage
   lsof -i :5432  # Example for PostgreSQL
   ```

2. **Service Won't Start**
   ```bash
   # Check logs
   docker compose logs [service-name]

   # Check resources
   docker system df
   ```

3. **Connection Issues**
   - Verify environment variables in active .env file
   - Check firewall rules
   - Ensure services are healthy

### Remote Access Issues

For development server:
```bash
# Test connectivity
telnet 192.168.2.201 5432

# Check SSH access
ssh zhiyue@192.168.2.201 "docker ps"
```

## Security Considerations

1. **Passwords**: All default passwords should be changed for production
2. **Network**: Services are exposed on all interfaces (0.0.0.0)
3. **Firewall**: Consider implementing firewall rules for production
4. **SSL/TLS**: Enable encryption for production deployments

## Maintenance

### Update Services

```bash
# Pull latest images
docker compose pull

# Recreate containers with new images
docker compose up -d --force-recreate
```

### Clean Up

```bash
# Remove stopped containers
docker compose rm -f

# Clean up volumes (WARNING: Data loss!)
docker compose down -v

# System cleanup
docker system prune -a
```

## Next Steps

1. Deploy infrastructure using appropriate method
2. Run health checks to verify services
3. Configure application to use the services
4. Set up monitoring and alerting (production)

For detailed service configurations, see:
- [Environment Variables Guide](./environment-variables.md)
- [Environment Structure](./environment-structure.md)
- [Development Server Setup](./development-server-setup.md)
