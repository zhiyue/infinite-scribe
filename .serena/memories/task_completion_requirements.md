# Task Completion Requirements

## Quality Gates - Definition of Done

Every task must meet these criteria before being considered complete:

### Code Quality Checks
- [ ] **Lint Check**: No linting errors (`pnpm backend lint` / `pnpm frontend lint`)
- [ ] **Format Check**: Code properly formatted (`pnpm backend format` / `pnpm frontend format`)
- [ ] **Type Check**: No TypeScript/mypy errors (`pnpm backend typecheck` / `pnpm frontend build`)
- [ ] **Tests**: All existing tests pass, new functionality has tests
- [ ] **Build Check**: Code compiles successfully

### Code Standards
- [ ] **File Size**: No Python files exceed 400 lines (use code-simplifier agent if needed)
- [ ] **No Dead Code**: Remove unused imports, functions, variables
- [ ] **No Code Duplication**: Reuse existing functions and patterns
- [ ] **Consistent Naming**: Follow existing codebase conventions
- [ ] **Documentation**: Update relevant documentation if behavior changes

### Testing Requirements
- [ ] **Unit Tests**: New functions have corresponding unit tests
- [ ] **Integration Tests**: API endpoints have integration tests where applicable
- [ ] **Test Coverage**: Reasonable test coverage for new functionality
- [ ] **No Cheater Tests**: Tests are accurate and reveal flaws, not just pass

### Backend Specific
- [ ] **Database Migrations**: New models have proper migrations
- [ ] **Service Layer**: Business logic in services, not controllers
- [ ] **Error Handling**: Proper HTTP exceptions and error messages
- [ ] **Type Hints**: Full type coverage with mypy compliance
- [ ] **Timezone Handling**: Use datetime.now(UTC), not datetime.utcnow()

### Frontend Specific  
- [ ] **TypeScript**: Strict type checking passes
- [ ] **Component Structure**: Proper prop interfaces and error boundaries
- [ ] **State Management**: Appropriate use of TanStack Query vs Zustand
- [ ] **Form Validation**: Zod schemas for form validation
- [ ] **Accessibility**: Basic accessibility considerations

## Commands to Run Before Commit

### Backend
```bash
cd apps/backend
uv run ruff check src/ --fix        # Fix auto-fixable issues
uv run ruff format src/             # Format code
uv run mypy src/ --ignore-missing-imports  # Type check
uv run pytest tests/unit/ -v       # Run unit tests
```

### Frontend
```bash
cd apps/frontend  
pnpm lint:fix                       # Fix linting issues
pnpm format                         # Format code
pnpm build                          # TypeScript compilation check
pnpm test                           # Unit tests
```

### Full Project
```bash
# From root directory
pnpm test all                       # All tests with Docker
pnpm check services                 # Verify services are healthy
```

## Never Do These

- **Never** use `--no-verify` to bypass commit hooks
- **Never** disable tests instead of fixing them  
- **Never** commit code that doesn't compile
- **Never** leave TODO comments without issue numbers
- **Never** make assumptions - verify with existing code
- **Never** hardcode secrets or API keys
- **Never** create partial implementations with "simplified" placeholders

## Always Do These

- **Always** commit working code incrementally
- **Always** update implementation plans as you progress
- **Always** learn from existing implementations before writing new code
- **Always** stop after 3 failed attempts and reassess approach
- **Always** use the specialized agents (code-simplifier, code-reviewer, etc.)
- **Always** run quality checks before committing
- **Always** write tests for new functionality