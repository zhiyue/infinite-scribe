# Infinite Scribe - Unified Makefile
# This Makefile provides convenient shortcuts for common development tasks

# Default test machine IP (can be overridden)
TEST_MACHINE_IP ?= 192.168.2.202

# Default SSH user (can be overridden)
SSH_USER ?= zhiyue

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help
help: ## Show this help message
	@echo "$(CYAN)Infinite Scribe - Development Commands$(NC)"
	@echo "$(GREEN)Usage: make [target]$(NC)"
	@echo "$(YELLOW)Variables: TEST_MACHINE_IP=$(TEST_MACHINE_IP) SSH_USER=$(SSH_USER)$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "$(YELLOW)Available targets:$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(CYAN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Backend Commands

.PHONY: backend-install
backend-install: ## Install backend dependencies
	@echo "$(GREEN)Installing backend dependencies...$(NC)"
	uv sync --all-extras

.PHONY: backend-run
backend-run: ## Run backend development server
	@echo "$(GREEN)Starting backend server...$(NC)"
	cd apps/backend && uv run uvicorn src.main:app --reload

.PHONY: backend-lint
backend-lint: ## Lint backend code
	@echo "$(GREEN)Linting backend code...$(NC)"
	cd apps/backend && uv run ruff check src/

.PHONY: backend-format
backend-format: ## Format backend code
	@echo "$(GREEN)Formatting backend code...$(NC)"
	cd apps/backend && uv run ruff format src/

.PHONY: backend-typecheck
backend-typecheck: ## Type check backend code
	@echo "$(GREEN)Type checking backend code...$(NC)"
	cd apps/backend && uv run mypy src/ --ignore-missing-imports

.PHONY: backend-test-unit
backend-test-unit: ## Run backend unit tests only (local)
	@echo "$(GREEN)Running backend unit tests...$(NC)"
	cd apps/backend && uv run pytest tests/unit/ -v

##@ Frontend Commands

.PHONY: frontend-install
frontend-install: ## Install frontend dependencies
	@echo "$(GREEN)Installing frontend dependencies...$(NC)"
	pnpm install

.PHONY: frontend-run
frontend-run: ## Run frontend development server
	@echo "$(GREEN)Starting frontend server...$(NC)"
	pnpm dev

.PHONY: frontend-build
frontend-build: ## Build frontend for production
	@echo "$(GREEN)Building frontend...$(NC)"
	pnpm build

.PHONY: frontend-test
frontend-test: ## Run frontend tests
	@echo "$(GREEN)Running frontend tests...$(NC)"
	pnpm test

##@ Testing Commands (Recommended: use docker-host)

.PHONY: test-all
test-all: ## Run all tests with Docker containers (recommended)
	@echo "$(GREEN)Running all tests with Docker containers on test machine $(TEST_MACHINE_IP)...$(NC)"
	TEST_MACHINE_IP=$(TEST_MACHINE_IP) ./scripts/test/run-tests.sh --all --docker-host

.PHONY: test-unit
test-unit: ## Run unit tests only with Docker containers
	@echo "$(GREEN)Running unit tests with Docker containers...$(NC)"
	TEST_MACHINE_IP=$(TEST_MACHINE_IP) ./scripts/test/run-tests.sh --unit --docker-host

.PHONY: test-integration
test-integration: ## Run integration tests only with Docker containers
	@echo "$(GREEN)Running integration tests with Docker containers...$(NC)"
	TEST_MACHINE_IP=$(TEST_MACHINE_IP) ./scripts/test/run-tests.sh --integration --docker-host

.PHONY: test-coverage
test-coverage: ## Run all tests with coverage report
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	TEST_MACHINE_IP=$(TEST_MACHINE_IP) ./scripts/test/run-tests.sh --all --docker-host --coverage

.PHONY: test-lint
test-lint: ## Run code quality checks only
	@echo "$(GREEN)Running code quality checks...$(NC)"
	./scripts/test/run-tests.sh --lint

.PHONY: test-all-remote
test-all-remote: ## Run all tests with pre-deployed services (alternative)
	@echo "$(YELLOW)Running tests with pre-deployed services on $(TEST_MACHINE_IP)...$(NC)"
	TEST_MACHINE_IP=$(TEST_MACHINE_IP) ./scripts/test/run-tests.sh --all --remote

##@ Development Shortcuts

.PHONY: install
install: backend-install frontend-install ## Install all dependencies (backend + frontend)
	@echo "$(GREEN)All dependencies installed!$(NC)"

.PHONY: dev
dev: ## Start both backend and frontend in parallel (requires tmux or separate terminals)
	@echo "$(YELLOW)Starting backend and frontend servers...$(NC)"
	@echo "$(YELLOW)Note: This requires tmux or you'll need to run in separate terminals$(NC)"
	@if command -v tmux >/dev/null 2>&1; then \
		tmux new-session -d -s infinite-scribe 'make backend-run' \; \
		split-window -h 'make frontend-run' \; \
		attach-session -t infinite-scribe; \
	else \
		echo "$(RED)tmux not found. Please run 'make backend-run' and 'make frontend-run' in separate terminals.$(NC)"; \
	fi

.PHONY: lint
lint: backend-lint test-lint ## Run all linting checks
	@echo "$(GREEN)All linting checks complete!$(NC)"

.PHONY: format
format: backend-format ## Format all code
	@echo "$(GREEN)All code formatted!$(NC)"

.PHONY: typecheck
typecheck: backend-typecheck ## Run all type checks
	@echo "$(GREEN)All type checks complete!$(NC)"

.PHONY: clean
clean: ## Clean build artifacts and caches
	@echo "$(GREEN)Cleaning build artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules/.cache" -exec rm -rf {} + 2>/dev/null || true

##@ Deployment Commands

.PHONY: deploy
deploy: ## Deploy to development server (default: sync and deploy all services)
	@echo "$(GREEN)Deploying to development server...$(NC)"
	./scripts/deploy/deploy-to-dev.sh

.PHONY: deploy-build
deploy-build: ## Build and deploy all services on development server
	@echo "$(GREEN)Building and deploying all services...$(NC)"
	./scripts/deploy/deploy-to-dev.sh --build

.PHONY: deploy-infra
deploy-infra: ## Deploy only infrastructure services
	@echo "$(GREEN)Deploying infrastructure services...$(NC)"
	./scripts/deploy/deploy-to-dev.sh --type infra

.PHONY: deploy-backend
deploy-backend: ## Deploy all backend services (API Gateway + Agents)
	@echo "$(GREEN)Deploying backend services...$(NC)"
	./scripts/deploy/deploy-to-dev.sh --type backend

.PHONY: deploy-backend-build
deploy-backend-build: ## Build and deploy all backend services
	@echo "$(GREEN)Building and deploying backend services...$(NC)"
	./scripts/deploy/deploy-to-dev.sh --type backend --build

.PHONY: deploy-agents
deploy-agents: ## Deploy all Agent services only
	@echo "$(GREEN)Deploying Agent services...$(NC)"
	./scripts/deploy/deploy-to-dev.sh --type agents

.PHONY: deploy-agents-build
deploy-agents-build: ## Build and deploy all Agent services
	@echo "$(GREEN)Building and deploying Agent services...$(NC)"
	./scripts/deploy/deploy-to-dev.sh --type agents --build

.PHONY: deploy-api
deploy-api: ## Deploy only API Gateway service
	@echo "$(GREEN)Deploying API Gateway only...$(NC)"
	./scripts/deploy/deploy-to-dev.sh --service api-gateway

.PHONY: deploy-api-build
deploy-api-build: ## Build and deploy only API Gateway service
	@echo "$(GREEN)Building and deploying API Gateway only...$(NC)"
	./scripts/deploy/deploy-to-dev.sh --service api-gateway --build

.PHONY: deploy-service
deploy-service: ## Deploy specific service (use SERVICE=<name> make deploy-service)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)Error: SERVICE not specified$(NC)"; \
		echo "Usage: SERVICE=api-gateway make deploy-service"; \
		exit 1; \
	fi
	@echo "$(GREEN)Deploying service: $(SERVICE)$(NC)"
	./scripts/deploy/deploy-to-dev.sh --service $(SERVICE)

.PHONY: deploy-service-build
deploy-service-build: ## Build and deploy specific service (use SERVICE=<name> make deploy-service-build)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)Error: SERVICE not specified$(NC)"; \
		echo "Usage: SERVICE=api-gateway make deploy-service-build"; \
		exit 1; \
	fi
	@echo "$(GREEN)Building and deploying service: $(SERVICE)$(NC)"
	./scripts/deploy/deploy-to-dev.sh --service $(SERVICE) --build

.PHONY: deploy-help
deploy-help: ## Show deployment script help
	./scripts/deploy/deploy-to-dev.sh --help

##@ SSH Access

.PHONY: ssh-dev
ssh-dev: ## SSH to development machine (192.168.2.201)
	@echo "$(GREEN)Connecting to development machine...$(NC)"
	ssh $(SSH_USER)@192.168.2.201

.PHONY: ssh-test
ssh-test: ## SSH to test machine (default: 192.168.2.202)
	@echo "$(GREEN)Connecting to test machine ($(TEST_MACHINE_IP))...$(NC)"
	ssh $(SSH_USER)@$(TEST_MACHINE_IP)

##@ Quick Start

.PHONY: setup
setup: install ## Initial project setup
	@echo "$(GREEN)Project setup complete!$(NC)"
	@echo "$(CYAN)Next steps:$(NC)"
	@echo "  1. Run 'make dev' to start development servers"
	@echo "  2. Run 'make test-all' to run all tests"
	@echo "  3. Run 'make help' to see all available commands"

.PHONY: check
check: lint typecheck test-unit ## Run all checks (lint, typecheck, unit tests)
	@echo "$(GREEN)All checks passed!$(NC)"

# Default target
.DEFAULT_GOAL := help
