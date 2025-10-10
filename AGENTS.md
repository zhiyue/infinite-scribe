# Repository Guidelines

## Project Structure & Module Organization
The workspace is a pnpm monorepo. Backend sources live in `apps/backend/src/` (FastAPI agents under `src/agents/**`), with unit and integration suites in `apps/backend/tests/unit` and `apps/backend/tests/integration`. The React frontend resides in `apps/frontend/src/`, and Playwright specs sit in `apps/frontend/e2e`. Shared automation and deployment helpers stay in the repo root and `scripts/`.

## Build, Test, and Development Commands
- `pnpm install`: bootstrap all workspace dependencies.
- `pnpm backend run` / `pnpm frontend run`: start FastAPI on :8000 and Vite on :5173.
- `pnpm backend test`, `pnpm frontend test`, `pnpm frontend e2e`: execute pytest, Vitest, and Playwright suites (append `uv run pytest --cov=src` for coverage reports).
- `pnpm backend lint`, `pnpm frontend lint`, `pnpm format`: apply Ruff, ESLint, and Prettier.
- `make dev`, `make test-all`: orchestrate common local development and CI-equivalent workflows.

## Coding Style & Naming Conventions
Python modules follow Ruff formatting and mypy typing with snake_case identifiers. TypeScript honors ESLint + Prettier; components use `PascalCase.tsx`, hooks `useName.ts`, and tests `*.test.ts(x)`. Favor repository and strategy patterns, inject dependencies for testability, and keep functions concise with meaningful names.

## Testing Guidelines
Backend tests run with pytest (`pnpm backend test` or `uv run pytest`), and coverage targets `src`. Frontend unit tests use Vitest, while end-to-end coverage relies on Playwright. Name Python files `test_*.py` and colocate frontend specs as `*.test.ts(x)`. Keep scenarios deterministic and add tests for every new behavior or regression fix.

## Commit & Pull Request Guidelines
Use Conventional Commits (e.g., `feat(auth): add password reset flow`). Each PR should link issues, describe intent, attach UI evidence when relevant, and document API changes. Before pushing, run `pre-commit run --all-files`, linting commands, and the pertinent test suites.

## Security & Configuration Tips
Never commit secrets. Mirror configuration via `apps/backend/.env.example` and `deploy/environments`. Validate services with `pnpm infra status`, and run `gitleaks` before shipping sensitive work.

## Agent-Specific Instructions
Create new agents under `apps/backend/src/agents/<agent_id>/` using snake_case IDs, register implementations in `registry.py`, and inherit from `BaseAgent`. Emit envelopes using the canonical `system` / `data` / `schema_version` layers and honor Kafka routing keys defined in settings.

## Communication & Localization
默认对用户输出简体中文，除非用户明确改用其他语言；框架名、协议名等专业术语保持英文，必要时在括号补充说明。内部日志、提交信息继续沿用既有英文规范。

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
