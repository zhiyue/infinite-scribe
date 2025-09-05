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
- Follow SOLID principles and prefer composition over inheritance
- Use dependency injection for testability
- Apply repository pattern for data access and strategy pattern for algorithms

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

- Search codebase first when uncertain
- Write tests for core functionality using TDD approach
- Update documentation when modifying code
- Make atomic commits for each completed feature stage and push

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

- Use descriptive names and avoid abbreviations or magic numbers
- Keep functions under 20 lines and maintain concise files
- Handle all error scenarios with meaningful messages
- Comment "why" not "what"

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

### 🚀 参数化命令系统

**快速开发命令** (推荐用法):

```bash
# 应用开发 (参数化)
pnpm backend install                 # 安装Python依赖
pnpm backend run                     # 启动API网关
pnpm backend lint                    # 代码检查
pnpm frontend run                    # 启动前端开发服务器
pnpm frontend build                  # 构建前端

# 测试 (参数化)
pnpm test all                        # 所有测试 (本地Docker)
pnpm test all --remote               # 远程测试 (192.168.2.202)
pnpm test unit                       # 单元测试
pnpm test coverage                   # 带覆盖率测试

# SSH连接 (参数化)
pnpm ssh dev                         # SSH到开发服务器 (192.168.2.201)
pnpm ssh test                        # SSH到测试服务器 (192.168.2.202)

# 服务检查 (参数化)
pnpm check services                  # 快速健康检查 (本地)
pnpm check services --remote         # 快速健康检查 (开发服务器)
pnpm check services:full             # 完整健康检查 (本地)
pnpm check services:full --remote    # 完整健康检查 (开发服务器)

# API工具 (参数化)
pnpm api export                      # 导出本地API定义
pnpm api export:dev                  # 导出开发环境API定义
```

**基础设施和应用部署** (保持原有):

```bash
# 基础设施管理
pnpm infra up                        # 启动本地基础设施服务
pnpm infra down                      # 停止本地基础设施服务
pnpm infra deploy --local            # 本地部署基础设施
pnpm infra deploy                    # 部署到开发服务器 (192.168.2.201)
pnpm infra status                    # 检查服务状态

# 应用部署
pnpm app                             # 部署所有应用服务
pnpm app --build                     # 构建并部署所有应用
pnpm app --type backend              # 只部署后端服务
pnpm app --service api-gateway       # 只部署API网关
```

**获取命令帮助**:

```bash
pnpm run                             # 主帮助系统
pnpm backend                         # 后端操作帮助
pnpm test                            # 测试操作帮助
pnpm ssh                             # SSH连接帮助
pnpm check                           # 服务检查帮助
```

## Development Environment

### Infrastructure Services

```bash
# 基础设施状态
pnpm infra up                        # 启动所有本地服务
pnpm infra down                      # 停止所有本地服务
pnpm check services                  # 健康检查 (本地, 快速)
pnpm check services:full             # 完整健康检查 (本地)
pnpm check services --remote         # 健康检查 (开发服务器, 快速)
pnpm check services:full --remote    # 完整健康检查 (开发服务器)
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

- **Service connectivity**: Run `pnpm check services` (本地) 或 `pnpm check services --remote` (开发服务器)
- **Build failures**: Try `pnpm infra down` then `pnpm infra up` to rebuild
- **Test failures**: Use Docker containers (`pnpm test all`)
- **Command not found**: Use `pnpm run` to see all available commands or `pnpm <target>` for specific help

### Getting Help

- **Backend issues**: Check `apps/backend/CLAUDE.md` and `apps/backend/docs/`
- **Frontend issues**: Check `apps/frontend/CLAUDE.md`
- **Infrastructure**: Check `docs/guides/deployment/`

> Think carefully and implement the most concise solution that changes as little code as possible.

## USE SUB-AGENTS FOR CONTEXT OPTIMIZATION

### 1. Always use the file-analyzer sub-agent when asked to read files.

The file-analyzer agent is an expert in extracting and summarizing critical information from files, particularly log files and verbose outputs. It provides concise, actionable summaries that preserve essential information while dramatically reducing context usage.

### 2. Always use the code-analyzer sub-agent when asked to search code, analyze code, research bugs, or trace logic flow.

The code-analyzer agent is an expert in code analysis, logic tracing, and vulnerability detection. It provides concise, actionable summaries that preserve essential information while dramatically reducing context usage.


## Philosophy

### Error Handling

- **Fail fast** for critical configuration (missing text model)
- **Log and continue** for optional features (extraction model)
- **Graceful degradation** when external services unavailable
- **User-friendly messages** through resilience layer

### Testing

- Do not use mock services for anything ever.
- Do not move on to the next test until the current test is complete.
- If the test fails, consider checking if the test is structured correctly before deciding we need to refactor the codebase.
- Tests to be verbose so we can use them for debugging.

## Tone and Behavior

- Criticism is welcome. Please tell me when I am wrong or mistaken, or even when you think I might be wrong or mistaken.
- Please tell me if there is a better approach than the one I am taking.
- Please tell me if there is a relevant standard or convention that I appear to be unaware of.
- Be skeptical.
- Be concise.
- Short summaries are OK, but don't give an extended breakdown unless we are working through the details of a plan.
- Do not flatter, and do not give compliments unless I am specifically asking for your judgement.
- Occasional pleasantries are fine.
- Feel free to ask many questions. If you are in doubt of my intent, don't guess. Ask.

## ABSOLUTE RULES:

- NO PARTIAL IMPLEMENTATION
- NO SIMPLIFICATION : no "//This is simplified stuff for now, complete implementation would blablabla"
- NO CODE DUPLICATION : check existing codebase to reuse functions and constants Read files before writing new functions. Use common sense function name to find them easily.
- NO DEAD CODE : either use or delete from codebase completely
- IMPLEMENT TEST FOR EVERY FUNCTIONS
- NO CHEATER TESTS : test must be accurate, reflect real usage and be designed to reveal flaws. No useless tests! Design tests to be verbose so we can use them for debuging.
- NO INCONSISTENT NAMING - read existing codebase naming patterns.
- NO OVER-ENGINEERING - Don't add unnecessary abstractions, factory patterns, or middleware when simple functions would work. Don't think "enterprise" when you need "working"
- NO MIXED CONCERNS - Don't put validation logic inside API handlers, database queries inside UI components, etc. instead of proper separation
- NO RESOURCE LEAKS - Don't forget to close database connections, clear timeouts, remove event listeners, or clean up file handles
- FILE SIZE LIMITS - Every .py file must not exceed 400 lines. If a file exceeds 400 lines, use the code-simplifier agent to refactor it into smaller, focused modules
