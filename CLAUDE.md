# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Development Guidelines

## Philosophy

### Core Beliefs

- **Incremental progress over big bangs** - Small changes that compile and pass
  tests
- **Learning from existing code** - Study and plan before implementing
- **Pragmatic over dogmatic** - Adapt to project reality
- **Clear intent over clever code** - Be boring and obvious

### Simplicity Means

- Single responsibility per function/class
- Avoid premature abstractions
- No clever tricks - choose the boring solution
- If you need to explain it, it's too complex

## Process

### 1. Planning & Staging

Break complex work into 3-5 stages. Document in `IMPLEMENTATION_PLAN.md`:

```markdown
## Stage N: [Name]

**Goal**: [Specific deliverable] **Success Criteria**: [Testable outcomes]
**Tests**: [Specific test cases] **Status**: [Not Started|In Progress|Complete]
```

- Update status as you progress
- Remove file when all stages are done

### 2. Implementation Flow

1. **Understand** - Study existing patterns in codebase
2. **Test** - Write test first (red)
3. **Implement** - Minimal code to pass (green)
4. **Refactor** - Clean up with tests passing
5. **Commit** - With clear message linking to plan

### 3. When Stuck (After 3 Attempts)

**CRITICAL**: Maximum 3 attempts per issue, then STOP.

1. **Document what failed**:
   - What you tried
   - Specific error messages
   - Why you think it failed

2. **Research alternatives**:
   - Find 2-3 similar implementations
   - Note different approaches used

3. **Question fundamentals**:
   - Is this the right abstraction level?
   - Can this be split into smaller problems?
   - Is there a simpler approach entirely?

4. **Try different angle**:
   - Different library/framework feature?
   - Different architectural pattern?
   - Remove abstraction instead of adding?

## Technical Standards

### Architecture Principles

- **Composition over inheritance** - Use dependency injection
- **Interfaces over singletons** - Enable testing and flexibility
- **Explicit over implicit** - Clear data flow and dependencies
- **Test-driven when possible** - Never disable tests, fix them

### Code Quality

- **Every commit must**:
  - Compile successfully
  - Pass all existing tests
  - Include tests for new functionality
  - Follow project formatting/linting

- **Before committing**:
  - Run formatters/linters
  - Self-review changes
  - Ensure commit message explains "why"

### Error Handling

- Fail fast with descriptive messages
- Include context for debugging
- Handle errors at appropriate level
- Never silently swallow exceptions

## Decision Framework

When multiple valid approaches exist, choose based on:

1. **Testability** - Can I easily test this?
2. **Readability** - Will someone understand this in 6 months?
3. **Consistency** - Does this match project patterns?
4. **Simplicity** - Is this the simplest solution that works?
5. **Reversibility** - How hard to change later?

## Project Integration

### Learning the Codebase

- Find 3 similar features/components
- Identify common patterns and conventions
- Use same libraries/utilities when possible
- Follow existing test patterns

### Tooling

- Use project's existing build system
- Use project's test framework
- Use project's formatter/linter settings
- Don't introduce new tools without strong justification

## Quality Gates

### Definition of Done

- [ ] Tests written and passing
- [ ] Code follows project conventions
- [ ] No linter/formatter warnings
- [ ] Commit messages are clear
- [ ] Implementation matches plan
- [ ] No TODOs without issue numbers

### Test Guidelines

- Test behavior, not implementation
- One assertion per test when possible
- Clear test names describing scenario
- Use existing test utilities/helpers
- Tests should be deterministic

## Important Reminders

**NEVER**:

- Use `--no-verify` to bypass commit hooks
- Disable tests instead of fixing them
- Commit code that doesn't compile
- Make assumptions - verify with existing code

**ALWAYS**:

- Commit working code incrementally
- Update plan documentation as you go
- Learn from existing implementations
- Stop after 3 failed attempts and reassess

# Project-Specific Information

## Architecture Overview

InfiniteScribe is an AI-powered novel writing platform built as a monorepo:

- **Backend**: Python 3.11 + FastAPI + SQLAlchemy (see `apps/backend/CLAUDE.md`)
- **Frontend**: React 18 + TypeScript + Vite (see `apps/frontend/CLAUDE.md`)
- **Databases**: PostgreSQL, Redis, Neo4j, Milvus
- **Infrastructure**: Docker Compose with multi-environment support

### Monorepo Structure
```
infinite-scribe/
├── apps/
│   ├── backend/          # Python FastAPI backend (see apps/backend/CLAUDE.md)
│   └── frontend/         # React TypeScript frontend (see apps/frontend/CLAUDE.md)
├── deploy/               # Docker Compose configurations and environment files
│   ├── docker-compose.yml
│   ├── environments/     # Environment configuration files (.env.*)
│   └── init/            # Initialization scripts
├── docs/                # Project documentation
└── scripts/             # Development and deployment scripts (see @scripts/README.md)
```

## Essential Commands

### 🎉 新的统一命令系统

**基础设施管理** (替代了 6+ 个旧命令):
```bash
pnpm infra up                        # 启动本地基础设施服务
pnpm infra down                      # 停止本地基础设施服务
pnpm infra deploy --local            # 本地部署基础设施
pnpm infra deploy                    # 部署到开发服务器
pnpm infra status                    # 检查服务状态
```

**应用部署** (替代了 9+ 个旧命令):
```bash
pnpm app                             # 部署所有应用服务
pnpm app --build                     # 构建并部署所有应用
pnpm app --type backend              # 只部署后端服务
pnpm app --service api-gateway       # 只部署API网关
```

### 开发命令
```bash
# 后端开发
pnpm backend:run                     # 启动API网关
pnpm backend:lint                    # 后端代码检查
pnpm backend:test:unit               # 后端单元测试

# 前端开发
pnpm frontend:run                    # 启动前端开发服务器
pnpm frontend:test                   # 前端测试

# 测试 (Docker-based)
pnpm test:all                        # 所有测试 (容器中)
pnpm test:coverage                   # 带覆盖率的测试
```

## Development Environment

### Environment Management
```bash
pnpm env:local          # Local development (default)
pnpm env:dev           # Development server (192.168.2.201)
pnpm env:test          # Test environment (192.168.2.202)
pnpm env:show          # Show current environment
```

### Infrastructure Services
```bash
pnpm infra up                    # Start all services
pnpm infra down                  # Stop all services  
pnpm infra status                # Service status
pnpm check:services              # Health check
```

#### Service Endpoints
- PostgreSQL: localhost:5432 (postgres/postgres)
- Redis: localhost:6379
- Neo4j: http://localhost:7474 (neo4j/password)
- MinIO: http://localhost:9001 (admin/password)
- Prefect: http://localhost:4200

### Package Management
- **Backend**: `uv` (Python 3.11)
- **Frontend**: `pnpm` (Node.js 20+)
- **Monorepo**: pnpm workspaces

## Development Workflow

### 1. Feature Development
1. Check existing patterns in relevant app directory
2. Create `IMPLEMENTATION_PLAN.md` for complex features (3-5 stages)
3. Follow test-driven development when possible
4. See app-specific CLAUDE.md for detailed guidance

### 2. Quality Gates
- All commits must pass lint/format/typecheck
- Include tests for new functionality
- Follow existing code patterns
- See `apps/*/CLAUDE.md` for specific standards

### 3. Testing Strategy
- **Local**: Unit tests during development
- **CI/CD**: Integration tests on test machine (192.168.2.202)
- **Production**: Deploy to development server (192.168.2.201)

## Common Development Tasks

### Starting New Feature
1. Identify if it's backend, frontend, or full-stack
2. Read relevant `apps/*/CLAUDE.md` for specific guidance
3. Create implementation plan if complex
4. Follow app-specific development patterns

### Cross-App Development
- **API Changes**: Update backend first, then frontend
- **Type Sharing**: Use consistent naming between backend schemas and frontend types
- **Testing**: Test integration points thoroughly

### Documentation
- **Backend-specific**: See `apps/backend/CLAUDE.md`
- **Frontend-specific**: See `apps/frontend/CLAUDE.md`
- **Architecture**: See `docs/architecture/`
- **API**: See `api-docs/`

## Troubleshooting

### Common Issues
- **Service connectivity**: Run `pnpm check:services`
- **Environment problems**: Check `pnpm env:show` and switch if needed
- **Build failures**: Try `pnpm infra down` then `pnpm infra up` to rebuild
- **Test failures**: Use Docker containers (`pnpm test:all`)

### Getting Help
- **Backend issues**: Check `apps/backend/CLAUDE.md` and `apps/backend/docs/`
- **Frontend issues**: Check `apps/frontend/CLAUDE.md`
- **Infrastructure**: Check `docs/guides/deployment/`
