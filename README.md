# The VC Brain

Evidence-backed founder intelligence platform. Sources, profiles, and scores founders for venture capital investment decisions.

## Status

Boilerplate phase. The repository contains a Docker-first development environment with a Vite + Tailwind CSS frontend, FastAPI modular monolith, background worker, and supporting data services.

## Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Vite 7 + React 18 + TypeScript + Tailwind CSS v4 | Investor-facing SPA |
| **API** | FastAPI + Uvicorn (async) | Modular monolith: auth, search, scoring, workflow |
| **Worker** | Arq (async Redis queue) | Background collection, processing, scoring jobs |
| **Database** | PostgreSQL 16 + pgvector | Core entities, embeddings, graph edges |
| **Cache / Queue** | Redis 7 | Job queue, caching, rate limiting |
| **Object Storage** | MinIO (S3-compatible) | Source snapshots, decks, documents |
| **Container** | Docker Compose | Local development environment |

## Services and Databases

### Services

| Service | Port | Description |
|---|---|---|
| `frontend` | 5173 | Vite dev server with HMR, proxies `/api` to backend |
| `api` | 8000 | FastAPI application server with auto-reload |
| `worker` | — | Arq background worker (no HTTP) |
| `postgres` | 5432 | PostgreSQL 16 with pgvector extension |
| `redis` | 6379 | Redis 7 for job queue and caching |
| `minio` | 9000 / 9001 | S3-compatible object storage (API / Console) |
| `minio-init` | — | One-shot bucket creation on first start |

### Databases and Storage

| Data store | What it stores | Architecture reference |
|---|---|---|
| **PostgreSQL** | Core entities: Person, Organization, Opportunity, SourceSnapshot, Observation, Claim, Relationship, ScoreSnapshot, Assessment, DecisionEvent. Also stores graph edges and vector embeddings (pgvector). | `docs/ARCHITECTURE.md:48-59` |
| **Redis** | Arq job queue, result backends, cache for frequent queries, rate-limit counters. | `docs/ARCHITECTURE.md:498` |
| **MinIO** | Immutable source snapshots (decks, PDFs, web captures), uploaded documents, exported reports. | `docs/ARCHITECTURE.md:53, 498` |

## Quick Start

```bash
# 1. Copy environment defaults
cp .env.example .env

# 2. Start the full stack
make up

# 3. Follow logs
make logs

# 4. Check service status
make ps

# 5. Stop everything
make down
```

## Commands

### Makefile shortcuts

| Command | Description |
|---|---|
| `make up` | Build and start all services in detached mode |
| `make down` | Stop all services |
| `make restart` | Restart application containers (frontend, api, worker) |
| `make logs` | Follow all service logs |
| `make ps` | Show service status |
| `make shell-api` | Open a shell in the API container |
| `make shell-db` | Open psql in the database container |
| `make migrate` | Run Alembic database migrations |
| `make lint` | Run Ruff (backend) and ESLint (frontend) |
| `make typecheck` | Run mypy (backend) and tsc (frontend) |
| `make test` | Run pytest (backend) and Vitest (frontend) |
| `make check` | Run lint + typecheck + test |
| `make build` | Build production Docker images |
| `make clean` | Stop stack and remove all data volumes |

### Manual commands

```bash
# Backend (inside container or local venv)
uv run uvicorn app.main:app --reload          # Start API
uv run pytest                                  # Run tests
uv run ruff check .                            # Lint
uv run mypy app                                # Type check

# Frontend (inside container or local)
npm run dev                                    # Start dev server
npm test -- --run                              # Run tests
npm run lint                                   # Lint
npm run typecheck                              # Type check
npm run build                                  # Production build
```

## Repository Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | Repository contract and safety rules for coding agents |
| `docs/ARCHITECTURE.md` | Proposed systems, data flow, and scoring approaches |
| `Problem_Statement.pdf` | Original challenge brief and product requirements |
| `compose.yaml` | Docker Compose development environment |
| `Makefile` | Shortcuts for common Docker Compose and tooling commands |
| `backend/` | FastAPI application, worker, migrations, and tests |
| `frontend/` | Vite + React + Tailwind CSS application and tests |
| `infra/` | Database initialization scripts and infrastructure configs |

## Development

### Adding a new backend module

1. Create `backend/app/modules/<name>/` with `routes.py`, `service.py`, etc.
2. Add the router to `backend/app/api/router.py`.
3. Add Alembic migration if new tables are needed: `alembic revision --autogenerate -m "add <name>"`.

### Adding a new frontend page

1. Create `frontend/src/pages/<Name>.tsx`.
2. Add route in `frontend/src/App.tsx` (once a router is added).
3. Add API client function in `frontend/src/api/<name>.ts`.

### Environment variables

See `.env.example` for all configurable values. The `APP_` prefix is used for backend settings (via `pydantic-settings`).

Inbound pitch decks are PDF-only and are streamed into a temporary quarantine before storage. Production/staging requires `APP_UPLOAD_MALWARE_SCANNER` to name a scanner executable; the API rejects uploads when the scanner is unavailable or reports a finding. Local development intentionally permits structural validation without an external scanner.
