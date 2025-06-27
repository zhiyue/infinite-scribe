#!/bin/bash

# Test script using remote containers at 192.168.2.201
echo "Running tests with remote containers at 192.168.2.201..."

# Load test environment variables
export $(grep -v '^#' .env.test | xargs)

# Check connectivity to remote services
echo "=== Checking remote services connectivity ==="
echo -n "PostgreSQL: "
nc -zv 192.168.2.201 5432 2>&1 | grep -q succeeded && echo "✓ Connected" || echo "✗ Failed"

echo -n "Neo4j: "
nc -zv 192.168.2.201 7687 2>&1 | grep -q succeeded && echo "✓ Connected" || echo "✗ Failed"

echo -n "Redis: "
nc -zv 192.168.2.201 6379 2>&1 | grep -q succeeded && echo "✓ Connected" || echo "✗ Failed"

# Run unit tests
echo -e "\n=== Running unit tests ==="
cd apps/backend && uv run pytest tests/unit/ -v

# Run integration tests with remote containers
echo -e "\n=== Running integration tests with remote containers ==="
uv run pytest tests/integration/ -v -k "not test_database_connections" \
    --cov=src --cov-report=term-missing

# Run linting
echo -e "\n=== Running linting ==="
uv run ruff check src/ --output-format=concise

# Run format check
echo -e "\n=== Running format check ==="
uv run ruff format --check src/

# Run type checking from project root
echo -e "\n=== Running type checking ==="
cd ../.. && uv run mypy apps/backend/src/ --ignore-missing-imports

echo -e "\n=== All tests completed ==="