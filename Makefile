.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help setup up down restart logs ps shell-api shell-db shell-worker shell-redis shell-minio migrate seed-demo lint typecheck test check build clean

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\n"} /^[a-zA-Z_-]+:.*## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Create local environment file
	@test -f .env || cp .env.example .env

up: setup ## Build and start the development stack
	$(COMPOSE) up --build -d

down: ## Stop the development stack
	$(COMPOSE) down

restart: ## Restart application containers
	$(COMPOSE) restart frontend api worker

logs: ## Follow stack logs
	$(COMPOSE) logs -f

ps: ## Show stack status
	$(COMPOSE) ps

shell-api: ## Open a shell in the API container
	$(COMPOSE) exec api sh

shell-worker: ## Open a shell in the worker container
	$(COMPOSE) exec worker sh

shell-redis: ## Open a redis-cli session
	$(COMPOSE) exec redis redis-cli

shell-minio: ## Open a shell in the MinIO container
	$(COMPOSE) exec minio sh

shell-db: ## Open psql in the database container
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-vc_brain} -d $${POSTGRES_DB:-vc_brain}

migrate: ## Apply backend database migrations
	$(COMPOSE) run --rm migrate

seed-demo: up ## Seed deterministic, synthetic local demo records
	$(COMPOSE) run --rm --no-deps api /opt/venv/bin/python -m scripts.seed_demo

lint: ## Run frontend and backend linters
	$(COMPOSE) run --rm api /opt/venv/bin/ruff check .
	$(COMPOSE) run --rm frontend npm run lint

typecheck: ## Run frontend and backend type checks
	$(COMPOSE) run --rm api /opt/venv/bin/mypy app
	$(COMPOSE) run --rm frontend npm run typecheck

test: ## Run all unit tests
	$(COMPOSE) run --rm api /opt/venv/bin/pytest
	$(COMPOSE) run --rm frontend npm test -- --run

check: lint typecheck test ## Run all validation

build: ## Build production images
	$(COMPOSE) build api frontend

clean: ## Stop stack and remove local data volumes
	$(COMPOSE) down --volumes --remove-orphans
