# Backend Makefile

.PHONY: help test test-unit test-integration test-ci lint format type-check

help:
	@echo "Available commands:"
	@echo "  make test              - Run all tests with testcontainers"
	@echo "  make test-unit         - Run unit tests only"
	@echo "  make test-integration  - Run integration tests with testcontainers"
	@echo "  make test-ci           - Run tests as in CI (external services)"
	@echo "  make lint              - Run linting checks"
	@echo "  make format            - Format code"
	@echo "  make type-check        - Run type checking"

# Run all tests with testcontainers
test:
	uv run pytest tests/ -v

# Run unit tests only
test-unit:
	uv run pytest tests/unit/ -v

# Run integration tests with testcontainers
test-integration:
	uv run pytest tests/integration/ -v

# Run all tests (unit + integration) with testcontainers
test-ci:
	uv run pytest tests/ -v

# Run linting
lint:
	uv run ruff check src/ tests/

# Format code
format:
	uv run ruff format src/ tests/

# Run type checking
type-check:
	uv run mypy src/ --ignore-missing-imports