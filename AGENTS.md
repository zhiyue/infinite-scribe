# Repository Guidelines

## Project Structure & Module Organization
- `apps/backend/`: FastAPI service and agents. Code in `src/` (API, agents, models, schemas, middleware). Tests in `tests/unit` and `tests/integration`.
- `apps/frontend/`: React + Vite + TypeScript app. App code in `src/`, E2E in `e2e/`.
- `scripts/`: Unified runner and deployment tooling. `deploy/` contains Compose and deploy helpers.
- `docs/`: Architecture, design, and product docs.
- Root helpers: `Makefile`, `package.json` (pnpm workspace), `pnpm-workspace.yaml`.

## Build, Test, and Development Commands
- Install: `pnpm install` (workspace), `pnpm backend install`, `pnpm frontend install`.
- Run locally: `pnpm infra up` (services), `pnpm backend run` (API on 8000), `pnpm frontend run` (Vite on 5173).
- Tests: `pnpm backend test` (pytest), `pnpm frontend test` (vitest), `pnpm frontend e2e` (Playwright), `pnpm test coverage` (repo-level).
- Lint/format: `pnpm backend lint`, `pnpm backend format`, `pnpm frontend lint`, `pnpm format`.
- Makefile shortcuts: `make dev`, `make lint`, `make test-all`.

## Coding Style & Naming Conventions
- Python: Ruff for lint/format; type-check with mypy. Files and functions `snake_case`, classes `PascalCase`, tests `tests/**/test_*.py`.
- TypeScript/React: ESLint + Prettier; strict TS config. Components `PascalCase.tsx`, hooks `use*.ts`, tests `*.test.ts(x)`.
- General: prefer small modules, pure functions, and explicit types. Avoid console logs; use structured logging/utilities.

## Testing Guidelines
- Backend: pytest for unit/integration; generate coverage with `uv run pytest --cov=src --cov-report=html` (see `htmlcov/`).
- Frontend: vitest for unit; Playwright for E2E (`apps/frontend/e2e/**`). Mock network where possible; add integration tests for API flows.
- Add tests for new features and bug fixes; no hard coverage gate, but keep critical paths covered.

## Commit & Pull Request Guidelines
- Commits follow Conventional Commits (seen in history): `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`. Example: `feat(auth): add password reset flow`.
- PRs include: concise description, linked issues, screenshots or recordings for UI changes, sample requests/responses for API changes, and migration notes when applicable.
- CI hygiene: run `pre-commit run --all-files` (ruff, mypy, bandit, shellcheck, hadolint, prettier), `pnpm lint`, and relevant tests before submitting.

## Security & Configuration Tips
- Never commit secrets. Use `apps/backend/.env.example` and `config.toml.example` as templates; local env lives in `.env` files or `deploy/environments`.
- Check services with `pnpm check:services`; verify infra via `pnpm infra status`.
- Run `gitleaks` (config in `.gitleaks.toml`) before pushing when touching credentials or scripts.

## Agent-Specific Notes
- New agents live under `apps/backend/src/agents/**`. Extend `BaseAgent`, implement `process_message`, and add an entrypoint (see `worldsmith/`). Keep topics and config in settings, not code.

