# Code Style and Conventions

## Backend (Python)
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Code Quality**: Ruff for linting/formatting, mypy for type checking
- **Imports**: Absolute imports preferred, grouped by standard/third-party/local
- **Type Hints**: Full type coverage required
- **Datetime**: Always use timezone-aware datetime (UTC), avoid datetime.utcnow()
- **Error Handling**: Use FastAPI HTTPException with consistent error responses
- **Database Models**: SQLAlchemy 2.0 style with typed relationships
- **Service Pattern**: Business logic in services, dependency injection in routes
- **Authentication**: JWT with Redis sessions

## Frontend (TypeScript/React)
- **Naming**: camelCase for variables/functions, PascalCase for components
- **Components**: Functional components with TypeScript interfaces
- **State Management**: TanStack Query for server state, Zustand for client state
- **Forms**: react-hook-form with Zod validation
- **Styling**: Tailwind CSS with Shadcn UI components
- **Testing**: Vitest for unit tests, Playwright for E2E
- **Error Handling**: React Error Boundaries for UI errors
- **Type Safety**: Full TypeScript coverage, strict mode enabled

## General Principles
- **File Size Limits**: Every .py file must not exceed 400 lines
- **No Code Duplication**: Reuse functions and constants, read existing code first
- **No Partial Implementation**: Complete features, no simplified placeholders
- **Test Coverage**: Tests required for every function
- **No Dead Code**: Either use or delete completely
- **Consistent Naming**: Follow existing codebase patterns