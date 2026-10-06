# Architecture Decision Records

Format: Problem · Options · Decision · Reasoning · Consequences · Replacement path.
Status: **Accepted**, **Proposed** (awaiting confirmation), **Superseded**.

---

## ADR-001 — Monorepo with a TypeScript web app and a Python API
**Status:** Accepted (handoff baseline)
- **Problem:** Two languages (TS frontend, Python backend for AI/optimization ecosystem) need to evolve together.
- **Options:** (a) monorepo, pnpm + uv; (b) two repos; (c) all-TypeScript backend.
- **Decision:** (a). `apps/web`, `services/api`, `packages/*`, root Makefile as the cross-language runner.
- **Reasoning:** Atomic changes across API contract + UI; one CI; Python wins for OR-Tools, data/AI libraries.
- **Consequences:** Two toolchains; contract drift risk → mitigated by ADR-003.
- **Replacement path:** Services can be split into separate repos later; boundaries are already process-level.

## ADR-002 — PostgreSQL + pgvector instead of a separate vector database
**Status:** Accepted
- **Problem:** Semantic memory (Phase 18) needs vector search; core data is relational.
- **Options:** (a) pgvector in the primary DB; (b) Pinecone/Qdrant/Weaviate; (c) no vectors.
- **Decision:** (a), extension enabled from Phase 1, tables only in Phase 18.
- **Reasoning:** Per-user corpora are small (thousands of rows/user); user-scoped filtering + joins with trips/places
  are trivial in SQL; one backup/ACL story; no data sync.
- **Consequences:** HNSW index tuning in Postgres; vector workload shares DB resources.
- **Replacement path:** `MemoryIndex` interface; move to a dedicated store if corpus/QPS outgrows Postgres.

## ADR-003 — Pydantic schemas are the API source of truth; TS types are generated
**Status:** Accepted
- **Problem:** Keep frontend types in sync with FastAPI.
- **Options:** (a) hand-written TS types; (b) OpenAPI → `openapi-typescript` generation; (c) tRPC/GraphQL.
- **Decision:** (b) into `packages/types`, committed, CI fails on drift.
- **Consequences:** API field names are snake_case in TS (accepted to avoid a mapping layer).

## ADR-004 — First-party cookie sessions (opaque tokens) instead of JWT
**Status:** Accepted (confirmed 2026-10-06)
- **Problem:** Secure auth for a browser app now and a native app later.
- **Options:** (a) opaque session token in httpOnly cookie, hashed in Postgres; (b) JWT access + refresh tokens;
  (c) hosted auth (Auth.js in Next, Clerk, Supabase Auth).
- **Decision:** (a). Same-origin via Next rewrites; `SameSite=Lax` + CSRF double-submit.
- **Reasoning:** Instant revocation (logout, "sign out everywhere"), no token storage in JS (XSS-resistant), simplest
  correct model; FastAPI remains the single authority (no split auth between Next and Python). Hosted auth adds a
  vendor + cost and makes the Python API depend on a third party for every request.
- **Consequences:** Session lookup per request (cheap indexed query; can be cached in Redis for 60 s).
- **Replacement path:** Native app can use the same opaque token via `Authorization: Bearer` (same `sessions`
  table). OAuth providers attach via `auth_identities` without changing sessions.

## ADR-005 — Application-level AI orchestration; defer LangGraph
**Status:** Accepted
- **Problem:** Multi-step AI flows (extract → search → rank → schedule → summarize) and a tool-calling chat.
- **Options:** (a) plain async Python pipelines + bounded tool loop; (b) LangGraph; (c) autonomous agent framework.
- **Decision:** (a) for MVP.
- **Reasoning:** Flows are mostly linear with deterministic stages; explicit code is easier to test with fakes and
  reason about authorization/cost. No need yet for durable cross-request graph state.
- **Consequences:** We implement our own retry/limits/usage wrappers (small).
- **Replacement path:** Re-evaluate in Phase 12–16 (companion, group conflict resolution). Tools/providers are plain
  functions that a LangGraph node can call unchanged.

## ADR-006 — Map tiles load directly in the browser; everything else goes through the API
**Status:** Accepted (provider choice in ADR-011)
- **Problem:** The handoff requires all provider calls go through the backend; vector tiles are high-volume static
  assets the renderer must fetch directly.
- **Decision:** Tiles/styles/glyphs are fetched by MapLibre from the tile CDN using a **public, domain-restricted**
  key (`NEXT_PUBLIC_MAP_TILES_KEY`). Geocoding, places, routing never use this key from the browser.
- **Consequences:** Tile usage isn't metered by our backend; the provider's dashboard covers it.
- **Replacement path:** Self-host PMTiles (Protomaps) behind our domain to remove the key entirely.

## ADR-007 — Places data: store provider IDs, cache details within provider terms
**Status:** Accepted (provider: Google Places, ADR-012)
- **Problem:** We want canonical `places` rows for joins (itinerary, saves), but providers (notably Google) restrict
  long-term storage of content other than place IDs.
- **Decision:** `places` rows always keep `provider` + `provider_place_id` + our UUID. Detail fields are a cache with
  `details_expire_at` set per provider policy (e.g. Google: refresh on display after expiry; lat/lng cache ≤ 30 days).
  Refresh is lazy on read.
- **Consequences:** Some reads trigger provider calls; budget for it via caching and batching.
- **Replacement path:** Switching provider = new `provider` value; a mapping job can match places across providers
  by name + proximity.

## ADR-008 — No PostGIS for MVP
**Status:** Accepted
- **Problem:** Spatial queries (nearby, bbox).
- **Options:** (a) PostGIS; (b) lat/lng columns + provider-side nearby search.
- **Decision:** (b). Nearby discovery uses the places provider; local spatial work is over small sets (one trip's
  items), done in Python. Official `pgvector/pgvector` image works as-is.
- **Replacement path:** Add PostGIS (custom image with both extensions) + `geography` columns via migration when we
  need DB-side spatial queries (e.g. memories map across all trips).

## ADR-009 — Flexible weighted preferences + behavior signals; `user_places` replaces `saved_places`
**Status:** Accepted
- **Problem:** Preferences are open-ended; the personality engine must learn from saves/rejections/edits.
- **Decision:** Core scheduler inputs as typed columns on `travel_profiles`; long tail as `travel_preferences(key,
  weight −1..1, value jsonb, source, confidence)` with a code-level key registry; append-only `preference_signals`.
  Saved and rejected places share one `user_places` table with a `state` column.
- **Reasoning:** Avoids dozens of rigid columns; registry keeps keys valid; signals give a real learning substrate.
- **Consequences:** Aggregation logic (signals → weights) is application code, tested deterministically.

## ADR-010 — Runtime versions and tooling
**Status:** Accepted
- Python **3.14** (matches local; native `uuid.uuid7()`), Node **22 LTS** in containers (local Node 23 works for
  dev), PostgreSQL **17** (`pgvector/pgvector:pg17`), Redis **7**, pnpm **12** via corepack, uv for Python, arq for jobs.
- As built in Phase 1: Next.js **16.4** (Turbopack, `cacheComponents`), React 19.3, Tailwind 4, shadcn/ui (radix-nova),
  Vitest 5, Playwright 1.63, FastAPI 0.142, SQLAlchemy 2.1, Pydantic 2.13.
- **TypeScript pinned to 5.x**: TypeScript 7 (native compiler) has no JS compiler API, which `openapi-typescript`
  and other tooling still need. Revisit when the tooling supports TS 7.
- **Replacement path:** Versions pinned in Dockerfiles/`.python-version`/`packageManager`; bump deliberately.

## ADR-011 — Map tile provider
**Status:** Accepted (confirmed 2026-10-06) — **MapTiler**
- **Options:** (a) MapTiler (free tier, good styles, key); (b) Stadia Maps; (c) Protomaps self-hosted PMTiles
  (no key, we host the file); (d) Mapbox (requires Mapbox GL for best results; license).
- **Recommendation:** (a) MapTiler for MVP speed; (c) as cost-control path.

## ADR-012 — Places & geocoding provider
**Status:** Accepted (confirmed 2026-10-06) — **Google Places API (New) + Google Geocoding**, with the terms check below as a Phase 5 entry gate
- **Options:**
  - (a) **Google Places API (New) + Geocoding** — best coverage of restaurants/attractions, hours, price level,
    ratings, photos; per-request cost and strict caching/attribution terms; must display on/with Google-compatible
    attribution rules.
  - (b) **Foursquare Places** — good POI/category data, more permissive; weaker in some regions.
  - (c) **Geoapify / OSM (Overpass + Nominatim)** — cheap/free, open data; hours/price/ratings sparse; public
    Nominatim has strict rate limits.
- **Recommendation:** (a) for MVP quality (the Japan test depends on real restaurant data), behind `PlaceProvider` /
  `GeocodingProvider`; fake provider for dev/tests so day-to-day work costs nothing.
- **Note:** Google's terms restrict showing Places content on non-Google maps in some cases — must be verified
  against current terms before committing; if it conflicts with MapLibre, prefer (b).
- **Phase 5 entry gate:** re-read Google Maps Platform terms on (1) displaying Places content on a non-Google map,
  (2) caching limits, (3) attribution. If (1) is disallowed, either switch to Foursquare or show Google content only
  in list/detail views — decision recorded as a new ADR.

## ADR-013 — Routing provider
**Status:** Accepted (confirmed 2026-10-06) — **OpenRouteService**
- **Options:** (a) OpenRouteService (hosted, free tier, walk/drive/cycle, matrix API, no transit); (b) GraphHopper
  (similar, transit via GTFS self-host); (c) Google Routes (transit, cost); (d) self-hosted OSRM (no transit, ops).
- **Recommendation:** (a) for MVP with walking/driving matrices; transit estimates deferred (labeled "transit times
  unavailable" rather than invented). Re-evaluate (c) when transit matters (Japan is transit-heavy — likely Phase 11–12).

## ADR-014 — Background jobs with arq
**Status:** Accepted
- **Options:** Celery, RQ, arq, Dramatiq, FastAPI BackgroundTasks.
- **Decision:** arq — asyncio-native (matches async SQLAlchemy/httpx), Redis-only, small.
- **Replacement path:** Job functions are plain async functions; swap runner if we need scheduling/priority features.
