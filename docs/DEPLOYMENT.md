# Deployment

> Phase 0: target platform is **not chosen yet** (decided in Phase 20). This document defines what any target must
> provide and how releases work, so foundation work stays portable.

## 1. Environments

| Env | Purpose | Providers | Data |
|---|---|---|---|
| `local` | Development (`docker compose up`) | fake by default; real opt-in via `.env` | dev seed |
| `test` | CI | fake only, network blocked | factories |
| `staging` | Pre-production (from Phase 20) | real, low quotas | synthetic |
| `production` | Users | real | real, backed up |

## 2. Runtime units

| Unit | Image | Scaling |
|---|---|---|
| web | `infra/docker/web.Dockerfile` (Next.js standalone output; `API_INTERNAL_URL` is a **build arg** because rewrites are resolved at build time) | stateless, horizontal |
| api | `infra/docker/api.Dockerfile` (uvicorn, multiple workers) | stateless, horizontal |
| worker | same image as api, `arq` entrypoint | horizontal by queue depth |
| postgres | managed Postgres 17 with pgvector | vertical; PITR backups |
| redis | managed Redis 7 | cache/queue (non-durable data only) |
| object storage | S3-compatible (Phase 17) | — |

Candidate platforms: Fly.io, Render, Railway (simple, container-native); AWS (ECS + RDS + ElastiCache) if
requirements grow. Requirement for Postgres: pgvector available.

## 3. Release process

1. CI green on `main` (lint, typecheck, tests, build, migration check, types drift).
2. Build and tag images with git SHA.
3. Release step: `alembic upgrade head` (one-off job) — migrations are backward compatible with the previous
   release (expand → migrate → contract).
4. Roll out api/worker, then web.
5. Smoke: `/api/v1/health/ready`, login, trip list.
6. Rollback: redeploy previous image; destructive migrations are never in the same release as the code that stops
   using a column.

## 4. Production configuration checklist (Phase 20)

`APP_ENV=production`, Secure cookies, HSTS, strict CSP, CORS locked, `PROVIDERS_MODE=real`, fake providers and seed
refuse to load, debug off, OpenAPI docs disabled or auth-protected, Sentry + structured logs shipped, uptime checks,
AI budget alerts, DB backups + restore drill, secrets in platform store, rate limits tuned.
