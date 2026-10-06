# Testing

## 1. Pyramid and tooling

| Level | Scope | Tooling | Runs |
|---|---|---|---|
| Backend unit | Pure logic: budget engine, scheduler, policies, prompt rendering, op validation, pagination | pytest | every commit |
| Backend service | Services with real DB + fake providers | pytest-asyncio, factory functions | every commit |
| API integration | HTTP → DB through the real app | httpx `AsyncClient` (ASGI), Postgres + Redis services | every commit |
| Migrations | Upgrade from empty; model/migration drift | `alembic upgrade head`, `alembic check` | every commit |
| AI | Flows/tools with `FakeAIProvider` | pytest | every commit |
| AI evals | Real model, golden prompts, rubric | pytest marker `eval`, manual/nightly | nightly / on prompt change |
| Frontend unit/component | Components, hooks, forms, API client error mapping | Vitest + Testing Library + MSW | every commit |
| E2E | Full user journeys on compose stack with `PROVIDERS_MODE=fake` | Playwright (+ axe) | main + nightly; PRs touching flows |

## 2. Backend test infrastructure

- Test DB (`atu_test`) created once per session and migrated to head. Tests that touch data use the `clean_state`
  fixture, which truncates every model table and flushes the Redis test DB *before* the test (so a failed test
  leaves data to inspect). Chosen over savepoint rollback because the app commits in its own sessions.
- Test settings are pinned in `make_settings()` (never read `.env`) so local configuration can't change results.
- Factories (`tests/factories`) build users, trips, days, items deterministically.
- `as_user(client, user)` helper logs in and sets CSRF; `other_user` fixture for authorization tests.
- Providers injected via `PROVIDERS_MODE=fake`; fake places/geocoding/routing/weather backed by JSON fixtures in
  `tests/fixtures/providers/` (clearly synthetic or recorded with attribution, never presented as live).
- No network: an autouse fixture fails any outbound HTTP not routed to a fake.

## 3. Mandatory test matrix per endpoint

| Case | Expectation |
|---|---|
| Happy path | Correct status + schema |
| Validation | 422 with field-level `errors[]` |
| Unauthenticated | 401 |
| Missing CSRF (unsafe methods) | 403 `CSRF_FAILED` |
| Other user's resource | 404, no data leak |
| Provider/AI failure (if applicable) | Error envelope, no internal details |

## 4. AI test matrix

Structured output valid / malformed JSON / schema-invalid / unknown IDs / foreign IDs; tool success / timeout /
provider 503 / authorization denied; loop limit; refusal; operational fields equal provider values
(hallucination resistance); proposals never auto-applied.

## 5. E2E journeys (MVP)

1. Register → onboarding → Universe.
2. Login / logout / protected-route redirect.
3. Create trip (form) → overview.
4. Describe trip → requirements card → create → generate itinerary (fake AI) → accept proposal.
5. View map; select item ↔ marker sync.
6. Edit itinerary: reorder, move day, edit time, remove + undo.
7. Discover → save place → add to trip day.
8. Budget: set total, add expense in another currency.
9. Chat: ask question → tool status → proposal → accept.
10. A11y smoke (axe) on each main screen; mobile viewport run of journeys 3–7.

## 6. Acceptance criteria (examples)

**Trip creation**
- Given an authenticated user, when they submit a valid destination and dates, then a trip is created with one owner
  traveler, one day per date, and a budget row.
- When `end_date < start_date`, the API returns 422 with `errors[0].field = "end_date"`.
- When another user requests the trip, the API returns 404.
- When the API fails, the UI shows a recoverable error with Retry and preserves form input.

**Itinerary generation**
- Every generated item of kind `place`/`meal` references a `place_id` returned by the place provider.
- No day exceeds the pace cap; no item is scheduled outside known opening hours; walking total respects tolerance.
- Nothing is written to `itinerary_items` until the proposal is accepted.
- If the AI provider fails, the job falls back to deterministic ranking or fails with a user-visible message; it
  never hangs (job timeout).

**AI tools**
- Calling `get_trip_context` with another user's trip ID returns `NOT_FOUND` and logs `status=denied`.

## 7. Seed / test data

Deterministic seeds (fixed UUIDs/dates) for dev (`make seed`) and tests; dev data labeled `[DEV]`; `.test` email
domain; seeding blocked in production.
