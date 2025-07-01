#!/bin/bash

# Unified test script for Infinite Scribe
# 
# Infrastructure:
#   - 192.168.2.201: Development machine (persistent services, NOT for testing)
#   - TEST_MACHINE_IP env var or 192.168.2.202: Test machine (for ALL tests)
#
# Usage: ./scripts/run-tests.sh [options]
#
# Options:
#   -u, --unit          Run unit tests only (no linting)
#   -i, --integration   Run integration tests only (no linting)
#   -a, --all           Run all tests (unit + integration + linting)
#   --remote            Use pre-deployed services on test machine (default: TEST_MACHINE_IP env var or 192.168.2.202)
#   --docker-host       Use test machine Docker (default: DOCKER_HOST_IP env var or TEST_MACHINE_IP)
#   --coverage          Generate coverage report
#   --lint              Run only linting and type checking
#   --no-lint           Skip linting and type checking (when used with --all)
#   -h, --help          Show this help message
#
# Default behavior (no flags): Run unit tests + linting

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default settings
RUN_UNIT=true
RUN_INTEGRATION=false
RUN_LINT=true
USE_COVERAGE=false
USE_REMOTE_SERVICES=false
USE_DOCKER_HOST=false
LINT_ONLY=false

# Test machine configuration (can be overridden by environment variable)
TEST_MACHINE_IP="${TEST_MACHINE_IP:-192.168.2.202}"

# Docker host configuration (can be overridden by environment variable)
DOCKER_HOST_IP="${DOCKER_HOST_IP:-${TEST_MACHINE_IP}}"
DOCKER_HOST_PORT="${DOCKER_HOST_PORT:-2375}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--unit)
            RUN_UNIT=true
            RUN_INTEGRATION=false
            RUN_LINT=false
            shift
            ;;
        -i|--integration)
            RUN_UNIT=false
            RUN_INTEGRATION=true
            RUN_LINT=false
            shift
            ;;
        -a|--all)
            RUN_UNIT=true
            RUN_INTEGRATION=true
            RUN_LINT=true
            shift
            ;;
        --remote)
            USE_REMOTE_SERVICES=true
            shift
            ;;
        --docker-host)
            USE_DOCKER_HOST=true
            shift
            ;;
        --coverage)
            USE_COVERAGE=true
            shift
            ;;
        --lint)
            LINT_ONLY=true
            shift
            ;;
        --no-lint)
            RUN_LINT=false
            shift
            ;;
        -h|--help)
            head -n 15 "$0" | tail -n 13
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Configure environment based on options
if [ "$USE_REMOTE_SERVICES" = true ]; then
    echo -e "${YELLOW}Using pre-deployed services on TEST machine at ${TEST_MACHINE_IP}${NC}"
    echo -e "${GREEN}Connecting to manually deployed test services${NC}"
    
    # Load .env.test but override host IPs with TEST_MACHINE_IP
    export $(grep -v '^#' "$PROJECT_ROOT/.env.test" | xargs)
    export POSTGRES_HOST=${TEST_MACHINE_IP}
    export NEO4J_HOST=${TEST_MACHINE_IP}
    export REDIS_HOST=${TEST_MACHINE_IP}
    export USE_EXTERNAL_SERVICES=true
    
    # Check connectivity
    if command -v nc &> /dev/null; then
        echo "Checking test services connectivity..."
        nc -zv ${TEST_MACHINE_IP} 5432 2>&1 | grep -q succeeded && echo "✓ PostgreSQL" || echo "✗ PostgreSQL"
        nc -zv ${TEST_MACHINE_IP} 7687 2>&1 | grep -q succeeded && echo "✓ Neo4j" || echo "✗ Neo4j"
        nc -zv ${TEST_MACHINE_IP} 6379 2>&1 | grep -q succeeded && echo "✓ Redis" || echo "✗ Redis"
    else
        echo -e "${YELLOW}Warning: 'nc' command not found. Skipping connectivity check.${NC}"
        echo "Test services are expected to be available at ${TEST_MACHINE_IP}"
    fi
elif [ "$USE_DOCKER_HOST" = true ]; then
    echo -e "${YELLOW}Using TEST machine Docker host at ${DOCKER_HOST_IP}:${DOCKER_HOST_PORT}${NC}"
    echo -e "${GREEN}Safe for destructive tests - using isolated test environment${NC}"
    export USE_REMOTE_DOCKER=true
    export REMOTE_DOCKER_HOST=tcp://${DOCKER_HOST_IP}:${DOCKER_HOST_PORT}
    
    # Check Docker connectivity
    echo -n "Docker host connectivity: "
    
    # Try local docker command first if available
    if command -v docker &> /dev/null; then
        if docker -H ${REMOTE_DOCKER_HOST} version > /dev/null 2>&1; then
            echo "✓ Connected (via Docker CLI)"
            docker -H ${REMOTE_DOCKER_HOST} version --format 'Server: {{.Server.Version}}'
        else
            echo "✗ Failed to connect via Docker CLI"
            # Try SSH as fallback
            if command -v ssh &> /dev/null && ssh -o ConnectTimeout=5 -o BatchMode=yes zhiyue@${DOCKER_HOST_IP} "docker version" &> /dev/null; then
                echo "✓ Connected (via SSH fallback)"
                ssh zhiyue@${DOCKER_HOST_IP} "docker version --format 'Server: {{.Server.Version}}'"
            else
                echo "Please ensure Docker daemon is accessible at ${REMOTE_DOCKER_HOST}"
                exit 1
            fi
        fi
    # If no local docker, try SSH
    elif command -v ssh &> /dev/null && ssh -o ConnectTimeout=5 -o BatchMode=yes zhiyue@${DOCKER_HOST_IP} "docker version" &> /dev/null; then
        echo "✓ Connected (via SSH)"
        ssh zhiyue@${DOCKER_HOST_IP} "docker version --format 'Server: {{.Server.Version}}'"
    else
        echo "✗ Cannot verify connectivity"
        echo -e "${YELLOW}Note: Testcontainers will attempt to connect directly to ${REMOTE_DOCKER_HOST}${NC}"
        echo "For better diagnostics, install Docker CLI or configure SSH access to zhiyue@${DOCKER_HOST_IP}"
    fi
fi

echo -e "${GREEN}Running Infinite Scribe Tests${NC}"
echo "========================================"

# Run linting and type checking
if [ "$RUN_LINT" = true ]; then
    echo -e "\n${GREEN}=== Running code quality checks ===${NC}"
    
    echo -e "\n${YELLOW}Running linting...${NC}"
    cd "$PROJECT_ROOT/apps/backend" && uv run ruff check src/ tests/ --output-format=concise
    
    echo -e "\n${YELLOW}Running format check...${NC}"
    uv run ruff format --check src/ tests/
    
    echo -e "\n${YELLOW}Running type checking...${NC}"
    cd "$PROJECT_ROOT" && uv run mypy apps/backend/src/ --ignore-missing-imports
fi

# Exit if only linting was requested
if [ "$LINT_ONLY" = true ]; then
    echo -e "\n${GREEN}Code quality checks completed!${NC}"
    exit 0
fi

# Run tests
cd "$PROJECT_ROOT/apps/backend"

# Prepare pytest options
PYTEST_OPTS="-v"
if [ "$USE_COVERAGE" = true ]; then
    PYTEST_OPTS="$PYTEST_OPTS --cov=src --cov-report=term-missing --cov-report=html"
fi

# Run unit tests
if [ "$RUN_UNIT" = true ]; then
    echo -e "\n${GREEN}=== Running unit tests ===${NC}"
    uv run pytest tests/unit/ $PYTEST_OPTS
fi

# Run integration tests
if [ "$RUN_INTEGRATION" = true ]; then
    echo -e "\n${GREEN}=== Running integration tests ===${NC}"
    uv run pytest tests/integration/ $PYTEST_OPTS
fi

# Clean up if using Docker host
if [ "$USE_DOCKER_HOST" = true ]; then
    echo -e "\n${YELLOW}Checking for leftover test containers...${NC}"
    
    leftover_containers=""
    
    # Since we already tested Docker connectivity above, use the working method
    # Check if Docker CLI connection worked during initial connectivity test
    if command -v docker &> /dev/null && docker -H ${REMOTE_DOCKER_HOST} version > /dev/null 2>&1; then
        echo "Using Docker CLI to check containers..."
        leftover_containers=$(timeout 10 docker -H ${REMOTE_DOCKER_HOST} ps -a --filter "name=test" --format "{{.Names}}" 2>/dev/null || echo "")
    # Fallback to SSH (which we know works based on earlier connectivity test)
    elif command -v ssh &> /dev/null; then
        echo "Using SSH to check containers..."
        leftover_containers=$(ssh -o ConnectTimeout=5 -o BatchMode=yes zhiyue@${DOCKER_HOST_IP} 'docker ps -a --filter "name=test" --format "{{.Names}}"' 2>/dev/null || echo "")
    else
        echo -e "${YELLOW}Cannot check for containers without Docker CLI or SSH access${NC}"
        leftover_containers=""
    fi
    
    # Only show message if we actually found container names (not error messages)
    if [ -n "$leftover_containers" ] && [ "$leftover_containers" != "" ] && [[ "$leftover_containers" != *"error"* ]] && [[ "$leftover_containers" != *"command"* ]] && [[ "$leftover_containers" != *"could not be found"* ]]; then
        echo "Found leftover test containers: $leftover_containers"
    else
        echo "No leftover test containers found. ✓"
    fi
fi

# Show coverage report location if generated
if [ "$USE_COVERAGE" = true ]; then
    echo -e "\n${GREEN}Coverage report generated in apps/backend/htmlcov/index.html${NC}"
fi

echo -e "\n${GREEN}=== All tests completed ===${NC}"