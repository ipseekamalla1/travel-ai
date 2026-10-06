# AI Travel Universe — Project Map

> Status: **Phase 1 (Foundation) complete.** This map is the single entry point into the system design. Each section summarizes one layer and links to the detailed document that owns it.
>
> Last updated: 2026-10-06

```
PRODUCT → UX → FRONTEND → BACKEND → DATABASE → API → AI → TOOLS → EXTERNAL SERVICES
        → INFRASTRUCTURE → TESTING → DEPLOYMENT → ROADMAP
```

| Layer | Owning document |
|---|---|
| Product vision, users, journeys, MVP | [PRODUCT.md](PRODUCT.md) |
| Screens, navigation, states, design language | [UX.md](UX.md) |
| System architecture, frontend + backend structure, providers, infra | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Entities, relationships, constraints, migrations | [DATABASE.md](DATABASE.md) |
| REST contracts, errors, pagination | [API.md](API.md) |
| AI orchestration, tools, prompts, cost, failure handling | [AI.md](AI.md) |
| Threat model and controls | [SECURITY.md](SECURITY.md) |
| Test strategy and acceptance criteria | [TESTING.md](TESTING.md) |
| Environments, CI/CD, deployment | [DEPLOYMENT.md](DEPLOYMENT.md) |
| Phases and milestones | [ROADMAP.md](ROADMAP.md) |
| Architecture Decision Records | [DECISIONS.md](DECISIONS.md) |

---

## 1. Product

**What it is:** an AI-powered personal travel operating system that learns *how the user travels* and supports the
whole lifecycle: **Dream → Discover → Plan → Explore → Remember → Learn → Next trip.**

**Target users (MVP):** independent leisure travelers (solo and couples) planning 3–21 day trips, comfortable on
mobile web, who currently stitch together Google Maps lists, spreadsheets, blogs and chat assistants.

**Three modes:**

| Mode | Device bias | Core jobs |
|---|---|---|
| Before the trip | Desktop + mobile | Describe trip, discover places, build itinerary, map, budget |
| During the trip | Mobile-first | Today view, next activity, nearby, weather, companion, expenses |
| After the trip | Both | Timeline, photos, favorites, spending, AI story, searchable memories |

**MVP (11 capabilities, §56 of the handoff):** register → travel profile → create trip → describe trip naturally →
AI recommendations → generate itinerary → view on map → modify itinerary → save places → basic budget → trip-aware
AI chat. MVP acceptance test is the "7-day Japan, $2,500, food/scenery/shopping/romance, relaxed, little walking"
request (see [PRODUCT.md §6](PRODUCT.md)).

**Explicitly not MVP:** voice, vision, group travel, semantic memory, packing, advanced notifications, social,
native app, admin system.

## 2. UX

**Navigation**

```
Marketing (public)       /  /about  /how-it-works
Auth (public)            /login  /register
App (authenticated)
├── /universe            Home: "your world of travel"
├── /onboarding          Travel-profile onboarding (first login)
├── /trips               Trip list + "New trip"
│   ├── /trips/new       Describe naturally OR structured form
│   └── /trips/[tripId]
│       ├── (overview)   Summary, map preview, itinerary preview, budget, weather, AI
│       ├── /itinerary   Day-by-day plan, synced with map
│       ├── /map         Full-screen map
│       ├── /places      Trip candidate/shortlisted places
│       └── /budget      Budget, categories, expenses
├── /discover            Destinations + places discovery (save / reject / rate / add to trip)
├── /places/[placeId]    Place detail
├── /companion           Trip-aware AI chat (live companion in Phase 12)
├── /memories            (Phase 17)
├── /profile             Travel profile + preferences
└── /settings            Account, units, currency, privacy, sessions
```

- **Mobile:** bottom tab bar (Universe · Trips · Discover · Companion · Profile); trip workspace uses a segmented
  control (Overview · Plan · Map · Budget) with a persistent AI button; map is a bottom-sheet experience.
- **Desktop:** left rail; trip workspace is a split view — itinerary (left) ↔ map (right) — with a slide-over AI panel.
- **Every data-dependent view** defines loading (skeleton), empty (with a primary action), error (with retry) and
  partial-degradation states (e.g. "Weather unavailable" chip rather than a broken page).
- **AI changes are proposals:** rendered as a diff card with **Accept / Cancel**; never silent writes.

Details: [UX.md](UX.md).

## 3. Frontend (`apps/web`)

| Concern | Choice |
|---|---|
| Framework | Next.js (App Router) + React + TypeScript (strict) |
| Styling / UI | Tailwind CSS + shadcn/ui (Radix primitives) + project design tokens |
| Server state | TanStack Query (all API data) |
| Client state | Zustand (UI-only: map selection, panel state, draft planner input) |
| Forms | React Hook Form + Zod |
| API types | Generated from FastAPI OpenAPI → `packages/types` (openapi-typescript) |
| API client | Thin typed `fetch` wrapper (`lib/api`), same-origin `/api/v1/*` via Next rewrites |
| Maps | MapLibre GL JS behind a `MapAdapter` component boundary |
| Auth | httpOnly session cookie set by API; `proxy.ts` (Next 16's renamed middleware) redirects when absent; server is the authority |

Structure is **feature-based**: `src/features/<feature>/{api,components,hooks,schemas,store}`; `src/app` only
composes features into routes; `src/components/ui` holds the design system. Details:
[ARCHITECTURE.md §3](ARCHITECTURE.md#3-frontend-architecture).

## 4. Backend (`services/api`)

FastAPI, Pydantic v2, SQLAlchemy 2 (async, asyncpg), Alembic, Redis, arq workers.

```
Route (HTTP, auth dependency, schema in/out)
  → Service (business rules, authorization, transactions)
    → Repository (SQLAlchemy queries, always scoped)
    → Provider (Places / Geocoding / Routing / Weather / AI / Storage / FX) → external API
```

**Domain modules:** `auth`, `users`, `travel_profiles`, `trips`, `destinations`, `places`, `itinerary`,
`routing`, `weather`, `budget`, `ai`, `conversations`, `memories` (later), `media` (later), `notifications` (later).
Each module owns `router.py`, `schemas.py`, `service.py`, `repository.py`, `models.py`.

**Cross-cutting:** `core/` (config, logging, security, errors, request-id middleware, rate limiting),
`common/` (pagination, money, time), `integrations/` (provider implementations), `workers/` (arq jobs).

**Authorization:** a `policies` module (`can_view_trip`, `can_edit_trip`, …) used by services *and* AI tools.
Repositories expose only owner-scoped query methods for user data. Details:
[ARCHITECTURE.md §4](ARCHITECTURE.md#4-backend-architecture).

## 5. Database

PostgreSQL 17 + pgvector (extension enabled from day 1, used from Phase 18). UUIDv7 primary keys, `timestamptz`
everywhere, Alembic-only schema changes.

```
users ─┬─ sessions
       ├─ travel_profiles (1:1)
       ├─ travel_preferences (key/value, weighted)
       ├─ preference_signals (event log: save / reject / rate / edit)
       ├─ user_places ── places ── destinations
       ├─ conversations ── conversation_messages
       ├─ ai_requests ── ai_tool_calls
       ├─ ai_proposals
       └─ trips ─┬─ trip_travelers
                 ├─ trip_destinations ── destinations
                 ├─ trip_places ── places
                 ├─ trip_days ── itinerary_items ── places, routes
                 ├─ budgets, budget_items, expenses
                 └─ (later) reservations, trip_timeline_events, memories, media, packing_*
shared caches: places, destinations, routes, weather_snapshots, fx_rates
```

Ownership rule: every user-owned row has `user_id`/`owner_id`; every trip child has `trip_id` with composite FKs
guaranteeing a child can't point at another trip's day. Details: [DATABASE.md](DATABASE.md).

## 6. API

REST, JSON, prefix `/api/v1`, cookie auth, RFC 9457-style error envelope with `code`, field-level `errors[]` and
`request_id`. Cursor pagination. Optimistic concurrency on itinerary via `version`. Long AI jobs are
`202 Accepted` + job resource + SSE/poll. Endpoints are introduced per phase. Details: [API.md](API.md).

## 7. AI

Application-level orchestration (no autonomous agents). Components:

| Component | Responsibility |
|---|---|
| `AIProvider` | Vendor adapter (OpenAI first): structured output, tool calls, streaming, embeddings |
| `ModelRouter` | Maps task tier (`simple` / `standard` / `advanced` / `vision` / `voice`) → configured model |
| `PromptRegistry` | Versioned prompts in `app/ai/prompts/*.py` |
| `ContextBuilder` | Bounded, task-specific context (token budgets per slice) |
| `ToolRegistry` | Typed tools with Pydantic args/results, per-tool authorization, timeout, caching |
| Flows | `extract_trip_requirements`, `plan_trip` pipeline, `chat` tool loop, (later) `companion` |
| `ProposalService` | AI write intents become `ai_proposals` the user accepts/cancels |
| `UsageTracker` | `ai_requests` / `ai_tool_calls`: model, tokens, cost, latency, status |

**Hard rule:** the LLM never invents coordinates, hours, prices, distances, travel times, weather or availability.
It selects among provider-returned IDs; the backend validates every referenced ID. Scheduling is deterministic
(OR-Tools / heuristics), not LLM arithmetic. Details: [AI.md](AI.md).

## 8. Tools (AI-callable)

| Tool | Kind | Phase |
|---|---|---|
| `get_trip_context`, `get_itinerary`, `get_user_preferences` | read | 9–10 |
| `geocode_location`, `search_places`, `get_place_details` | read (provider) | 9 |
| `get_route`, `get_weather` | read (provider) | 9–11 |
| `calculate_budget` | read (deterministic) | 10 |
| `propose_itinerary_change`, `propose_save_place` | write → proposal | 10 |
| `get_nearby_places`, `get_current_context` | read | 12 |
| `save_memory`, `search_memories` | write/read | 17–18 |

Every tool receives a `ToolContext(user_id, conversation_id, trip_id?)` and calls the same policy functions as REST.

## 9. External services

| Capability | Abstraction | Initial provider (proposed) | Notes |
|---|---|---|---|
| LLM | `AIProvider` | OpenAI | Models configured via env per tier |
| Map tiles | `MapAdapter` (frontend) | MapLibre + MapTiler (ADR-011) | Public key is domain-restricted |
| Geocoding | `GeocodingProvider` | Google Geocoding (ADR-012) | Cached in Redis + `destinations` |
| Places | `PlaceProvider` | Google Places API (New) (ADR-012) | ToS check is a Phase 5 entry gate |
| Routing | `RoutingProvider` | OpenRouteService (ADR-013) | No transit; shown as unavailable, never invented |
| Weather | `WeatherProvider` | Open-Meteo | No key for non-commercial use |
| Optimization | in-process | OR-Tools | Deterministic scheduling |
| FX rates | `FxProvider` | Frankfurter (ECB) | Daily rates, cached |
| Storage | `StorageProvider` | Local FS (dev) → S3-compatible (prod) | Phase 17 |
| Email | `Notifier` | Console (dev) → Resend/SES (prod) | Only needed for password reset |

## 10. Infrastructure

```
docker compose up
  web       Next.js dev server          :3000
  api       FastAPI (uvicorn --reload)  :8000
  worker    arq worker (AI jobs)        —
  postgres  pgvector/pgvector:pg17      :5432
  redis     redis:7                     :6379
```

Tooling: pnpm workspaces (via corepack) for JS, uv for Python, Makefile task runner, GitHub
Actions CI (lint, typecheck, tests, build, migration check). Config via `.env` (see `.env.example`); no server
secrets in `NEXT_PUBLIC_*`. Details: [ARCHITECTURE.md §8](ARCHITECTURE.md#8-infrastructure) and
[DEPLOYMENT.md](DEPLOYMENT.md).

## 11. Testing

| Layer | Tooling |
|---|---|
| Backend unit / service | pytest, pytest-asyncio, fake providers |
| Backend API + DB | httpx AsyncClient against a real Postgres (testcontainers or compose service), per-test transaction rollback |
| AuthZ | Parametrized "other user" tests for every user-owned endpoint and every AI tool |
| AI | Fake `AIProvider` with scripted outputs: malformed JSON, unknown IDs, tool timeouts; recorded-fixture evals |
| Frontend | Vitest + Testing Library + MSW |
| E2E | Playwright against compose stack with fake AI/providers (`PROVIDERS_MODE=fake`) |

Details and acceptance criteria: [TESTING.md](TESTING.md).

## 12. Deployment

Containerized web + api + worker; managed Postgres (with pgvector) and Redis; S3-compatible storage. Proposed
first target: a single-region PaaS (Fly.io / Render / Railway) — **decided in Phase 20**, not now. Alembic
migrations run as a release step. Details: [DEPLOYMENT.md](DEPLOYMENT.md).

## 13. Roadmap

Phases 0–20 from the handoff. MVP = Phases 1–10 (with a thin slice of 11). See [ROADMAP.md](ROADMAP.md).

---

## 14. Decisions

Confirmed 2026-10-06 (see [DECISIONS.md](DECISIONS.md)):

| Decision | Choice | ADR |
|---|---|---|
| Places + geocoding | Google Places API (New) + Google Geocoding — terms check before Phase 5 | ADR-012 |
| Map tiles | MapTiler | ADR-011 |
| Routing | OpenRouteService (walk/drive/cycle; transit deferred) | ADR-013 |
| Auth | First-party opaque session cookies | ADR-004 |
| Runtimes | Python 3.14, Node 22 LTS (containers), Postgres 17 + pgvector, Redis 7, pnpm, uv | ADR-010 |

Still open (not blocking Phase 1):
- **OpenAI model IDs per tier** — set via `AI_MODEL_*` env vars before Phase 9; an OpenAI API key is needed then.
- **API keys** for Google Maps Platform, MapTiler and OpenRouteService — needed from Phases 5–6; fake providers
  cover development until then.

## 15. Foundation implementation plan (Phase 1) — ✅ done 2026-10-06

Order follows §68 of the handoff. Each step ends green before the next. Deviations are listed at the end.

1. Root: `.gitignore`, `.editorconfig`, `README.md`, `Makefile`, `.env.example`, `pnpm-workspace.yaml`,
   root `package.json` (corepack-pinned pnpm).
2. `apps/web`: `create-next-app` (TS, App Router, Tailwind, ESLint, `src/`), shadcn/ui init, TanStack Query
   provider, Zustand, RHF+Zod, Prettier, Vitest + Testing Library, Playwright skeleton, design tokens, app shell
   (marketing / auth / app route groups with placeholder-free minimal pages), `/api` rewrite to FastAPI.
3. `services/api`: uv project, FastAPI app factory, settings (pydantic-settings), structlog JSON logging,
   request-ID middleware, error envelope + handlers, `/api/v1/health` (liveness) and `/api/v1/health/ready`
   (DB + Redis), async SQLAlchemy engine/session, Alembic with initial migration (extensions: `pgvector`,
   `citext`), ruff + mypy, pytest with DB fixtures, arq worker skeleton.
4. `packages/types`: OpenAPI → TS generation script (`pnpm gen:types`), CI drift check.
5. `infra/docker`: Dockerfiles (web, api) + `docker-compose.yml` with health checks, named volumes,
   `.env`-driven ports.
6. `scripts/`: `dev`, `migrate`, `seed` (deterministic dev seed, clearly marked), `gen-types`.
7. CI: GitHub Actions — web (lint, typecheck, test, build), api (ruff, mypy, pytest with Postgres + Redis
   services, `alembic upgrade head` + `alembic check`), types drift.
8. Verify: `docker compose up` → web :3000 renders, api :8000 `/api/v1/health/ready` = ok; all tests pass.
9. Commit in logical steps (`chore(repo)`, `feat(web)`, `feat(api)`, `chore(infra)`, `ci`, `docs`).

**Phase 1 deviations from this plan (as built):**
- `packages/config` was not created — shared config lives at the root (`.prettierrc.json`, `.editorconfig`);
  revisit if a second JS app appears.
- No `seed` script yet: there are no domain tables to seed. It arrives with Phase 2 (users).
- No pre-commit hooks; `make check` and CI enforce the same checks.
- App route group `(app)` is not scaffolded — routes are created in the phase that implements them, so no
  placeholder pages exist.
