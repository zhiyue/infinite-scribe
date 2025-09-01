# InfiniteScribe Project Overview

## Purpose
InfiniteScribe is an AI-powered novel writing platform built as a monorepo using multi-agent collaboration. The platform helps users create novels through AI-driven writing assistance and world-building tools.

## Architecture
- **Monorepo Structure**: Apps organized under `apps/` with backend (Python FastAPI) and frontend (React TypeScript)
- **Unified Backend**: Single codebase for all backend services (API Gateway + AI Agents) in `apps/backend/`
- **Flexible Service Selection**: Uses `SERVICE_TYPE` environment variable to determine which service runs
- **Multi-database Setup**: PostgreSQL, Redis, Neo4j, Milvus for different data needs
- **Container-first Development**: Docker Compose for local development and deployment

## Tech Stack
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Pydantic Settings, uv package manager
- **Frontend**: React 18, TypeScript, Vite, pnpm
- **Databases**: PostgreSQL (main), Redis (cache/SSE), Neo4j (graph data), Milvus (vector embeddings)
- **Infrastructure**: Docker Compose, multi-environment support
- **Configuration**: TOML-based with environment variable interpolation

## Key Features
- Multi-agent AI collaboration for novel writing
- Advanced configuration system with TOML + environment variable support
- Unified backend launcher for multiple service types
- Real-time SSE communication
- Comprehensive authentication and session management