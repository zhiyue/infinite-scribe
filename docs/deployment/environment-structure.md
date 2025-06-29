# Environment Structure

## Overview

InfiniteScribe uses a simplified environment structure with three main environments and a template file.

## Quick Start

```bash
# First time setup - consolidate existing .env files
pnpm env:consolidate

# Switch to local development
pnpm env:local

# Switch to dev server (192.168.2.201)
pnpm env:dev

# Switch to test environment
pnpm env:test

# Check current environment
pnpm env:show
```

## File Structure

```
.env              → Symlink to active environment
.env.local        → Local development with Docker Compose
.env.dev          → Development server (192.168.2.201)
.env.test         → Test environment (configurable via TEST_MACHINE_IP)
.env.example      → Template with all possible variables
```

## Environment Details

### Local Development (`.env.local`)
- Used for local development with Docker Compose
- All services use `localhost`
- Database: `infinite_scribe`
- Node environment: `development`

### Development Server (`.env.dev`)
- Used for persistent development infrastructure on remote server
- All services use `192.168.2.201`
- Database: `infinite_scribe`
- Node environment: `development`
- **Important**: This server is for development only, NOT for testing
- **Deployment**: Infrastructure services are deployed on this server using Docker Compose

### Test Environment (`.env.test`)
- Used for running tests with isolated containers
- Services use `${TEST_MACHINE_IP}` (default: 192.168.2.202)
- Database: `infinite_scribe_test` (separate from development)
- Node environment: `test`
- Includes Docker configuration for testcontainers

## Switching Between Environments

### Using npm scripts (Recommended)
```bash
pnpm env:local   # Switch to local development
pnpm env:dev     # Switch to dev server
pnpm env:test    # Switch to test environment
```

### Manual switching
```bash
rm .env
ln -s .env.local .env    # For local development
ln -s .env.dev .env      # For dev server
ln -s .env.test .env     # For testing
```

## Adding New Variables

1. Add the variable to `.env.example` with a descriptive comment
2. Add it to the appropriate environment files (`.env.local`, `.env.dev`, `.env.test`)
3. Update the documentation in `docs/deployment/environment-variables.md`
4. If the variable is used in code, ensure proper defaults are set

## Infrastructure Deployment

### Local Development
```bash
# Deploy infrastructure locally using Docker Compose
./scripts/deployment/deploy-infrastructure.sh --local

# Or use pnpm command
pnpm infra:up
```

### Development Server
```bash
# Deploy infrastructure to dev server (default)
./scripts/deployment/deploy-infrastructure.sh

# This will:
# 1. Sync files to 192.168.2.201
# 2. Use .env.dev configuration
# 3. Start services with docker-compose on the remote server
```

### Key Differences
- **Local**: Uses `.env.local`, runs on your machine
- **Dev Server**: Uses `.env.dev`, runs on 192.168.2.201
- **Test**: Uses `.env.test`, runs on test machine (192.168.2.202)

## Best Practices

1. **Never commit** real credentials or API keys
2. **Use `.env.example`** as the source of truth for all variables
3. **Document** all new environment variables
4. **Use sensible defaults** in your code
5. **Keep environment-specific** values in their respective files
6. **Use appropriate environment** for each task:
   - Local development: `.env.local`
   - Shared development: `.env.dev`
   - Testing: `.env.test`

## Migration from Old Structure

If you have old environment files from the layered structure:
```bash
# Run the consolidation script
pnpm env:consolidate

# Old files will be backed up to .env-backup-TIMESTAMP/
# Review and manually delete old files when ready
```

The old layered structure files that can be removed:
- `.env.infrastructure`
- `.env.backend.local`
- `.env.backend.example`
- `.env.frontend.example`
- `.env.agents.example`
- `.env.remote-docker`
- `apps/backend/.env.test`
- `apps/backend/.env.ci`
