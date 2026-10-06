# Roadmap

Status legend: ✅ done · 🟡 in progress · ⬜ not started

| Phase | Name | Status | Exit criteria |
|---|---|---|---|
| 0 | Project map | 🟡 | Docs complete; open decisions confirmed |
| 1 | Foundation | ⬜ | `docker compose up` → web :3000 + api `/health/ready` ok; lint/typecheck/tests green locally and in CI |
| 2 | Auth | ⬜ | Register/login/logout/me; protected routes; CSRF; rate limits; authz test harness |
| 3 | Travel profile | ⬜ | Onboarding; profile + preferences editable; signals table recording |
| 4 | Trips | ⬜ | CRUD; days generated; travelers (owner); budget row; overview page |
| 5 | Destinations + places | ⬜ | Geocoding, search, details, save/reject/rate, trip places — real provider + fake provider |
| 6 | Map | ⬜ | Map with markers, clusters, filters, selection, route layer, list ↔ map sync |
| 7 | Itinerary | ⬜ | Items CRUD, move/reorder with concurrency, times/durations, legs, warnings |
| 8 | Budget | ⬜ | Budget, items, expenses with FX, summary calculations |
| 9 | AI trip planner | ⬜ | Requirements extraction; plan job; proposal accept; MVP Japan prompt passes rubric |
| 10 | AI chat | ⬜ | Streaming chat, tools, proposals, usage tracking |
| — | **MVP release** | ⬜ | Phases 1–10 + forecast display; E2E suite green |
| 11 | Weather intelligence | ⬜ | Forecast per day; itinerary advisories with swap proposals |
| 12 | Live companion | ⬜ | Location/time-aware context, nearby ranking, today view, offline-readable itinerary |
| 13 | Voice | ⬜ | STT → companion → TTS via `voice` tier; push-to-talk UI |
| 14 | Vision | ⬜ | Image analyze endpoint (landmark/menu/sign/food); save result to trip |
| 15 | Packing | ⬜ | Generated, checkable lists from weather + activities + profile |
| 16 | Group travel | ⬜ | Invitations, roles, per-traveler prefs, voting, comments, conflict-aware planning |
| 17 | Memories | ⬜ | Media upload, timeline, memories, AI story from recorded data only |
| 18 | Semantic memory | ⬜ | Embeddings + user-scoped retrieval answering history questions |
| 19 | Polish | ⬜ | Motion, a11y audit, perf budgets, empty/error state audit |
| 20 | Production | ⬜ | Deploy target chosen, monitoring, error reporting, backups, hardening, cost dashboards |

## Phase details (MVP)

### Phase 1 — Foundation
Monorepo, Next.js app shell with design tokens + route groups, FastAPI app factory with config/logging/errors/
request-ID/health, async SQLAlchemy + Alembic (extensions migration), Redis, arq worker skeleton, Docker Compose with
health checks, `.env.example`, ESLint/Prettier/ruff/mypy, Vitest/pytest/Playwright skeletons, OpenAPI → TS types,
GitHub Actions CI, README. **No product features.**

### Phase 2 — Auth
`users`, `sessions` migrations; argon2id; cookie sessions; CSRF; `/auth/*`; `current_user` dependency; policy
module + "other user" test helpers; login/register pages; middleware redirect; rate limiting on auth routes.

### Phase 3 — Travel profile
`travel_profiles`, `travel_preferences`, `preference_signals`; preference-key registry; onboarding flow; profile
page.

### Phase 4 — Trips
`trips`, `trip_travelers`, `destinations` (minimal), `trip_destinations`, `trip_days`, `budgets`; trip CRUD, list,
overview, structured create form.

### Phase 5 — Destinations + places
Geocoding + places providers (real + fake), caching, `places`, `user_places`, `trip_places`; Discover, place
detail, saved places.

### Phase 6 — Map
MapAdapter + MapLibre implementation; trip map; selection store; clustering; route layer (from routing provider).

### Phase 7 — Itinerary
`itinerary_items`, `routes`; itinerary API + UI; drag/keyboard reorder; legs; warnings (opening hours, tight
transfers).

### Phase 8 — Budget
`budget_items`, `expenses`, `fx_rates`; budget engine; budget UI.

### Phase 9 — AI trip planner
AI provider/router/prompts/usage; `ai_requests`, `ai_jobs`, `ai_proposals`; requirements extraction; plan_trip
pipeline incl. OR-Tools scheduler; proposal accept/reject; planner UI.

### Phase 10 — AI chat
`conversations`, `conversation_messages`, `ai_tool_calls`; tool registry; SSE chat; proposal cards; summaries.

## Explicitly deferred
Voice, vision, group travel, semantic memory, advanced notifications, social, native app (evaluate Expo after MVP
is stable — backend is API-first so a native client can reuse it), admin system.
