# Command Reference: Make vs pnpm

This document provides a quick reference for using either `make` or `pnpm` commands to perform common development tasks.

## Backend Commands

| Task | Make Command | pnpm Command |
|------|--------------|--------------|
| Install dependencies | `make backend-install` | `pnpm run backend:install` |
| Run development server | `make backend-run` | `pnpm run backend:run` |
| Lint code | `make backend-lint` | `pnpm run backend:lint` |
| Format code | `make backend-format` | `pnpm run backend:format` |
| Type check | `make backend-typecheck` | `pnpm run backend:typecheck` |
| Run unit tests | `make backend-test-unit` | `pnpm run backend:test:unit` |

## Frontend Commands

| Task | Make Command | pnpm Command |
|------|--------------|--------------|
| Install dependencies | `make frontend-install` | `pnpm run frontend:install` |
| Run development server | `make frontend-run` | `pnpm run frontend:run` |
| Build for production | `make frontend-build` | `pnpm run frontend:build` |
| Run tests | `make frontend-test` | `pnpm run frontend:test` |

## Testing Commands

| Task | Make Command | pnpm Command |
|------|--------------|--------------|
| Run all tests (Docker) | `make test-all` | `pnpm run test:all` |
| Run unit tests only | `make test-unit` | `pnpm run test:unit` |
| Run integration tests | `make test-integration` | `pnpm run test:integration` |
| Run with coverage | `make test-coverage` | `pnpm run test:coverage` |
| Run lint checks only | `make test-lint` | `pnpm run test:lint` |
| Run with remote services | `make test-all-remote` | `pnpm run test:all:remote` |

## Development Shortcuts

| Task | Make Command | pnpm Command |
|------|--------------|--------------|
| Install all dependencies | `make install` | `pnpm run install` |
| Run all dev servers | `make dev` | `pnpm run backend:run` + `pnpm run frontend:run` |
| Run all linting | `make lint` | `pnpm run lint:all` |
| Format all code | `make format` | `pnpm run format:all` |
| Run all type checks | `make typecheck` | `pnpm run typecheck:all` |
| Run all checks | `make check` | `pnpm run check` |
| Clean build artifacts | `make clean` | `pnpm run clean` |

## SSH Access

| Task | Make Command | pnpm Command |
|------|--------------|--------------|
| SSH to dev machine | `make ssh-dev` | `pnpm run ssh:dev` |
| SSH to test machine | `make ssh-test` | `pnpm run ssh:test` |

## Environment Variables

Both Make and pnpm commands support the same environment variables:

- `TEST_MACHINE_IP`: IP address of the test machine (default: 192.168.2.202)
- `SSH_USER`: SSH username (default: zhiyue)

### Examples:

```bash
# Using Make
TEST_MACHINE_IP=192.168.2.100 make test-all
SSH_USER=myuser make ssh-dev

# Using pnpm
TEST_MACHINE_IP=192.168.2.100 pnpm run test:all
SSH_USER=myuser pnpm run ssh:dev
```

## Quick Start

```bash
# Setup project (install all dependencies)
make setup
# or
pnpm run install

# Run development servers
make dev  # Opens tmux with both servers
# or run in separate terminals:
pnpm run backend:run
pnpm run frontend:run

# Run all tests
make test-all
# or
pnpm run test:all

# Show all available commands
make help
# or
pnpm run
```

## Tips

1. **Make** is generally shorter to type and provides colored output
2. **pnpm** commands are more explicit and integrate well with Node.js tooling
3. Both approaches are equally valid - choose based on your preference
4. Environment variables work the same way with both tools
