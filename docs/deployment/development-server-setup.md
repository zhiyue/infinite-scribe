# Development Server Setup Guide

## Server Information

- **IP Address**: 192.168.2.201
- **User**: zhiyue
- **Project Path**: ~/workspace/mvp/infinite-scribe/
- **Environment**: Uses `.env.dev` configuration
- **Purpose**: Shared development infrastructure (NOT for testing)

## Quick Deployment

### From Local Machine

```bash
# Ensure you have .env.dev configured
pnpm env:dev

# Deploy to development server
./scripts/deployment/deploy-infrastructure.sh

# Or manually deploy
pnpm infra:deploy
```

### On Development Server

```bash
# SSH to server
ssh zhiyue@192.168.2.201

# Navigate to project
cd ~/workspace/mvp/infinite-scribe

# Ensure using dev environment
ln -sf .env.dev .env

# Start services
docker compose up -d
```

## Deployed Services

### Core Database Services

1. **PostgreSQL 16**
   - Port: 5432
   - Database: infinite_scribe
   - User: postgres
   - Password: devPostgres123!
   - Connection: `postgresql://postgres:devPostgres123!@192.168.2.201:5432/infinite_scribe`

2. **Redis 7.2**
   - Port: 6379
   - Password: devRedis123!
   - Memory limit: 512MB (LRU policy)
   - Connection: `redis://:devRedis123!@192.168.2.201:6379/0`

3. **Neo4j 5.x**
   - Bolt port: 7687
   - HTTP port: 7474
   - User: neo4j
   - Password: devNeo4j123!
   - Web UI: http://192.168.2.201:7474
   - Connection: `bolt://neo4j:devNeo4j123!@192.168.2.201:7687`

### Optional Services

4. **Milvus 2.6.0** (Vector Database)
   - Port: 19530
   - Metrics port: 9091
   - Dependencies: etcd, MinIO
   - Status: Available when enabled

5. **Apache Kafka 3.7** (Message Broker)
   - External port: 9092
   - Internal port: 29092
   - Bootstrap servers: `192.168.2.201:9092`
   - Dependencies: Zookeeper

6. **MinIO** (Object Storage)
   - API port: 9000
   - Console port: 9001
   - Access key: devMinioAccess
   - Secret key: devMinioSecret123!
   - Web UI: http://192.168.2.201:9001

7. **Prefect 3.x** (Workflow Orchestration)
   - API/UI port: 4200
   - Web UI: http://192.168.2.201:4200
   - API endpoint: http://192.168.2.201:4200/api
   - Components:
     - prefect-api: API server
     - prefect-background-service: Background scheduler
     - prefect-worker: Task executor

## Service Management

### Essential Commands

```bash
# View all services
docker compose ps

# Start specific service
docker compose up -d [service-name]

# Stop specific service
docker compose stop [service-name]

# Restart service
docker compose restart [service-name]

# View logs
docker compose logs -f [service-name]

# Execute command in service
docker compose exec [service-name] [command]
```

### Health Monitoring

From your local machine:
```bash
# Check all services
pnpm check:services

# Check with full details
pnpm check:services:full
```

On the server:
```bash
# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check specific service health
docker inspect [container-name] --format='{{.State.Health.Status}}'
```

## Data Management

### Volume Locations

All data is persisted in Docker volumes:
- `postgres-data`: PostgreSQL databases
- `redis-data`: Redis persistence files
- `neo4j-data`: Neo4j graph database
- `milvus-data`: Vector embeddings
- `minio-data`: Object storage files
- `kafka-data`: Message data
- `prefect-data`: Workflow metadata

### Backup Procedures

```bash
# PostgreSQL backup
docker compose exec postgres pg_dump -U postgres infinite_scribe > infinite_scribe_$(date +%Y%m%d).sql

# Neo4j backup
docker compose exec neo4j neo4j-admin database dump neo4j --to-path=/backups/

# Redis backup
docker compose exec redis redis-cli BGSAVE

# Full volume backup
./scripts/monitoring/backup-dev-data.sh
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs
   docker compose logs [service-name]

   # Check port conflicts
   sudo lsof -i :[port-number]
   ```

2. **Connection refused**
   - Verify service is running: `docker compose ps`
   - Check environment variables in `.env.dev`
   - Ensure firewall allows connections

3. **Kafka connection issues**
   - Kafka uses dual listeners:
     - Internal: `kafka:29092`
     - External: `192.168.2.201:9092`
   - Ensure KAFKA_ADVERTISED_LISTENERS is correctly set

4. **Prefect UI can't connect to API**
   - CORS is configured for all origins
   - API URL should be `http://192.168.2.201:4200/api`

### Resource Monitoring

```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check Docker resource usage
docker system df

# Monitor container resources
docker stats
```

## Security Notes

1. **Current Status**: Development configuration with known passwords
2. **Network**: Services bound to 0.0.0.0 (accessible from network)
3. **Recommendations for production**:
   - Change all default passwords
   - Implement firewall rules
   - Enable SSL/TLS for services
   - Restrict service binding to specific interfaces

## Maintenance Tasks

### Regular Updates

```bash
# Update Docker images
docker compose pull

# Recreate containers with new images
docker compose up -d --force-recreate

# Clean up old images
docker image prune -a
```

### Cleanup Procedures

```bash
# Remove stopped containers
docker compose rm -f

# Clean build cache
docker builder prune

# Full system cleanup (careful!)
docker system prune -a --volumes
```

## Integration with Development

### Backend Configuration

The backend services automatically use development server when:
```bash
# Switch to dev environment locally
pnpm env:dev

# Start backend service
cd apps/backend
uv run uvicorn src.main:app --reload
```

### Environment Variables

Key variables in `.env.dev`:
```bash
POSTGRES_HOST=192.168.2.201
REDIS_HOST=192.168.2.201
NEO4J_HOST=192.168.2.201
# ... all services use 192.168.2.201
```

## Remote Access

### SSH Access
```bash
# Direct SSH
ssh zhiyue@192.168.2.201

# SSH with port forwarding (access services locally)
ssh -L 5432:localhost:5432 zhiyue@192.168.2.201  # PostgreSQL
ssh -L 7474:localhost:7474 zhiyue@192.168.2.201  # Neo4j UI
```

### Using pnpm shortcuts
```bash
# Quick SSH access
pnpm ssh:dev

# Deploy to dev
pnpm deploy:dev

# View remote logs
pnpm logs:remote
```

## Best Practices

1. **Always use `.env.dev`** for development server deployments
2. **Never run tests** against development server services
3. **Coordinate with team** before restarting shared services
4. **Monitor resource usage** regularly
5. **Backup data** before major changes

## Next Steps

1. Configure your local `.env.dev` file
2. Deploy infrastructure: `./scripts/deployment/deploy-infrastructure.sh`
3. Verify services: `pnpm check:services`
4. Start developing with shared infrastructure

For more information:
- [Infrastructure Deployment Guide](./infrastructure-deployment.md)
- [Environment Variables Guide](./environment-variables.md)
- [Environment Structure](./environment-structure.md)
