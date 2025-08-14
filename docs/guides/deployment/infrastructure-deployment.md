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
# First time setup - run development setup script
./scripts/dev/setup-dev.sh

# Create local development environment file
cp .env.example .env.local   # For local development

# Edit the file with appropriate values
# - Add API keys (OPENAI_API_KEY, etc.)
# - Update passwords if needed
```

### 2. Environment Overview

InfiniteScribe now uses a simplified deployment approach:

- **Local Development**: Use `pnpm infra up` for local Docker services
- **Development Server**: Use `pnpm infra deploy` to deploy to 192.168.2.201
- **Test Environment**: Tests run on dedicated test machine (192.168.2.202)

```bash
# Check which environment files exist
ls -la deploy/environments/
```

## Deployment Methods

### Local Development Deployment

Deploy infrastructure locally using Docker Compose:

```bash
# Method 1: Using new unified command (Recommended)
pnpm infra up

# Method 2: Using deployment script with local flag
pnpm infra deploy --local

# Method 3: Direct docker-compose
docker compose --env-file deploy/environments/.env.local up -d
```

**Features:**
- All services run on localhost
- Uses `.env.local` configuration
- Data persisted in local Docker volumes
- Ideal for individual development

### Development Server Deployment

Deploy to the shared development server (192.168.2.201):

```bash
# Deploy infrastructure to development server (Recommended)
pnpm infra deploy

# This will:
# 1. Sync project files to 192.168.2.201
# 2. Use deploy/environments/.env.dev configuration
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
pnpm ssh:dev

# 2. Navigate to project
cd ~/workspace/mvp/infinite-scribe

# 3. Start services using new structure
docker compose --env-file deploy/environments/.env.dev up -d

# 4. Verify services
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
# Using new unified commands (Recommended)
pnpm infra up                              # Start local services
pnpm infra down                            # Stop local services  
pnpm infra status                          # View service status
pnpm infra logs --service [service-name]   # View specific service logs
pnpm infra logs --follow                   # Follow all logs

# Or using Docker commands directly
docker compose up -d
docker compose down
docker compose ps
docker compose logs -f [service-name]
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
