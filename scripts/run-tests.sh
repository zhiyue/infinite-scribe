#!/bin/bash
# Script to run tests for the backend

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Running Infinite Scribe Backend Tests..."
echo "========================================"

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Run unit tests
echo -e "\n${GREEN}Running Unit Tests...${NC}"
cd apps/backend
../../.venv/bin/python -m pytest tests/unit -v --tb=short

# Run integration tests (only if requested)
if [ "$1" == "--integration" ]; then
    echo -e "\n${GREEN}Running Integration Tests...${NC}"
    echo "Note: Integration tests require Docker to be running"
    ../../.venv/bin/python -m pytest tests/integration -v --tb=short -m integration
fi

# Check coverage if requested
if [ "$1" == "--coverage" ]; then
    echo -e "\n${GREEN}Running Tests with Coverage...${NC}"
    ../../.venv/bin/python -m pytest tests --cov=src --cov-report=html --cov-report=term
    echo -e "\n${GREEN}Coverage report generated in htmlcov/index.html${NC}"
fi

echo -e "\n${GREEN}Tests completed!${NC}"