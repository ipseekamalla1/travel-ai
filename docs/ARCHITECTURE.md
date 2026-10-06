# Architecture

## 1. System overview

```
┌──────────────────────────── Browser (mobile / desktop) ────────────────────────────┐
│ Next.js app (React, TanStack Query, Zustand, MapLibre)                             │
│   • fetches only same-origin /api/v1/*  (cookie session)                           │
│   • loads map tiles directly from tile CDN with a domain-restricted public key     │
└───────────────┬────────────────────────────────────────────────────────────────────┘
                │ HTTPS (same origin; Next rewrites /api/* → api service)
┌───────────────▼──────────────┐      enqueue       ┌───────────────────────────────┐
│ FastAPI (services/api)        │ ─────────────────▶ │ arq worker (same codebase)     │
│  routes → services → repos    │ ◀──── Redis ────── │  AI planning jobs, enrichment  │
│  providers (interfaces)       │   job status/SSE   └──────────────┬────────────────┘
└───────┬───────────┬──────────┘                                   │
        │           │                                              │
   ┌────▼───┐  ┌────▼────┐   ┌─────────────────────────────────────▼─────────────────┐
   │Postgres│  │  Redis  │   │ External: OpenAI · Places · Geocoding · Routing ·       │
   │+pgvector│ │cache/RL/│   │ Open-Meteo · FX · Object storage · Email                │
   └────────┘  │ queue   │   └─────────────────────────────────────────────────────────┘
               └─────────┘
```

**Principle (§9 of handoff):** the browser never talks to OpenAI, places, routing, weather or geocoding providers.
The single exception is **map tiles** (raster/vector tile images and styles), which must stream directly to the map
renderer for performance; they use a public, domain-restricted key that grants nothing beyond tile reads. This is
recorded in ADR-006.

## 2. Monorepo layout

```
/
├── apps/
│   └── web/                     Next.js app
├── services/
│   └── api/                     FastAPI app + arq worker + Alembic
├── packages/
│   └── types/                   OpenAPI-generated TS types (generated, committed, drift-checked in CI)
├── infra/
│   └── docker/                  Dockerfiles, compose overrides, postgres init scripts
├── scripts/                     dev, migrate, seed, gen-types helpers
├── tests/
│   └── e2e/                     Playwright suites (cross-app)
├── docs/
├── docker-compose.yml           (root, so `docker compose up` works from repo root)
├── Makefile                     single entry point for common tasks
├── pnpm-workspace.yaml
├── package.json
└── .env.example
```

Deviation from the handoff: `docker-compose.yml` lives at the root (not `/infra/docker`) so the documented
`docker compose up` works without `-f`. Dockerfiles stay under `infra/docker/`.

Tooling: **pnpm** workspaces (pinned via corepack) for JS; **uv** for Python dependency/venv management;
**Makefile** as the cross-language task runner (`make dev`, `make test`, `make migrate`, `make seed`, `make types`).

## 3. Frontend architecture

### 3.1 Directory structure (`apps/web/src`)

```
app/
  (marketing)/            page.tsx (/), about/, how-it-works/       — static, server components
  (auth)/                 login/, register/                          — redirect to /universe if signed in
  (app)/                  layout.tsx = authenticated shell (bottom nav / left rail)
    universe/
    onboarding/
    trips/
      page.tsx
      new/
      [tripId]/
        layout.tsx         trip workspace shell (tabs, AI panel, map context)
        page.tsx           overview
        itinerary/
        map/
        places/
        budget/
    discover/
    places/[placeId]/
    companion/
    memories/              (Phase 17)
    profile/
    settings/
  layout.tsx, providers.tsx, error.tsx, not-found.tsx, global-error.tsx
proxy.ts                  cookie-presence redirect for (app) routes (Next 16 renamed middleware → proxy)

components/
  ui/                     shadcn/ui primitives, owned and themed (button, input, dialog, drawer, sheet, tabs, toast…)
  layout/                 AppShell, BottomNav, SideRail, PageHeader, EmptyState, ErrorState, Skeletons
  maps/                   MapView, MapMarker, MarkerCluster, RouteLayer, MapControls, MapAdapter
  ai/                     AIMessage, AIActionCard (proposal), WhyThis, AIPromptInput, AITypingState
  (domain display components live in features/*/components)

features/
  auth/                   api.ts, hooks (useSession, useLogin), schemas.ts, components (LoginForm…)
  travel-profile/         onboarding steps, preference editors
  trips/                  trip list, trip form, requirements card
  destinations/
  places/                 PlaceCard, PlaceSearch, save/reject actions
  itinerary/              DayColumn, ItineraryItem, reorder logic, store (selection)
  maps/                   trip-map composition, map ↔ itinerary sync store
  budget/                 BudgetSummary, CategoryBreakdown, ExpenseForm
  companion/              chat thread, SSE stream hook, proposal handling
  memories/               (Phase 17)

lib/
  api/                    client.ts (fetch wrapper, error normalization, CSRF header), query-keys.ts
  auth/                   server helpers (read session cookie in RSC for redirects only)
  maps/                   style URLs, bounds helpers, marker icon registry
  validation/             shared Zod helpers (dates, money, currency)
  format/                 date/time/money/distance formatting (Intl)
stores/                   app-wide Zustand stores (ui.ts: panels, theme)
hooks/                    generic hooks (useMediaQuery, useGeolocation, useDebounce)
types/                    re-exports from @atu/types + UI-only types
styles/                   globals.css, design tokens (CSS variables)
```

Rule: `app/` files are thin — they compose `features/*`. Features may import `components/*` and `lib/*`, never
another feature's internals (only its `index.ts` public surface).

### 3.2 Rendering strategy

- Marketing: static server components.
- `cacheComponents` is enabled (Next 16): anything reading `cookies()`/`headers()` must sit behind `<Suspense>`
  (see Next's "Authentication with Cache Components" guide bundled in `node_modules/next/dist/docs`).
- App routes: server components render the shell and do **auth redirect only**; data is fetched client-side via
  TanStack Query against `/api/v1` so caching, optimistic updates and mutations stay in one model. (We can later
  prefetch on the server with `HydrationBoundary` for first paint where it matters, e.g. trip overview.)
- Map components are client-only (`dynamic(..., { ssr: false })`).

### 3.3 State management

| State | Where |
|---|---|
| Server data (trips, itinerary, places, budget, conversations) | TanStack Query; keys in `lib/api/query-keys.ts` (`['trips', tripId, 'itinerary']`) |
| Optimistic itinerary edits | TanStack Query `onMutate` + rollback; server `version` conflict → refetch + toast |
| Map/itinerary selection, hovered item, visible day, panel open | Zustand `useTripWorkspaceStore` (scoped per trip) |
| Form state | React Hook Form; Zod schemas mirror API schemas (generated types + hand-written refinements) |
| Planner draft prompt | Zustand + `sessionStorage` persistence (survives refresh) |

### 3.4 API layer

- `lib/api/client.ts`: `apiFetch<T>(path, init)` → same-origin fetch, `credentials: 'include'`, JSON, adds
  `X-CSRF-Token` header from the CSRF cookie on unsafe methods, parses the error envelope into a typed `ApiError`
  (`status`, `code`, `fieldErrors`, `requestId`).
- Per-feature `api.ts` exports typed functions using generated types from `@atu/types`.
- 401 → clear query cache, redirect to `/login?next=…`.
- SSE (chat streaming, job progress) via `fetch` + `ReadableStream` reader in `features/companion/hooks/useChatStream`.

### 3.5 Forms & validation

RHF + `zodResolver`. Client validation is UX only; the API re-validates everything. Server field errors from the
error envelope are mapped back onto RHF fields (`setError`).

### 3.6 Map architecture

```
<TripMap>                         features/maps — knows about trips, itinerary, selection
  └── <MapView adapter=maplibre>  components/maps — knows only about generic layers
        ├── MarkerLayer (clustered, GeoJSON source)
        ├── RouteLayer (polyline per day)
        ├── UserLocationLayer
        └── MapControls (zoom, locate, layer filter, fit bounds)
```

- `MapAdapter` interface (`setView`, `fitBounds`, `setSources`, `on('select')`) isolates MapLibre; switching to
  Mapbox/Google later is an adapter swap.
- Data enters the map as GeoJSON derived from TanStack Query data (no separate map fetches).
- **Sync:** selecting an itinerary item sets `selectedItemId` in the workspace store → map `flyTo` + highlight;
  clicking a marker sets the same ID → list scrolls to item / bottom sheet opens with place details.
- Filters (category, day) are store state applied as MapLibre layer filters (no refetch).
- Clustering via MapLibre GeoJSON source clustering.

## 4. Backend architecture

### 4.1 Directory structure (`services/api`)

```
app/
  main.py                    app factory: middleware, routers, exception handlers, lifespan
  core/
    config.py                Settings (pydantic-settings), per-env
    logging.py               structlog JSON config, redaction processor
    security.py              password hashing (argon2id), token generation/hashing, CSRF
    errors.py                AppError hierarchy → error envelope
    middleware.py            request ID, timing, access log
    rate_limit.py            Redis sliding-window limiter dependency
    db.py                    async engine, session factory, `get_session` dependency
    redis.py
  common/
    models.py                Base, UUIDv7 PK mixin, timestamp mixin
    pagination.py            cursor encode/decode, Page[T]
    money.py                 Decimal helpers, currency validation
    time.py                  tz-aware helpers
  auth/                      router, service, models (sessions), dependencies (current_user)
  users/
  policies/                  authorization functions (trip access, etc.) — used by services + AI tools
  travel_profiles/           profile + preferences + preference_signals
  trips/                     trips, travelers, trip_destinations, trip_days generation
  destinations/
  places/                    places cache, user_places, trip_places
  itinerary/                 items, reorder, scheduling (OR-Tools), route enrichment
  routing/                   RoutingService + route cache
  weather/                   WeatherService + snapshot cache
  budget/                    budgets, items, expenses, calculation engine
  fx/                        FxService
  ai/
    providers/               base.py (AIProvider protocol), openai.py, fake.py
    router.py                ModelRouter (tier → model)
    prompts/                 trip_requirements.py, trip_planner.py, chat.py, companion.py … (versioned)
    tools/                   registry.py, context.py, one file per tool group
    context/                 ContextBuilder + token budgeting
    flows/                   extract_requirements.py, plan_trip.py, chat.py
    proposals/               ProposalService: create/validate/apply/expire
    usage.py                 UsageTracker (ai_requests, ai_tool_calls), price table
    schemas.py               Structured output models
  conversations/             conversations + messages, SSE endpoints
  integrations/              provider implementations (google_places.py, openmeteo.py, ors.py, maptiler_geocoding.py,
                             frankfurter.py, local_storage.py, s3_storage.py) + fakes
  workers/                   arq settings + job functions
  seed/                      deterministic dev/test seed
  api/
    v1.py                    mounts module routers under /api/v1
migrations/                  Alembic env + versions
tests/
  unit/  integration/  api/  ai/  factories/  conftest.py
pyproject.toml
```

### 4.2 Layering rules

| Layer | May | Must not |
|---|---|---|
| Router | Parse/validate input (Pydantic), resolve `current_user`, call one service method, map result to response schema | Contain business logic or queries |
| Service | Business rules, call policies, orchestrate repositories/providers, own transaction boundaries | Know about HTTP (no `Request`, no `HTTPException`) — raise `AppError`s |
| Repository | SQLAlchemy queries; user-data methods require an owner/user argument | Call providers or other services |
| Provider | Talk to one external API, map to domain DTOs, handle provider errors → `ProviderError` | Touch the DB |
| Policy | Pure functions over loaded entities + user | Perform I/O beyond what's passed in |

Dependency injection via FastAPI `Depends` (session, current user, services constructed per request). Providers
are built once in lifespan from settings (`PROVIDERS_MODE=real|fake`) and exposed via a `Providers` container.

### 4.3 Provider abstractions

```python
class PlaceProvider(Protocol):
    name: str
    async def search(self, q: PlaceSearchQuery) -> list[PlaceSummary]: ...
    async def details(self, provider_place_id: str) -> PlaceDetails: ...
    async def nearby(self, lat: float, lng: float, radius_m: int, categories: list[PlaceCategory]) -> list[PlaceSummary]: ...

class GeocodingProvider(Protocol):
    async def geocode(self, text: str, *, bias: LatLng | None = None) -> list[GeocodeResult]: ...
    async def reverse(self, point: LatLng) -> GeocodeResult | None: ...

class RoutingProvider(Protocol):
    async def route(self, legs: list[LatLng], mode: TravelMode) -> RouteResult: ...
    async def matrix(self, points: list[LatLng], mode: TravelMode) -> DurationMatrix: ...   # for the scheduler

class WeatherProvider(Protocol):
    async def daily_forecast(self, point: LatLng, start: date, end: date) -> list[DailyWeather]: ...
    async def hourly_forecast(self, point: LatLng, day: date) -> list[HourlyWeather]: ...

class AIProvider(Protocol):     # see AI.md
class StorageProvider(Protocol):
    async def put(self, key: str, data: AsyncIterator[bytes], content_type: str) -> StoredObject: ...
    async def presigned_get(self, key: str, ttl: timedelta) -> str: ...
    async def delete(self, key: str) -> None: ...
class FxProvider(Protocol):
    async def rates(self, base: str, on: date) -> dict[str, Decimal]: ...
```

Each provider call is wrapped by a common `instrumented()` helper: timeout, retry with jittered backoff on
retryable errors (429/5xx/timeouts), latency + status logging, and a simple Redis-backed circuit breaker per
provider. Domain services depend only on the protocols.

### 4.4 Caching (Redis + Postgres)

| Data | Cache | Key | TTL | Shared across users? |
|---|---|---|---|---|
| Geocoding | Redis | `geo:v1:{provider}:{sha1(normalized text + bias)}` | 30 d | Yes (public data) |
| Place search | Redis | `places:search:v1:{provider}:{sha1(query params)}` | 24 h (ToS-bounded) | Yes |
| Place details | Postgres `places` + Redis | `places:detail:v1:{provider}:{id}` | per ToS (see ADR-007) | Yes |
| Route | Postgres `routes` (dedup by key) | `route:v1:{provider}:{mode}:{rounded coords}` | 30 d | Yes |
| Distance matrix | Redis | `matrix:v1:{provider}:{mode}:{sha1(sorted points)}` | 7 d | Yes |
| Weather forecast | Postgres `weather_snapshots` + Redis | `wx:v1:{provider}:{lat2}:{lng2}:{date}` | 1–3 h (forecast), ∞ (historical) | Yes |
| FX | Postgres `fx_rates` | `{base}:{date}` | ∞ for past dates | Yes |
| AI results | Only deterministic, non-personal (e.g. destination info) | `ai:v1:{prompt_version}:{sha1(input)}` | 7 d | Only if input has no user data |

Rule: **any cache entry built from user-private data is keyed by `user_id` or not cached at all.** Public provider
data is shared.

### 4.5 Background jobs (arq)

Used for work that can exceed a comfortable HTTP request (≈ 10 s): itinerary generation, place enrichment, route
matrix warm-up, (later) media processing and embeddings. Job state is persisted in Postgres (`ai_jobs`, see
DATABASE.md; a finished planning job points at the `ai_proposals` row it produced) and progress events are published to Redis pub/sub for SSE. Jobs are
idempotent and retry-safe.

### 4.6 Observability

- structlog JSON logs; every log line carries `request_id`, `user_id` (UUID only), `route`, `duration_ms`.
- `X-Request-ID` accepted from proxy or generated; returned in responses and error envelopes.
- Provider calls log `provider`, `operation`, `latency_ms`, `status`, `cache_hit`.
- AI calls write `ai_requests` rows (model, tokens, cost, latency, status).
- Redaction processor strips `password`, `token`, `authorization`, `cookie`, `api_key`, emails in free text.
- Later (Phase 20): OpenTelemetry traces, Sentry, metrics dashboards.

## 5. Authentication & authorization

See [SECURITY.md](SECURITY.md) and ADR-004.

- Registration/login via email + password (argon2id).
- On login the API creates a `sessions` row and sets cookie `atu_session` = random 256-bit token
  (`HttpOnly; Secure; SameSite=Lax; Path=/`); DB stores only `sha256(token)`.
- Sliding expiry (14 days idle, 60 days absolute). Logout revokes the row. "Sign out everywhere" revokes all.
- CSRF: double-submit token (`atu_csrf` readable cookie + `X-CSRF-Token` header) on unsafe methods, plus
  `SameSite=Lax` and Origin checking.
- `current_user` dependency resolves the session; services receive a `User` and call policies.
- Authorization: `policies.trips.require_trip_access(user, trip, Permission.EDIT)`; repositories never expose
  unscoped `get_by_id` for user-owned resources. Not-owned resources return **404** (not 403) to avoid ID probing.

## 6. AI orchestration

Summary only — see [AI.md](AI.md). Flows are plain Python async functions composed from typed steps; tools are
registered functions with Pydantic schemas and per-tool authorization; write intents produce proposals. LangGraph is
deferred (ADR-005).

## 7. Itinerary engine

```
candidates (provider places, user-saved, AI-ranked with scores)
   │
   ├─ clustering by area (k-medoids on travel-time matrix, per city)
   ├─ assignment of clusters → days (respect trip_destinations date ranges)
   └─ per-day sequencing: OR-Tools routing with time windows
        constraints: opening hours, durations, meal windows, max activities (pace),
                     max walking minutes (walking tolerance), locked items, day start/end
        objective: maximize Σ score − λ·travel_time
   │
   ▼
ScheduledDay[] → validated → proposal (or direct write for manual "re-optimize day" with confirmation)
```

Fallback when OR-Tools finds no feasible solution in the time limit: greedy nearest-neighbour with time-window
checks, and items that don't fit are returned as `unscheduled` with a reason. Duration defaults per category come
from a table (museum 120 min, café 45 min, …), overridable by user.

## 8. Infrastructure

### 8.1 Local development

```
docker compose up            # web, api, worker, postgres, redis (hot reload via bind mounts)
make migrate                 # alembic upgrade head (also run automatically by the api entrypoint in dev)
make seed                    # deterministic dev data (users dev+alice@example.test etc.)
```

Native option (faster on macOS): `docker compose up postgres redis` + `pnpm dev` + `uv run fastapi dev`.

Ports are configurable via `.env` (`WEB_PORT`, `API_PORT`, `POSTGRES_PORT`, `REDIS_PORT`) with defaults 3000 /
8000 / 5432 / 6379. Health checks: `pg_isready`, `redis-cli ping`, API `/api/v1/health/ready`.

### 8.2 Environment variables

See `.env.example` (created in Phase 1). Groups:

| Group | Variables |
|---|---|
| Core | `APP_ENV`, `LOG_LEVEL`, `API_BASE_URL`, `WEB_BASE_URL`, `CORS_ORIGINS` |
| DB/cache | `DATABASE_URL`, `REDIS_URL` |
| Auth | `AUTH_SECRET` (CSRF/HMAC), `SESSION_IDLE_DAYS`, `SESSION_ABSOLUTE_DAYS` |
| AI | `OPENAI_API_KEY`, `AI_MODEL_SIMPLE`, `AI_MODEL_STANDARD`, `AI_MODEL_ADVANCED`, `AI_MODEL_VISION`, `AI_MODEL_EMBEDDING`, `AI_MONTHLY_BUDGET_USD`, `AI_USER_DAILY_REQUEST_LIMIT` |
| Providers | `PROVIDERS_MODE` (`real`/`fake`), `PLACES_PROVIDER`, `PLACES_API_KEY`, `GEOCODING_PROVIDER`, `GEOCODING_API_KEY`, `ROUTING_PROVIDER`, `ROUTING_API_KEY`, `WEATHER_PROVIDER`, `WEATHER_API_KEY` (optional) |
| Storage | `STORAGE_DRIVER` (`local`/`s3`), `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_BUCKET`, `STORAGE_LOCAL_PATH` |
| Web (public) | `NEXT_PUBLIC_MAP_STYLE_URL`, `NEXT_PUBLIC_MAP_TILES_KEY` (domain-restricted tile key only) |
| Web (server) | `API_INTERNAL_URL` (rewrite target) |

### 8.3 CI

GitHub Actions, path-filtered jobs: `web` (pnpm install, lint, typecheck, vitest, build), `api` (uv sync, ruff,
mypy, pytest with Postgres+Redis service containers, `alembic upgrade head`, `alembic check` for model/migration
drift), `types` (regenerate OpenAPI types, fail on diff), `e2e` (compose stack, fake providers; on main + nightly).

## 9. Cross-cutting conventions

- **Time:** store `timestamptz` in UTC; trip-local times (`itinerary_items.start_time`) are `time` + the day's
  `date` interpreted in the trip/destination IANA timezone stored on `trip_days.timezone`.
- **Money:** `numeric(12,2)` + ISO-4217 `char(3)`; never floats. Conversions store the rate used.
- **IDs:** UUIDv7 (time-ordered, generated in Python 3.14 `uuid.uuid7()`).
- **Enums:** Postgres native enums avoided (painful migrations); use `text` + `CHECK` constraints mirrored by Python
  `StrEnum`.
- **Naming:** snake_case DB, snake_case JSON in API (the TS client uses the generated snake_case types directly to
  avoid a mapping layer).
