# =============================================================================
# Django Project Makefile
# =============================================================================
# This Makefile provides convenient shortcuts for common development tasks.
#
# Usage:
#   make <target>
#   make help         - Show all available commands
#
# Examples:
#   make dev          - Start development with Docker infrastructure
#   make test         - Run tests
#   make lint         - Run linters
# =============================================================================

# Default shell
SHELL := /bin/bash

# Project paths
BACKEND_DIR := backend
DOCKER_COMPOSE := docker compose
DOCKER_COMPOSE_DEV := docker compose -f docker-compose.dev.yml
PYTHON := python
MANAGE := $(PYTHON) manage.py

# Colors for output (optional, for better readability)
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m  # No Color

# =============================================================================
# HELP
# =============================================================================

.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "Django Project Makefile"
	@echo "======================="
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""

# =============================================================================
# DEVELOPMENT - LOCAL (SQLite)
# =============================================================================
# Use these targets for quick local development without Docker infrastructure.
# Best for: Rapid prototyping, simple feature development
# =============================================================================

.PHONY: install
install: ## Install all development dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	cd $(BACKEND_DIR) && pip install -r requirements/local.txt

.PHONY: local
local: ## Run Django locally with SQLite (quick development)
	@echo "$(GREEN)Starting Django with SQLite...$(NC)"
	cd $(BACKEND_DIR) && DJANGO_SETTINGS_MODULE=backend_core.settings.local $(MANAGE) runserver

.PHONY: local-migrate
local-migrate: ## Run migrations on local SQLite database
	cd $(BACKEND_DIR) && DJANGO_SETTINGS_MODULE=backend_core.settings.local $(MANAGE) migrate

.PHONY: local-shell
local-shell: ## Open Django shell (local SQLite)
	cd $(BACKEND_DIR) && DJANGO_SETTINGS_MODULE=backend_core.settings.local $(MANAGE) shell

# =============================================================================
# DEVELOPMENT - DOCKER INFRASTRUCTURE
# =============================================================================
# Use these targets for production-like development with PostgreSQL and Redis.
# Best for: Testing database queries, caching, WebSockets
# =============================================================================

.PHONY: dev
dev: dev-up ## Start development with Docker infrastructure (PostgreSQL, Redis)
	@echo "$(GREEN)Starting Django with Docker infrastructure...$(NC)"
	@echo "$(YELLOW)PostgreSQL: localhost:5432$(NC)"
	@echo "$(YELLOW)Redis: localhost:6379$(NC)"
	cd $(BACKEND_DIR) && DJANGO_SETTINGS_MODULE=backend_core.settings.local_docker $(MANAGE) runserver

.PHONY: dev-up
dev-up: ## Start Docker infrastructure only (PostgreSQL, Redis)
	@echo "$(GREEN)Starting Docker infrastructure...$(NC)"
	$(DOCKER_COMPOSE_DEV) up -d
	@echo "$(GREEN)Waiting for services to be ready...$(NC)"
	@sleep 3
	@echo "$(GREEN)Infrastructure ready!$(NC)"

.PHONY: dev-down
dev-down: ## Stop Docker infrastructure
	@echo "$(YELLOW)Stopping Docker infrastructure...$(NC)"
	$(DOCKER_COMPOSE_DEV) down

.PHONY: dev-logs
dev-logs: ## View Docker infrastructure logs
	$(DOCKER_COMPOSE_DEV) logs -f

.PHONY: dev-migrate
dev-migrate: ## Run migrations (with Docker PostgreSQL)
	cd $(BACKEND_DIR) && DJANGO_SETTINGS_MODULE=backend_core.settings.local_docker $(MANAGE) migrate

.PHONY: dev-shell
dev-shell: ## Open Django shell (with Docker PostgreSQL)
	cd $(BACKEND_DIR) && DJANGO_SETTINGS_MODULE=backend_core.settings.local_docker $(MANAGE) shell

.PHONY: dev-dbshell
dev-dbshell: ## Open PostgreSQL shell
	$(DOCKER_COMPOSE_DEV) exec postgres psql -U django_user -d backend_core_db

.PHONY: dev-redis-cli
dev-redis-cli: ## Open Redis CLI
	$(DOCKER_COMPOSE_DEV) exec redis redis-cli

# =============================================================================
# PRODUCTION
# =============================================================================
# Use these targets for production deployment testing.
# =============================================================================

.PHONY: prod
prod: ## Start full production stack (Django + PostgreSQL + Redis)
	@echo "$(GREEN)Starting production stack...$(NC)"
	$(DOCKER_COMPOSE) up -d --build
	@echo "$(GREEN)Production stack running at http://localhost:8000$(NC)"

.PHONY: prod-down
prod-down: ## Stop production stack
	@echo "$(YELLOW)Stopping production stack...$(NC)"
	$(DOCKER_COMPOSE) down

.PHONY: prod-logs
prod-logs: ## View production logs
	$(DOCKER_COMPOSE) logs -f

.PHONY: prod-shell
prod-shell: ## Open Django shell in production container
	$(DOCKER_COMPOSE) exec app python manage.py shell

.PHONY: prod-bash
prod-bash: ## Open bash in production container
	$(DOCKER_COMPOSE) exec app /bin/sh

# =============================================================================
# DATABASE
# =============================================================================

.PHONY: makemigrations
makemigrations: ## Create new migrations
	cd $(BACKEND_DIR) && $(MANAGE) makemigrations

.PHONY: migrate
migrate: ## Run all pending migrations
	cd $(BACKEND_DIR) && $(MANAGE) migrate

.PHONY: superuser
superuser: ## Create a superuser
	cd $(BACKEND_DIR) && $(MANAGE) createsuperuser

.PHONY: backup
backup: ## Backup the database
	@echo "$(GREEN)Creating database backup...$(NC)"
	./docker/scripts/backup-db.sh

.PHONY: restore
restore: ## Restore database (usage: make restore FILE=backup.sql.gz)
	@echo "$(YELLOW)Restoring database from $(FILE)...$(NC)"
	./docker/scripts/restore-db.sh $(FILE)

# =============================================================================
# TESTING
# =============================================================================

.PHONY: test
test: ## Run all tests
	@echo "$(GREEN)Running tests...$(NC)"
	cd $(BACKEND_DIR) && pytest -v

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	cd $(BACKEND_DIR) && pytest --cov --cov-config=.coveragerc --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)Coverage report: backend/htmlcov/index.html$(NC)"

.PHONY: test-fast
test-fast: ## Run tests without coverage (faster)
	cd $(BACKEND_DIR) && pytest -x -q

.PHONY: test-watch
test-watch: ## Run tests in watch mode (requires pytest-watch)
	cd $(BACKEND_DIR) && ptw -- -v

.PHONY: test-docker
test-docker: dev-up ## Run tests with Docker infrastructure
	@echo "$(GREEN)Running tests with PostgreSQL and Redis...$(NC)"
	cd $(BACKEND_DIR) && DJANGO_SETTINGS_MODULE=backend_core.settings.local_docker pytest -v

.PHONY: test-api
test-api: ## Run API integration tests (requires: make dev running)
	@echo "$(GREEN)Running API integration tests...$(NC)"
	cd $(BACKEND_DIR) && python -m pytest tests/api_integration/ -v --tb=short -x

.PHONY: test-api-reset
test-api-reset: dev-down dev-up dev-migrate ## Reset Docker DB for clean API test run
	@echo "$(GREEN)Database reset complete. Ready for: make test-api$(NC)"

.PHONY: dev-worker
dev-worker: ## Start Celery worker for async tasks (email, notifications)
	@echo "$(GREEN)Starting Celery worker...$(NC)"
	cd $(BACKEND_DIR) && DJANGO_SETTINGS_MODULE=backend_core.settings.local_docker celery -A backend_core worker -l info

# =============================================================================
# LINTING & CODE QUALITY
# =============================================================================

.PHONY: lint
lint: ## Run all linters
	@echo "$(GREEN)Running linters...$(NC)"
	cd $(BACKEND_DIR) && black --check . && isort --check-only . && flake8 .

.PHONY: format
format: ## Auto-format code (black + isort)
	@echo "$(GREEN)Formatting code...$(NC)"
	cd $(BACKEND_DIR) && black . && isort .
	@echo "$(GREEN)Code formatted!$(NC)"

.PHONY: black
black: ## Run black formatter
	cd $(BACKEND_DIR) && black .

.PHONY: isort
isort: ## Run isort (import sorting)
	cd $(BACKEND_DIR) && isort .

.PHONY: flake8
flake8: ## Run flake8 linter
	cd $(BACKEND_DIR) && flake8 .

.PHONY: check
check: lint test ## Run all checks (lint + test)
	@echo "$(GREEN)All checks passed!$(NC)"

# =============================================================================
# STATIC FILES
# =============================================================================

.PHONY: collectstatic
collectstatic: ## Collect static files
	cd $(BACKEND_DIR) && $(MANAGE) collectstatic --noinput

# =============================================================================
# DOCKER
# =============================================================================

.PHONY: build
build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t django-backend:latest ./$(BACKEND_DIR)

.PHONY: docker-clean
docker-clean: ## Clean up Docker resources
	@echo "$(YELLOW)Cleaning up Docker resources...$(NC)"
	docker system prune -f
	docker volume prune -f

.PHONY: docker-ps
docker-ps: ## Show running containers
	docker compose ps

# =============================================================================
# UTILITIES
# =============================================================================

.PHONY: clean
clean: ## Clean up generated files
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(NC)"

.PHONY: reset
reset: dev-down clean ## Reset everything (stop containers, clean files)
	@echo "$(GREEN)Reset complete!$(NC)"

.PHONY: logs
logs: ## View Django logs (production)
	$(DOCKER_COMPOSE) logs -f app

.PHONY: urls
urls: ## Show all URL patterns
	cd $(BACKEND_DIR) && $(MANAGE) show_urls 2>/dev/null || echo "Install django-extensions: pip install django-extensions"

.PHONY: shell-plus
shell-plus: ## Open enhanced Django shell (requires django-extensions)
	cd $(BACKEND_DIR) && $(MANAGE) shell_plus 2>/dev/null || $(MANAGE) shell

# =============================================================================
# SECRETS & ENVIRONMENT
# =============================================================================

.PHONY: secret-key
secret-key: ## Generate a new Django secret key
	@python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

.PHONY: env-example
env-example: ## Copy example env files
	@echo "$(GREEN)Copying environment examples...$(NC)"
	@test -f .env || cp .env.example .env && echo "Created .env from .env.example"
	@test -f .env.dev || cp .env.dev.example .env.dev && echo "Created .env.dev from .env.dev.example"
	@echo "$(YELLOW)Remember to update the values in .env files!$(NC)"

# =============================================================================
# QUICK START
# =============================================================================

.PHONY: setup
setup: install env-example dev-up dev-migrate superuser ## Complete setup for new developers
	@echo ""
	@echo "$(GREEN)=====================================$(NC)"
	@echo "$(GREEN)  Setup Complete!$(NC)"
	@echo "$(GREEN)=====================================$(NC)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Start development:  make dev"
	@echo "  2. Run tests:          make test"
	@echo "  3. View API docs:      http://localhost:8000/api/schema/swagger/"
	@echo ""

# =============================================================================
# E2E TESTS (Playwright)
# =============================================================================
# Requires: Docker infra running, Django server (make dev), Next.js (cd frontend && npm run dev)
# =============================================================================

E2E_DIR := e2e

.PHONY: e2e-install
e2e-install: ## Install E2E test dependencies + Playwright browsers
	cd $(E2E_DIR) && npm install && npx playwright install --with-deps chromium

.PHONY: e2e
e2e: ## Run all E2E tests (headless)
	cd $(E2E_DIR) && npx playwright test

.PHONY: e2e-ui
e2e-ui: ## Run E2E tests with interactive UI
	cd $(E2E_DIR) && npx playwright test --ui

.PHONY: e2e-headed
e2e-headed: ## Run E2E tests with visible browser
	cd $(E2E_DIR) && npx playwright test --headed

.PHONY: e2e-report
e2e-report: ## Open E2E HTML test report
	cd $(E2E_DIR) && npx playwright show-report reports/e2e-html

.PHONY: e2e-section
e2e-section: ## Run a specific E2E section (usage: make e2e-section FILE=01-registration)
	cd $(E2E_DIR) && npx playwright test tests/$(FILE).spec.ts

# =============================================================================
# DEFAULT TARGET
# =============================================================================

.DEFAULT_GOAL := help
