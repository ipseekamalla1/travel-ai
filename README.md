# AI Travel Universe

An AI-powered personal travel operating system: **Dream → Discover → Plan → Explore → Remember → Learn → Next trip.**
It learns how you travel and builds plans from real places, real opening hours and real travel times — the AI
interprets verified data and proposes changes; it never invents operational facts or edits your plans silently.

> **Status:** Phase 1 (Foundation) complete — monorepo, web app shell, API service, database, cache, worker,
> Docker, tests and CI. Product features start in Phase 2 (auth). See [docs/ROADMAP.md](docs/ROADMAP.md).

## Architecture

```
Browser ──▶ Next.js (apps/web) ──/api/* rewrite──▶ FastAPI (services/api) ──▶ PostgreSQL + pgvector
                                                        │                 ──▶ Redis (cache, rate limits, jobs)
                                                        └── providers ──▶ OpenAI · Google Places · OpenRouteService · Open-Meteo
                                           arq worker (services/api) ◀── Redis queue
```

The browser only talks to our own origin; secrets and providers stay server-side. Full design:
[docs/PROJECT_MAP.md](docs/PROJECT_MAP.md) → [ARCHITECTURE](docs/ARCHITECTURE.md) · [DATABASE](docs/DATABASE.md) ·
[API](docs/API.md) · [AI](docs/AI.md) · [UX](docs/UX.md) · [SECURITY](docs/SECURITY.md) ·
[TESTING](docs/TESTING.md) · [DEPLOYMENT](docs/DEPLOYMENT.md) · [DECISIONS](docs/DECISIONS.md).

## Project structure

```
apps/web/            Next.js 16 (App Router, React 19, TypeScript, Tailwind 4, shadcn/ui, TanStack Query, Zustand)
services/api/        FastAPI, Pydantic, SQLAlchemy 2 (async), Alembic, arq worker
  app/core/          config, logging, errors, request-ID middleware, db, redis
  app/<domain>/      feature modules (router → service → repository) — added per phase
  migrations/        Alembic revisions
  tests/             unit, API and migration tests
packages/types/      TypeScript types generated from the API's OpenAPI schema
tests/e2e/           Playwright end-to-end tests
infra/docker/        Dockerfiles, Postgres init scripts
docs/                Product and system design
```

## Prerequisites

- Docker (with Compose v2)
- Node.js ≥ 22 with corepack (`npm install -g corepack@latest && corepack enable` — older bundled corepack versions
  fail with "Cannot find matching keyid")
- [uv](https://docs.astral.sh/uv/) for Python (`brew install uv` or `pip install uv`); Python 3.14 is installed by uv
  if needed

## Quick start (everything in Docker)

```bash
cp .env.example .env        # then set AUTH_SECRET (command in the file); change ports if they're taken
docker compose up --build   # or: make up
```

| Service | URL |
|---|---|
| Web | http://localhost:3000 |
| API | http://localhost:8000/api/v1/health/ready |
| API docs (non-production) | http://localhost:8000/api/v1/docs |
| Postgres | localhost:5432 (`POSTGRES_PORT`) — user/password/db `atu` |
| Redis | localhost:6379 (`REDIS_PORT`) |

The API container applies migrations on start in development. Ports are configurable in `.env`
(`WEB_PORT`, `API_PORT`, `POSTGRES_PORT`, `REDIS_PORT`); if you change `POSTGRES_PORT`, update the host URLs
(`DATABASE_URL`, `TEST_DATABASE_URL`) to match.

## Native development (faster reload)

```bash
make setup     # install JS + Python deps, Playwright browser, create .env
make infra     # Postgres + Redis in Docker
make api       # migrate + FastAPI with reload on :8000
make worker    # arq worker (optional until jobs exist)
make web       # Next.js on :3000, proxies /api/* to API_INTERNAL_URL
```

## Testing

```bash
make check     # lint + typecheck + generated-types check + API and web tests (what CI runs)
make test-api  # pytest — needs Postgres/Redis (make infra); uses the separate atu_test database
make test-web  # Vitest + Testing Library
make up && make e2e   # Playwright against the running stack (desktop + mobile, includes axe a11y checks)
```

## Environment variables

All variables are documented in [.env.example](.env.example). Key rules:

- `.env` is git-ignored; never commit real secrets.
- Server-only secrets (`OPENAI_API_KEY`, `GOOGLE_MAPS_API_KEY`, `OPENROUTESERVICE_API_KEY`, `AUTH_SECRET`, storage
  keys) must **never** use the `NEXT_PUBLIC_` prefix. The only public key is the domain-restricted map-tiles key.
- `PROVIDERS_MODE=fake` (default) uses deterministic fixtures so development costs nothing; production refuses to
  start with fake providers or a weak `AUTH_SECRET`.

## Common tasks

| Task | Command |
|---|---|
| New migration | `make migration m="add trips"` then review the file |
| Apply migrations | `make migrate` |
| Regenerate API types after changing API schemas | `make types` |
| Format code | `make format` |
| All targets | `make help` |
