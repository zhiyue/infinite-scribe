# Gemini Project Guide: Infinite Scribe

This document provides a guide for the Gemini AI assistant to effectively
contribute to the "Infinite Scribe" project.

## 1. Project Overview

Infinite Scribe is a full-stack monorepo application. The project is structured
with a clear separation of concerns, containing a frontend application, a
backend application, and shared packages. It heavily utilizes Docker for
containerization and has a sophisticated, AI-agent-based development workflow
defined in directories like `.bmad-core`, `.clinerules`, and `.claude`.

## 2. Tech Stack

- **Monorepo Management**: pnpm workspaces (`pnpm-workspace.yaml`)
- **Frontend**: TypeScript-based (likely React/Next.js, located in
  `apps/frontend`)
- **Backend**: TypeScript/Node.js and Python (`apps/backend`)
- **Package Management**:
  - **Node.js**: pnpm
  - **Python**: uv (`pyproject.toml`, `uv.lock`)
- **Linting & Formatting**:
  - **TypeScript/JavaScript**: ESLint, Prettier
  - **Python**: Ruff, Pyright
- **Testing**: The testing framework is likely configured in `package.json` and
  `pyproject.toml`.
- **Containerization**: Docker (`docker-compose.yml`)
- **Automation**: `Makefile`, `pre-commit` hooks, shell scripts in `scripts/`.
- **CI/CD**: GitHub Actions (`.github/workflows`)

## 3. Project Structure

- `apps/`: Contains the main, deployable applications.
  - `frontend/`: The user-facing web application.
  - `backend/`: The server-side application/API.
- `docs/`: Contains critical project documentation, including architecture,
  PRDs, and development practices. **This should be consulted before making any
  significant changes.**
- `scripts/`: Various automation and utility scripts.
- `infrastructure/`: Docker configurations.
- `.bmad-core/`, `.claude/`, `.clinerules/`: **Crucial**: These directories
  define a highly structured, role-based (e.g., architect, dev, qa) AI-assisted
  development process. Review the rules and templates within before starting a
  task.

## 4. Key Files

- `Makefile`: Defines common, high-level commands for tasks like installation,
  testing, and running the project. **Use `make` commands whenever possible.**
- `docker-compose.yml`: Defines the services for local development.
- `package.json` (root): Defines root-level scripts and dependencies.
- `pnpm-workspace.yaml`: Defines the pnpm workspace structure.
- `pyproject.toml`: Defines Python dependencies and project metadata.
- `docs/architecture.md`: High-level architecture documentation.

## 5. Development Workflow

### Installation

1.  To install all dependencies (both Node.js and Python), it is likely there is
    a top-level command.
2.  **Action**: Check the `Makefile` for an `install` or `setup` target. If it
    exists, run `make install`.
3.  If not, run `pnpm install` for Node.js dependencies and `uv sync` for Python
    dependencies.

### Running the Application

1.  The project is containerized with Docker.
2.  **Action**: Use `docker-compose up` to start all services.
3.  Alternatively, check the `Makefile` for a `run`, `dev`, or `start` target,
    e.g., `make run`.

### Environment Management

- The project uses `.env.*` files for environment variables.
- Use `pnpm env:local`, `pnpm env:dev`, or `pnpm env:test` to switch between
  different environments.

## 6. Testing

- **Action**: Check the `Makefile` for a `test` target (e.g., `make test`). This
  is the preferred way to run all tests.
- If a make target doesn't exist, use `pnpm test` to run tests across the
  monorepo.

## 7. Linting and Formatting

- **Action**: Check the `Makefile` for `lint` and `format` targets.
- If they don't exist, use the following commands:
  - `pnpm lint`
  - `pnpm format`
  - `uv run ruff check .`
  - `uv run ruff format .`

## 8. Committing and CI

- The project uses `pre-commit` hooks (`.pre-commit-config.yaml`).
- Hooks will automatically run linting and formatting checks before a commit is
  created.
- All changes pushed to GitHub will trigger CI workflows defined in
  `.github/workflows`. Ensure all local checks pass before pushing.

## 9. Special Instructions: AI-Assisted Workflow

This project has a unique, highly structured development process that appears to
be designed for AI agents.

- **Roles**: Development is broken down into roles like `architect`, `dev`,
  `pm`, `qa`, etc.
- **Rules & Templates**: The `.bmad-core`, `.clinerules`, and `.claude`
  directories contain markdown files with specific instructions, checklists, and
  templates for each role and task.
- **Procedure**: Before starting any task (e.g., writing a feature, fixing a
  bug, creating documentation), **you must first consult the relevant files in
  these directories**. Adhere strictly to the defined workflows, templates, and
  quality checklists. Start by looking at `.clinerules/cline_rules.md` and
  `dev_workflow.md`.
