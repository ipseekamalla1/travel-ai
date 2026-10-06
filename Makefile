# AI Travel Universe — task runner. `make help` lists targets.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Load .env (if present) so host-run commands use the same ports/URLs as docker compose.
-include .env
export

API_DIR := services/api
UV := uv --directory $(API_DIR)
PNPM := pnpm

.PHONY: help
help: ## Show available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ---------- setup ----------
.PHONY: setup
setup: ## Install all dependencies and create .env if missing
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")
	$(PNPM) install
	$(UV) sync
	$(PNPM) --filter @atu/e2e exec playwright install chromium

# ---------- run ----------
.PHONY: up down logs ps infra api web worker
up: ## Start the full stack in Docker (web :3000, api :8000)
	docker compose up --build -d --wait
	@echo "web → http://localhost:$${WEB_PORT:-3000}   api → http://localhost:$${API_PORT:-8000}/api/v1/docs"

down: ## Stop the stack (data volumes are kept)
	docker compose down

logs: ## Follow logs from all services
	docker compose logs -f

ps: ## Show service status
	docker compose ps

infra: ## Start only Postgres + Redis (for running api/web natively)
	docker compose up -d --wait postgres redis

api: ## Run the API natively with reload (needs `make infra`)
	$(UV) run alembic upgrade head
	$(UV) run uvicorn app.asgi:app --reload --port $${API_PORT:-8000}

worker: ## Run the arq worker natively (needs `make infra`)
	$(UV) run arq app.workers.settings.WorkerSettings --watch app

web: ## Run the web app natively (needs the API)
	$(PNPM) --filter @atu/web dev --port $${WEB_PORT:-3000}

# ---------- database ----------
.PHONY: migrate migration
migrate: ## Apply database migrations
	$(UV) run alembic upgrade head

migration: ## Create a migration: make migration m="add trips"
	@test -n "$(m)" || (echo 'usage: make migration m="message"' && exit 1)
	$(UV) run alembic revision --autogenerate -m "$(m)"

# ---------- quality ----------
.PHONY: lint format typecheck test test-api test-web e2e types types-check check
lint: ## Lint everything
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(PNPM) --filter @atu/web lint
	$(PNPM) --filter @atu/web format:check

format: ## Auto-format everything
	$(UV) run ruff check --fix .
	$(UV) run ruff format .
	$(PNPM) --filter @atu/web format

typecheck: ## Type-check API (mypy) and web (tsc)
	$(UV) run mypy app tests scripts
	$(PNPM) --filter @atu/web typecheck
	$(PNPM) --filter @atu/e2e exec tsc --noEmit

test-api: ## Run API tests (needs `make infra`)
	$(UV) run pytest

test-web: ## Run web unit/component tests
	$(PNPM) --filter @atu/web test

test: test-api test-web ## Run all unit + integration tests

e2e: ## Run Playwright E2E against the running stack (`make up` first)
	$(PNPM) --filter @atu/e2e test

types: ## Regenerate TypeScript API types from the FastAPI schema
	$(PNPM) --filter @atu/types gen

types-check: ## Fail if generated API types are out of date
	$(PNPM) --filter @atu/types check

check: lint typecheck types-check test ## Everything CI runs (except E2E)
