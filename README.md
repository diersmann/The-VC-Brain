# The VC Brain

Evidence-backed founder intelligence platform. Sources, profiles, and scores founders for venture capital investment decisions.

## Status

Working local product foundation. The repository contains a Docker-first Vite/React frontend, FastAPI API, Arq worker, PostgreSQL/pgvector, Redis, and MinIO stack. Migrations run before API and worker readiness; the local demo seed is synthetic and opt-in.

Implemented foundations include PDF-only inbound submission with idempotency and durable outbox handoff, provenance-linked observations and source snapshots, deterministic scoring/rubric helpers, collector guardrails, explicit failure states, and tested sourcing/inbound/decision views. Authentication and tenant scoping, the complete triage-to-decision lifecycle, real SLA clocks, production telemetry, and several external-provider integrations remain partial or proposed. See [`IMPROVEMENT_BACKLOG.md`](IMPROVEMENT_BACKLOG.md) for the evidence-backed status of each capability.

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

# Optional: add clearly labelled synthetic demo records
make seed-demo

# 3. Follow logs
make logs

# 4. Check service status
make ps

# 5. Stop everything
make down

# Optional reset: stop the stack and delete local PostgreSQL, Redis, MinIO,
# and frontend dependency volumes. This is destructive for local data.
make clean
```

The optional `make seed-demo` command creates two fictional, clearly labelled inbound records and does not call paid or external APIs. It is safe to rerun.

## Current workflow map

The implemented UI route skeleton is:

`/sourcing` → `/inbound` or `/submit` → `/investigated` → `/decisions`

The pages expose truthful loading, empty, partial, and failure states, but the full authenticated triage, diligence, SLA, memo, and investment-decision contract is not complete yet.

## Commands

### Makefile shortcuts

| Command | Description |
|---|---|
| `make up` | Build and start all services in detached mode; migrations run before API/worker readiness |
| `make down` | Stop all services |
| `make restart` | Restart application containers (frontend, api, worker) |
| `make logs` | Follow all service logs |
| `make ps` | Show service status |
| `make shell-api` | Open a shell in the API container |
| `make shell-db` | Open psql in the database container |
| `make migrate` | Run Alembic database migrations |
| `make seed-demo` | Start the stack and seed deterministic, synthetic local demo records |
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

## Troubleshooting

- If `make up` cannot connect to Docker, start Docker Desktop/Engine and rerun it; the command is otherwise non-destructive.
- If the API is not ready, run `make ps` and `docker compose logs migrate api worker`. API and worker startup intentionally waits for a successful migration container.
- If schema state is unclear, run `make migrate` and inspect `make ps`; it is safe to rerun migrations.
- To remove local data and rebuild from an empty database/object store, use `make clean` followed by `make up`.

## Repository Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | Repository contract and safety rules for coding agents |
| `docs/ARCHITECTURE.md` | Target systems, data flow, scoring approaches, and implementation boundaries |
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
2. Add the route in `frontend/src/App.tsx`, lazy-load the page, and preserve the shared loading fallback.
3. Add API client function in `frontend/src/api/<name>.ts`.

### Environment variables

See `.env.example` for all configurable values. Backend settings use the `APP_` prefix in local runs and Docker; `POSTGRES_*` and `MINIO_ROOT_*` remain service-native container credentials.

Website collection accepts only public HTTP(S) URLs, validates redirects, and streams responses up to `APP_WEBSITE_MAX_BYTES`.

Inbound pitch decks are PDF-only and are streamed into a temporary quarantine before storage. Production/staging requires `APP_UPLOAD_MALWARE_SCANNER` to name a scanner executable; the API rejects uploads when the scanner is unavailable or reports a finding. Local development intentionally permits structural validation without an external scanner.
