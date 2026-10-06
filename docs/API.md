# API

REST over HTTPS, JSON, base path **`/api/v1`**. The FastAPI OpenAPI document (`/api/v1/openapi.json`) is the
machine-readable source of truth; this file is the human contract and the place where endpoints are agreed
**before** they're implemented. Endpoints are built phase by phase — the list below is not a mandate to build them
all at once.

## 1. Conventions

| Topic | Rule |
|---|---|
| Auth | `atu_session` httpOnly cookie. Unsafe methods also require `X-CSRF-Token` matching the `atu_csrf` cookie |
| Content | `application/json; charset=utf-8`; snake_case fields; dates `YYYY-MM-DD`; times `HH:MM` (local to the trip day); timestamps RFC 3339 UTC |
| Money | `{ "amount": "123.45", "currency": "JPY" }` — amount as **string** decimal to avoid float loss |
| IDs | UUID strings |
| Success | Return the resource directly (no `data` wrapper). Create → `201` + `Location`. Delete → `204` |
| Lists | `{ "items": [...], "next_cursor": "opaque" \| null }`; `?limit=` (default 20, max 100) & `?cursor=` |
| Partial update | `PATCH` with only changed fields (JSON merge semantics). `PUT` used only for whole-document replacement (travel profile) |
| Concurrency | Itinerary-wide operations send `If-Match: "<trip.version>"`; mismatch → `412 VERSION_CONFLICT` |
| Idempotency | `Idempotency-Key` header on AI job creation and expense creation; replay returns the original response |
| Long work | `202 Accepted` + job resource; progress via `GET /jobs/{id}` or SSE `GET /jobs/{id}/events` |
| Rate limits | `429` with `Retry-After`; stricter buckets for auth and AI routes |
| Request ID | `X-Request-ID` on every response; included in error body |

### 1.1 Error envelope (RFC 9457 style)

```json
{
  "type": "https://errors.atu.dev/validation",
  "title": "Validation failed",
  "status": 422,
  "code": "VALIDATION_ERROR",
  "detail": "One or more fields are invalid.",
  "errors": [
    { "field": "end_date", "code": "DATE_BEFORE_START", "message": "End date must be on or after start date." }
  ],
  "request_id": "01J9Z…"
}
```

Content type `application/problem+json`. No stack traces or provider error bodies are ever returned.

| Status | `code` examples |
|---|---|
| 400 | `BAD_REQUEST`, `INVALID_CURSOR` |
| 401 | `UNAUTHENTICATED`, `SESSION_EXPIRED` |
| 403 | `CSRF_FAILED`, `FORBIDDEN` (only where existence is already known, e.g. viewer trying to edit) |
| 404 | `NOT_FOUND` (also used for resources the user may not see) |
| 409 | `EMAIL_TAKEN`, `TRIP_DAYS_HAVE_ITEMS`, `PROPOSAL_NOT_PENDING` |
| 412 | `VERSION_CONFLICT` |
| 422 | `VALIDATION_ERROR` (field errors) |
| 429 | `RATE_LIMITED`, `AI_QUOTA_EXCEEDED` |
| 502/503/504 | `PROVIDER_UNAVAILABLE`, `PROVIDER_TIMEOUT`, `AI_UNAVAILABLE` |
| 500 | `INTERNAL_ERROR` |

## 2. Endpoints by phase

### Phase 1 — Health
| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Liveness: `{ "status": "ok" }` |
| GET | `/health/ready` | Readiness: checks DB + Redis; `503` with failing component names |

### Phase 2 — Auth
| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/auth/register` | `{ email, password, display_name }` | `201` `User`; sets session + CSRF cookies |
| POST | `/auth/login` | `{ email, password }` | `200` `User`; sets cookies. Generic `401 INVALID_CREDENTIALS` (no user enumeration) |
| POST | `/auth/logout` | — | `204`; revokes session, clears cookies |
| POST | `/auth/logout-all` | — | `204` |
| GET | `/auth/me` | — | `200` `User` or `401` |
| GET | `/auth/csrf` | — | `200 { csrf_token }` and sets cookie (bootstrap for first unsafe call) |

`User = { id, email, display_name, home_currency, locale, units, created_at }` (`onboarding_completed` is added in
Phase 3 with the travel profile).

**As built (Phase 2):**
- CSRF bootstrap: the web client calls `GET /auth/csrf` before its first unsafe request when no `atu_csrf` cookie
  exists, and on `403 CSRF_FAILED` refreshes the token once and retries. Login/register rotate the CSRF token.
- `POST /auth/logout` is idempotent (204 even without a valid session) so clients can always clear a stale cookie.
- Rate limits: `RATE_LIMIT_AUTH_PER_MINUTE` (default 10) per IP for login and register; half that per email for login.
- `EMAIL_TAKEN` (409) on register is a deliberate enumeration trade-off — see SECURITY.md §3.
Password rules: 10–128 chars, checked against a small common-password list; no composition rules (NIST 800-63B).

### Phase 3 — Profile & travel profile
| Method | Path | Notes |
|---|---|---|
| GET / PATCH | `/me` | display name, home currency, locale, units |
| GET | `/me/travel-profile` | `TravelProfile` incl. `preferences[]` |
| PUT | `/me/travel-profile` | Replace core profile fields |
| PATCH | `/me/travel-profile/preferences` | `{ upsert: [{ key, weight, value? }], remove: [key] }` |
| POST | `/me/travel-profile/complete-onboarding` | Sets `onboarding_completed_at` |
| GET | `/meta/preference-keys` | Registry of allowed preference keys + labels (drives onboarding UI) |

### Phase 4 — Trips
| Method | Path | Notes |
|---|---|---|
| GET | `/trips?status=&cursor=` | `TripSummary[]` ordered upcoming first |
| POST | `/trips` | `TripCreate { name, destination_label, destinations?: [{ destination_id }], start_date?, end_date?, duration_days?, traveler_count, currency, budget_total?, requirements? }` → `201 Trip` (creates owner traveler, days, budget) |
| GET | `/trips/{trip_id}` | `Trip` (incl. destinations, travelers, budget summary, version) |
| PATCH | `/trips/{trip_id}` | Date changes regenerate days; `?on_removed_days=` required if removed days have items |
| DELETE | `/trips/{trip_id}` | Owner only, `204` |
| GET | `/trips/{trip_id}/days` | `TripDay[]` |
| PATCH | `/trips/{trip_id}/days/{day_id}` | title, notes |

Validation: `end_date >= start_date`; trip length ≤ 90 days; either dates or `duration_days`; currency ISO-4217;
`start_date` may be in the past only when `status` is `completed` (importing past trips, later).

### Phase 5 — Destinations & places
| Method | Path | Notes |
|---|---|---|
| GET | `/destinations/search?q=` | Geocoding-backed, cached; returns `Destination[]` (persisted canonical rows) |
| GET | `/places/search?q=&destination_id=&near=lat,lng&category=&open_at=&cursor=` | Provider-backed `PlaceSummary[]` with user state (`saved`/`rejected`) merged |
| GET | `/places/{place_id}` | `PlaceDetails` (refreshes if `details_expire_at` passed) |
| PUT | `/places/{place_id}/state` | `{ state: "saved" \| "rejected", rating?, note?, list_name? }` — records preference signal |
| DELETE | `/places/{place_id}/state` | Clear saved/rejected |
| GET | `/me/places?state=saved&cursor=` | User's saved places |
| GET | `/trips/{trip_id}/places?status=` | Trip candidate places |
| POST | `/trips/{trip_id}/places` | `{ place_id, status? }` |
| PATCH / DELETE | `/trips/{trip_id}/places/{trip_place_id}` | |

### Phase 6–7 — Itinerary & map
| Method | Path | Notes |
|---|---|---|
| GET | `/trips/{trip_id}/itinerary` | `{ version, days: [{ day, items[] }], unscheduled: [] }` — one call powers both list and map (includes lat/lng and route polylines) |
| POST | `/trips/{trip_id}/itinerary/items` | `{ trip_day_id \| null, kind, place_id?, title?, position?, start_time?, duration_minutes?, notes? }` |
| PATCH | `/trips/{trip_id}/itinerary/items/{item_id}` | times, duration, notes, status, locked, transport mode |
| DELETE | `/trips/{trip_id}/itinerary/items/{item_id}` | records `itinerary_item_removed` signal |
| POST | `/trips/{trip_id}/itinerary/move` | `{ item_id, to_day_id \| null, to_position }` with `If-Match` — atomic reorder/move |
| POST | `/trips/{trip_id}/days/{day_id}/optimize` | Returns a **proposal** (re-sequenced day), does not write |
| GET | `/trips/{trip_id}/days/{day_id}/routes?mode=` | Legs between consecutive items (provider-backed, cached) |

Note: the handoff listed `PUT /api/itinerary/{id}`. Items are nested under trips instead so the trip ID is always
in the path and authorization is a single trip check.

### Phase 8 — Budget
| Method | Path | Notes |
|---|---|---|
| GET | `/trips/{trip_id}/budget` | `BudgetSummary { total, currency, planned_by_category, planned_by_day, estimated_from_itinerary, spent_by_category, spent_total, remaining, daily_target, per_day_remaining, warnings[] }` |
| PATCH | `/trips/{trip_id}/budget` | total, daily target, allocations |
| GET / POST | `/trips/{trip_id}/budget/items` | planned cost lines |
| PATCH / DELETE | `/trips/{trip_id}/budget/items/{id}` | |
| GET / POST | `/trips/{trip_id}/expenses` | POST converts to trip currency via FX (rate stored) |
| PATCH / DELETE | `/trips/{trip_id}/expenses/{id}` | |

### Phase 9 — AI trip planner
| Method | Path | Notes |
|---|---|---|
| POST | `/ai/trip-requirements` | `{ text, trip_id? }` → `TripRequirementsDraft { requirements, missing_fields[], assumptions[], destination_candidates[] }` (synchronous, SIMPLE tier, ≤ 10 s). Nothing is persisted except usage. |
| POST | `/trips/{trip_id}/plan` | `{ regenerate_days?: [day_id], instructions? }` + `Idempotency-Key` → `202 Job` |
| GET | `/jobs/{job_id}` | `Job { status, progress { stage, percent }, proposal_id?, error? }` |
| GET | `/jobs/{job_id}/events` | SSE: `progress`, `done`, `error` |
| GET | `/proposals/{proposal_id}` | `Proposal { kind, summary, payload, preview, status, expires_at }` — `preview` renders resulting itinerary |
| POST | `/proposals/{proposal_id}/accept` | Applies atomically in one transaction; `409` if not pending, `412` if trip version moved incompatibly |
| POST | `/proposals/{proposal_id}/reject` | `{ feedback? }` → preference signal |

### Phase 10 — AI chat
| Method | Path | Notes |
|---|---|---|
| GET / POST | `/conversations` | `POST { trip_id?, kind }` |
| GET | `/conversations/{id}/messages?cursor=` | newest-first pages |
| POST | `/conversations/{id}/messages` | `{ content }` → **SSE stream**: `message.delta`, `tool.started`, `tool.finished` (name + short status only), `proposal.created`, `message.completed`, `error` |
| DELETE | `/conversations/{id}` | Deletes messages; usage rows keep only non-content metadata |

### Phase 11 — Weather
| Method | Path | Notes |
|---|---|---|
| GET | `/trips/{trip_id}/weather` | Daily forecast per trip day/destination where within forecast horizon; `available: false` otherwise (never fabricated) |
| GET | `/trips/{trip_id}/weather/advisories` | Weather-vs-itinerary conflicts with suggested proposals |

### Phase 12 — Companion
| Method | Path | Notes |
|---|---|---|
| POST | `/companion/context` | `{ trip_id, location: { lat, lng, accuracy_m }, local_time }` → snapshot (today, next item, weather now, nearby) |
| POST | `/conversations/{id}/messages` | same endpoint, `kind=companion`, with `client_context` (location/time) per message |

Later phases (voice `/ai/voice/*`, vision `/ai/vision/analyze`, packing, groups, memories) are specified when the
phase starts.

## 3. Key schemas (abridged)

```jsonc
// Trip
{
  "id": "…", "name": "Japan for two", "destination_label": "Japan",
  "destinations": [{ "id": "…", "name": "Tokyo", "arrive_date": "2027-05-10", "depart_date": "2027-05-14" }],
  "start_date": "2027-05-10", "end_date": "2027-05-16", "duration_days": 7,
  "traveler_count": 2, "currency": "USD", "status": "planning",
  "requirements": { "interests": ["food","scenery","shopping","romance"], "pace": "relaxed", "walking": "low" },
  "budget": { "total": { "amount": "2500.00", "currency": "USD" }, "remaining": { "amount": "1840.00", "currency": "USD" } },
  "my_role": "owner", "version": 7, "created_at": "…", "updated_at": "…"
}

// ItineraryItem
{
  "id": "…", "trip_day_id": "…", "kind": "place", "position": 2,
  "title": "Shinjuku Gyoen", "start_time": "10:00", "end_time": "11:30", "duration_minutes": 90,
  "place": { "id": "…", "name": "Shinjuku Gyoen", "lat": 35.685, "lng": 139.710, "category": "park",
             "opening_hours_today": "09:00–17:30" },
  "status": "planned", "locked": false, "transport_mode_to_next": "walk",
  "leg_to_next": { "duration_s": 840, "distance_m": 1100, "provider": "ors" },
  "estimated_cost": { "amount": "3.40", "currency": "USD", "basis": "provider" },
  "source": "ai", "reason": "Calm garden walk fits your relaxed pace and love of scenery; flat paths.",
  "warnings": [{ "code": "CLOSES_SOON", "message": "Closes 30 min after planned end." }]
}
```

## 4. Acceptance criteria pattern

Every endpoint ships with tests for: happy path, validation failure (field errors), unauthenticated (401), another
user's resource (404), and provider/AI failure where applicable (5xx envelope, no leak). See
[TESTING.md](TESTING.md).
