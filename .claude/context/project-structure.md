---
created: 2025-08-28T12:10:36Z
last_updated: 2025-08-28T12:10:36Z
version: 1.0
author: Claude Code PM System
---

# Project Structure

## Monorepo Architecture

InfiniteScribe follows a monorepo structure with clear separation between frontend, backend, and infrastructure components.

```
infinite-scribe/
├── apps/                     # Application components
│   ├── backend/              # Python FastAPI backend
│   │   ├── src/             # Source code
│   │   ├── tests/           # Test suites (unit, integration)
│   │   ├── pyproject.toml   # Python dependencies
│   │   └── CLAUDE.md        # Backend-specific guidelines
│   └── frontend/            # React TypeScript frontend
│       ├── src/             # Source code
│       ├── public/          # Static assets
│       ├── package.json     # Node dependencies
│       └── CLAUDE.md        # Frontend-specific guidelines
├── deploy/                   # Infrastructure & deployment
│   ├── docker-compose.yml   # Multi-service orchestration
│   ├── environments/        # Environment configurations
│   └── init/               # Database initialization scripts
├── scripts/                  # Development & deployment automation
│   ├── run.js              # Unified parameterized command system
│   ├── deploy/             # Deployment scripts
│   └── ops/                # Operations scripts
├── docs/                     # Project documentation
│   ├── architecture/        # System design documents
│   ├── guides/             # Development guides
│   └── api/                # API documentation
├── api-docs/                # API specifications
└── .claude/                 # Claude Code context and rules
    ├── context/            # Project context files
    └── rules/              # Development rules
```

## Key Directories

### Applications (`/apps`)

**Backend (`/apps/backend`)**
- Python 3.11 + FastAPI + SQLAlchemy
- Follows clean architecture with service layer
- Comprehensive test suite with pytest
- Authentication system with JWT tokens

**Frontend (`/apps/frontend`)**
- React 18 + TypeScript + Vite
- Modern component-based architecture  
- Material-UI or similar design system
- TypeScript strict mode enabled

### Infrastructure (`/deploy`)

**Environment Management**
- Multi-environment support (local, dev, test, prod)
- Docker Compose orchestration
- Environment-specific configuration files
- Database initialization scripts

**Services Stack**
- PostgreSQL (primary database)
- Redis (caching & sessions)
- Neo4j (graph relationships)
- Milvus (vector database)
- MinIO (object storage)
- Prefect (workflow orchestration)

### Automation (`/scripts`)

**Unified Command System**
- Parameterized script system via `run.js`
- Development operations automation
- Deployment and infrastructure management
- Health checking and monitoring scripts

### Development Tools

**Configuration Files**
- `package.json` - Root workspace configuration
- `pnpm-workspace.yaml` - Workspace definitions
- `tsconfig.base.json` - TypeScript base configuration
- `.eslintrc.js` - ESLint configuration
- `CLAUDE.md` - Development guidelines

## File Organization Patterns

### Naming Conventions
- **Directories**: kebab-case (`user-service`, `auth-middleware`)
- **Files**: kebab-case for config, camelCase for code
- **Components**: PascalCase (`UserProfile.tsx`)
- **Services**: kebab-case (`user-service.py`)

### Module Structure
- Each major feature gets its own directory
- Clear separation between business logic and infrastructure
- Consistent import/export patterns
- Co-located tests with source code

### Documentation Organization
- Feature docs alongside implementation
- API docs generated from code
- Architecture decisions recorded in `/docs`
- Component-specific docs in respective CLAUDE.md files

## Development Workflow Integration

### Git Integration
- Conventional commit messages
- Pre-commit hooks for code quality
- Branch-based development workflow
- Automated testing on commits

### Package Management
- pnpm workspaces for frontend
- uv for Python backend dependencies
- Lockfiles committed for reproducibility
- Development vs production dependency separation

## Build & Deploy Structure

### Local Development
- Hot reload for both frontend and backend
- Containerized infrastructure services
- Health check endpoints for all services
- Comprehensive logging and debugging

### Production Deployment
- Multi-stage Docker builds
- Environment-specific configurations
- Automated database migrations
- Service health monitoring