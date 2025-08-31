# InfiniteScribe Project Overview

## Project Purpose
InfiniteScribe is an AI-powered novel writing platform that uses multi-agent collaboration to assist writers in creating novels. It provides intelligent writing assistance through specialized AI agents for different aspects of novel writing (worldbuilding, story direction, character development, etc.).

## Tech Stack

### Monorepo Structure
- **Package Manager**: pnpm with workspaces
- **Architecture**: Microservices with shared infrastructure
- **Development**: Docker Compose with multi-environment support

### Backend (Python 3.11 + FastAPI)
- **Framework**: FastAPI with async/await
- **ORM**: SQLAlchemy 2.0 with typed relationships
- **Package Manager**: `uv` for dependency management
- **Code Quality**: Ruff (linting/formatting), mypy (type checking)
- **Testing**: pytest with testcontainers for integration tests
- **Databases**: PostgreSQL, Redis, Neo4j, Milvus (vector DB)

### Frontend (React 18 + TypeScript)
- **Framework**: React 18.2 with TypeScript 5.2
- **Build Tool**: Vite 7.0
- **State Management**: TanStack Query + Zustand
- **UI Library**: Shadcn UI with Tailwind CSS
- **Testing**: Vitest (unit) + Playwright (E2E)

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Environments**: Local, Development (192.168.2.201), Test (192.168.2.202)
- **Services**: PostgreSQL, Redis, Neo4j, MinIO, Prefect
- **Authentication**: JWT tokens with Redis session management

## Key Architecture Patterns

### Backend
- **Service Layer Pattern**: Business logic in `common/services/`
- **CQRS Schema Pattern**: Separate Create/Read/Update schemas
- **Agent Architecture**: BaseAgent pattern for AI agents
- **Dependency Injection**: Services injected into API routes

### Frontend  
- **Component-Based**: Reusable UI components with Shadcn UI
- **Server State**: TanStack Query for API interactions
- **Client State**: Zustand for local state
- **Type Safety**: Full TypeScript coverage
- **Authentication**: Token-based with automatic refresh