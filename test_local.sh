#!/bin/bash

# Local test script for systems without Docker
echo "Running local tests..."

# Run unit tests
echo "=== Running unit tests ==="
cd apps/backend && uv run pytest tests/unit/ -v

# Run linting
echo -e "\n=== Running linting ==="
uv run ruff check src/ --output-format=concise

# Run format check
echo -e "\n=== Running format check ==="
uv run ruff format --check src/

# Run type checking from project root
echo -e "\n=== Running type checking ==="
cd ../.. && uv run mypy apps/backend/src/ --ignore-missing-imports

echo -e "\n=== All local tests completed ==="