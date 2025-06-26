# Environment Configuration Sync

## Dev Server Configuration

The development server (192.168.2.201) has been configured with the following credentials:

### Infrastructure Services

| Service | Username | Password | Port |
|---------|----------|----------|------|
| PostgreSQL | postgres | devPostgres123! | 5432 |
| PostgreSQL (Prefect) | prefect | devPrefect123! | 5432 |
| Redis | - | devRedis123! | 6379 |
| Neo4j | neo4j | devNeo4j123! | 7687 |
| MinIO | devMinioAccess | devMinioSecret123! | 9000 |

### Updated Files

1. **`.env.infrastructure`** - Updated with dev server credentials
   - PostgreSQL passwords
   - Redis password
   - Neo4j password
   - MinIO access keys
   - Prefect PostgreSQL credentials

2. **`.env.backend.local`** - Created for local development
   - Contains all connection strings pointing to dev server
   - Use this when running backend services locally
   - Copy to `.env.backend` when developing locally

### Environment Usage Guide

#### For Docker Deployment (on dev server)
- Use `.env.infrastructure` - Docker Compose reads this
- Services use internal Docker network names (postgres, redis, etc.)
- `.env.backend.example` is configured for Docker networking

#### For Local Development (on your machine)
- Use `.env.backend.local` - Points to dev server services
- Frontend uses `.env.frontend` - Already configured for dev server
- All services accessible via 192.168.2.201

### Quick Start for Local Development

```bash
# Backend development
cp .env.backend.local .env.backend
cd apps/api-gateway
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend development
cp .env.frontend.example .env.frontend
cd apps/frontend
pnpm install
pnpm dev
```

### Security Notes

- These are development credentials only
- Do not use these passwords in production
- Keep `.env.backend.local` in .gitignore (already added)
- Production credentials should be managed separately

### Service Access URLs

All services are accessible from the internal network:

- PostgreSQL: `postgresql://postgres:devPostgres123!@192.168.2.201:5432/infinite_scribe`
- Redis: `redis://:devRedis123!@192.168.2.201:6379`
- Neo4j Bolt: `bolt://neo4j:devNeo4j123!@192.168.2.201:7687`
- Neo4j Browser: http://192.168.2.201:7474
- MinIO Console: http://192.168.2.201:9001
- Prefect UI: http://192.168.2.201:4200