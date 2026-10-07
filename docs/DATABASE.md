# Database

PostgreSQL 17 with extensions `vector` (pgvector), `citext`, `pg_trgm`. Schema managed **only** by Alembic.

## 1. Conventions

| Rule | Detail |
|---|---|
| Primary keys | `id uuid PRIMARY KEY`, UUIDv7 generated in the application (`uuid.uuid7()`) — time-ordered for index locality |
| Timestamps | `created_at timestamptz NOT NULL DEFAULT now()`, `updated_at timestamptz NOT NULL DEFAULT now()` (set by SQLAlchemy `onupdate`) on every table |
| Enumerations | `text` + `CHECK (col IN (...))`, mirrored by Python `StrEnum` (no Postgres enum types) |
| Money | `numeric(12,2)` + `currency char(3)` (ISO 4217, `CHECK (currency ~ '^[A-Z]{3}$')`) |
| Coordinates | `lat double precision CHECK (lat BETWEEN -90 AND 90)`, `lng double precision CHECK (lng BETWEEN -180 AND 180)` — no PostGIS for MVP (ADR-008) |
| Foreign keys | Always declared; `ON DELETE CASCADE` for owned children, `SET NULL` for references that should survive (e.g. usage logs) |
| Ownership | Every user-owned row carries `user_id`/`owner_id`; every trip child carries `trip_id` |
| Same-trip integrity | Composite FKs (`(trip_day_id, trip_id) → trip_days(id, trip_id)`) so a child can't reference another trip's rows |
| JSONB | Only for genuinely schemaless data (provider payloads, AI structured output, preference values); always validated by a Pydantic model on write |
| Migrations | One Alembic revision per logical change; never edit a merged revision; `alembic check` in CI; data migrations separated from schema migrations |
| Naming | Tables plural snake_case; indexes `ix_<table>_<cols>`; uniques `uq_<table>_<cols>`; checks `ck_<table>_<name>` (SQLAlchemy naming convention configured so Alembic autogenerate is deterministic) |

## 2. Entity-relationship overview

```
users 1─* sessions
users 1─1 travel_profiles
users 1─* travel_preferences
users 1─* preference_signals
users 1─* user_places *─1 places *─1 destinations
users 1─* trips (owner_id)
trips 1─* trip_travelers *─0..1 users
trips 1─* trip_destinations *─1 destinations
trips 1─* trip_places *─1 places
trips 1─* trip_days 1─* itinerary_items *─0..1 places
itinerary_items *─0..1 routes (route_to_next_id)
trips 1─1 budgets
trips 1─* budget_items, expenses
users 1─* conversations 1─* conversation_messages
users 1─* ai_requests 1─* ai_tool_calls
users 1─* ai_jobs, ai_proposals
shared caches: places, destinations, routes, weather_snapshots, fx_rates
later: reservations, trip_timeline_events, memories, media, packing_lists, packing_items, notifications, memory_embeddings
```

## 3. Tables by phase

### Phase 1 — Foundation
Initial migration: `CREATE EXTENSION IF NOT EXISTS vector, citext, pg_trgm;` No tables yet besides `alembic_version`.

### Phase 2 — Auth

**users**
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| email | citext NOT NULL | `uq_users_email` |
| password_hash | text NULL | argon2id; NULL for future OAuth-only users |
| display_name | text NOT NULL | 1–80 chars |
| home_currency | char(3) NOT NULL DEFAULT 'USD' | |
| locale | text NOT NULL DEFAULT 'en' | |
| units | text NOT NULL DEFAULT 'metric' | `CHECK IN ('metric','imperial')` |
| status | text NOT NULL DEFAULT 'active' | `active`, `disabled` |
| email_verified_at | timestamptz NULL | |
| last_login_at | timestamptz NULL | |
| created_at / updated_at | | |

**sessions**
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK users CASCADE | `ix_sessions_user_id` |
| token_hash | bytea NOT NULL | sha256 of the cookie token; `uq_sessions_token_hash` |
| expires_at | timestamptz NOT NULL | sliding idle expiry |
| absolute_expires_at | timestamptz NOT NULL | hard cap |
| last_seen_at | timestamptz NOT NULL | updated at most once per 5 min |
| user_agent | text NULL | truncated 256 |
| ip_prefix | text NULL | /24 or /48 only — no full IPs |
| revoked_at | timestamptz NULL | |
| created_at / updated_at | | |
Index: `ix_sessions_expires_at` (cleanup job).

**auth_identities** *(Phase 2b / when OAuth is added)*: `user_id`, `provider`, `provider_subject`,
`uq(provider, provider_subject)`.

### Phase 3 — Travel profile

**travel_profiles** (1:1 with users)
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK CASCADE | `uq_travel_profiles_user_id` |
| travel_styles | text[] NOT NULL DEFAULT '{}' | e.g. `food`, `culture`, `nature`, `adventure`, `luxury`, `romance` (validated against registry) |
| pace | text NOT NULL DEFAULT 'balanced' | `relaxed`, `balanced`, `packed` |
| budget_style | text NOT NULL DEFAULT 'moderate' | `shoestring`, `moderate`, `comfortable`, `luxury` |
| accommodation_style | text NULL | `hostel`, `budget_hotel`, `boutique`, `luxury`, `apartment` |
| walking_tolerance | text NOT NULL DEFAULT 'medium' | `low`, `medium`, `high` (maps to max walking minutes/day in scheduler) |
| dietary | text[] NOT NULL DEFAULT '{}' | `vegetarian`, `vegan`, `halal`, `kosher`, `gluten_free`, `no_seafood`, … |
| day_start / day_end | time NOT NULL DEFAULT '09:00' / '21:00' | preferred active hours |
| onboarding_completed_at | timestamptz NULL | |
| created_at / updated_at | | |

Core, frequently-queried scheduler inputs are real columns; the long tail lives in `travel_preferences`.

**travel_preferences** — flexible weighted preferences (ADR-009)
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK CASCADE | |
| key | text NOT NULL | from a code registry: `interest.food.street_food`, `interest.nightlife`, `interest.photography`, `avoid.crowds`, `pref.tourist_spots` … |
| weight | numeric(4,3) NOT NULL | `CHECK (weight BETWEEN -1 AND 1)`; negative = dislike |
| value | jsonb NULL | *Not yet created* — added by migration when the first key needs structured detail (e.g. a cuisines list) |
| source | text NOT NULL | `onboarding`, `explicit`, `inferred`, `trip_request` |
| confidence | numeric(4,3) NOT NULL DEFAULT 1 | inferred prefs < 1 |
| created_at / updated_at | | |
Unique `uq_travel_preferences_user_id_key`. Index `ix_travel_preferences_user_id`.

**preference_signals** — append-only behavior log feeding the personality engine. *Deferred to Phase 5*: nothing
emits signals until places can be saved/rejected, so the table (with its `place_id`/`trip_id` FKs) is created then.
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK CASCADE | |
| signal | text NOT NULL | `place_saved`, `place_rejected`, `place_rated`, `itinerary_item_removed`, `itinerary_item_added`, `ai_suggestion_accepted`, `ai_suggestion_rejected`, `place_visited` |
| place_id | uuid FK places SET NULL | |
| trip_id | uuid FK trips SET NULL | |
| value | numeric NULL | rating 1–5 etc. |
| context | jsonb NULL | small, e.g. `{ "category": "museum" }` |
| created_at | | (no updated_at — immutable) |
Index `ix_preference_signals_user_id_created_at`.

### Phase 4 — Trips

**trips**
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| owner_id | uuid FK users CASCADE | `ix_trips_owner_id_start_date` |
| name | text NOT NULL | 1–120 |
| description | text NULL | ≤ 2000 |
| destination_label | text NOT NULL | display text, e.g. "Japan" |
| start_date / end_date | date NULL | NULL while dates undecided; `CHECK (end_date >= start_date)`, `CHECK (end_date - start_date <= 89)` |
| duration_days | smallint NULL | used when dates unknown; `CHECK (1..90)` |
| traveler_count | smallint NOT NULL DEFAULT 1 | `CHECK (1..20)` |
| currency | char(3) NOT NULL | |
| status | text NOT NULL DEFAULT 'planning' | `draft`, `planning`, `ready`, `active`, `completed`, `archived` |
| requirements | jsonb NULL | validated `TripRequirements` (interests, pace, walking, must_have, avoid) |
| cover_image_url | text NULL | |
| version | integer NOT NULL DEFAULT 1 | optimistic concurrency for itinerary-wide operations |
| created_at / updated_at | | |
Constraint: `CHECK ((start_date IS NULL) = (end_date IS NULL))`; `UNIQUE (id, owner_id)` (for composite FKs where useful).

**trip_travelers**
| Column | Type | Notes |
|---|---|---|
| id, trip_id FK CASCADE | | |
| user_id | uuid FK users CASCADE NULL | NULL = non-user companion (name only) |
| display_name | text NOT NULL | |
| role | text NOT NULL | `owner`, `editor`, `viewer` |
| status | text NOT NULL DEFAULT 'active' | `invited`, `active`, `removed` (invites in Phase 16) |
Unique `(trip_id, user_id)` where user_id not null (partial). MVP: owner row created with each trip; authorization
already reads membership, so group travel needs no authz rewrite.

**destinations** (shared, canonical)
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| kind | text NOT NULL | `country`, `region`, `city`, `area` |
| name | text NOT NULL | |
| country_code | char(2) NULL | |
| parent_id | uuid FK destinations NULL | city → country |
| lat, lng | double | centroid |
| bbox | double precision[4] NULL | west, south, east, north |
| timezone | text NULL | IANA |
| provider, provider_ref | text NOT NULL | `uq_destinations_provider_provider_ref` |
| created_at / updated_at | | |
Index: `ix_destinations_name_trgm` (gin_trgm_ops) for autocomplete over cached destinations.

**trip_destinations** — multi-city trips (Tokyo → Kyoto)
`id`, `trip_id` FK CASCADE, `destination_id` FK RESTRICT, `position` smallint, `arrive_date` / `depart_date` date
NULL. Unique `(trip_id, position)`.

**trip_days**
| Column | Type | Notes |
|---|---|---|
| id, trip_id FK CASCADE | | |
| date | date NOT NULL | |
| day_index | smallint NOT NULL | 0-based |
| destination_id | uuid FK destinations NULL | where the night is spent |
| timezone | text NOT NULL | IANA; interprets item times |
| title, notes | text NULL | |
Unique `(trip_id, date)`, `(trip_id, day_index)`, `(id, trip_id)`.
Days are generated by the service when dates are set. Shrinking dates with items on removed days is rejected with
`409 TRIP_DAYS_HAVE_ITEMS` unless the request says `on_removed_days: "move_to_unscheduled" | "delete"`.

### Phase 5 — Places

**places** (shared cache of provider data — see ADR-007 for ToS-driven retention)
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | internal ID used everywhere in our API |
| provider, provider_place_id | text NOT NULL | `uq_places_provider_provider_place_id` |
| name | text NOT NULL | |
| category | text NOT NULL | normalized: `restaurant`, `cafe`, `bar`, `attraction`, `museum`, `park`, `shopping`, `nightlife`, `hotel`, `activity`, `viewpoint`, `transport`, `other` |
| subcategories | text[] NOT NULL DEFAULT '{}' | provider types normalized |
| lat, lng | double NOT NULL | |
| destination_id | uuid FK destinations NULL | |
| address | text NULL | |
| timezone | text NULL | |
| price_level | smallint NULL | 0–4 |
| rating, rating_count | numeric(2,1), integer NULL | |
| opening_hours | jsonb NULL | normalized weekly periods + exceptions |
| attributes | jsonb NULL | website, phone, photo references, accessibility, reservable… |
| details_fetched_at | timestamptz NULL | |
| details_expire_at | timestamptz NULL | after this, refresh before display |
Indexes: `ix_places_destination_id_category`, `ix_places_lat_lng` (btree on (lat, lng) for bounding-box queries),
`ix_places_name_trgm`.

**user_places** (implements the handoff's `saved_places`, plus rejections and ratings — ADR-009)
| Column | Type | Notes |
|---|---|---|
| id, user_id FK CASCADE, place_id FK CASCADE | | |
| state | text NOT NULL | `saved`, `rejected` |
| rating | smallint NULL | `CHECK 1..5` |
| note | text NULL | |
| list_name | text NULL | lightweight collections ("Dream", "Kyoto food") |
Unique `(user_id, place_id)`; index `(user_id, state, created_at DESC)`.

**trip_places**
| Column | Type | Notes |
|---|---|---|
| id, trip_id FK CASCADE, place_id FK RESTRICT | | |
| added_by | uuid FK users SET NULL | |
| source | text NOT NULL | `user`, `ai`, `saved` |
| status | text NOT NULL DEFAULT 'candidate' | `candidate`, `shortlisted`, `rejected` |
| score | numeric(5,4) NULL | AI/recommender relevance |
| reason | text NULL | AI explanation (generated from provider facts + preferences) |
| notes | text NULL | |
Unique `(trip_id, place_id)`.

### Phase 6–7 — Map & itinerary

**itinerary_items**
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| trip_id | uuid NOT NULL | |
| trip_day_id | uuid NULL | NULL = "unscheduled" bucket; FK `(trip_day_id, trip_id) → trip_days(id, trip_id)` CASCADE |
| kind | text NOT NULL | `place`, `meal`, `transit`, `lodging`, `free_time`, `note` |
| place_id | uuid FK places RESTRICT NULL | `CHECK (kind NOT IN ('place','meal') OR place_id IS NOT NULL)` |
| title | text NOT NULL | defaults to place name |
| position | integer NOT NULL | order within day; unique `(trip_day_id, position)` DEFERRABLE INITIALLY DEFERRED |
| start_time / end_time | time NULL | local to `trip_days.timezone`; `CHECK (end_time > start_time)` when both set |
| duration_minutes | smallint NULL | `CHECK 5..1440` |
| status | text NOT NULL DEFAULT 'planned' | `planned`, `confirmed`, `done`, `skipped` |
| locked | boolean NOT NULL DEFAULT false | scheduler must not move it |
| transport_mode_to_next | text NULL | `walk`, `drive`, `transit`, `cycle`, `taxi` |
| route_to_next_id | uuid FK routes SET NULL | |
| estimated_cost | numeric(12,2) NULL | per-party estimate |
| estimated_cost_currency | char(3) NULL | |
| cost_basis | text NULL | `user`, `price_level_model`, `provider` — honesty about where a number came from |
| notes | text NULL | |
| source | text NOT NULL DEFAULT 'user' | `user`, `ai` |
| reason | text NULL | AI explanation |
| created_at / updated_at | | |
Indexes: `ix_itinerary_items_trip_id`, `ix_itinerary_items_trip_day_id_position`.

**routes** (shared cache)
`id`, `cache_key` text unique, `provider`, `mode`, `origin_lat/lng`, `dest_lat/lng`, `distance_m` integer,
`duration_s` integer, `geometry` text (encoded polyline), `computed_at`, `expires_at`.

### Phase 8 — Budget

**budgets**: `id`, `trip_id` FK CASCADE unique, `total_amount numeric(12,2) NULL CHECK >= 0`, `currency char(3)`,
`daily_target numeric(12,2) NULL`, `allocations jsonb NULL` (category → amount, validated).

**budget_items** (planned costs not tied to itinerary items — flights, hotel, pass)
`id`, `trip_id` FK CASCADE, `category` (`accommodation`, `food`, `transport`, `activities`, `shopping`, `other`),
`label`, `amount`, `currency`, `trip_day_id` NULL (composite FK), `per` (`trip`, `person`, `day`), `source`
(`user`, `ai`).

**expenses**
`id`, `trip_id` FK CASCADE, `created_by` FK users SET NULL, `category`, `amount numeric(12,2) CHECK > 0`,
`currency`, `amount_trip_currency numeric(12,2)`, `fx_rate numeric(18,8)`, `fx_date date`, `spent_on date`,
`place_id` NULL, `itinerary_item_id` FK SET NULL, `note`. Index `(trip_id, spent_on)`.

**fx_rates** (shared): `base char(3)`, `quote char(3)`, `on_date date`, `rate numeric(18,8)`, `provider`;
PK `(base, quote, on_date)` (exception to the UUID rule — natural key, pure cache).

The budget engine computes, never stores, derived totals (planned by category/day, spent, remaining, burn rate).

### Phase 9–10 — AI

**conversations**: `id`, `user_id` FK CASCADE, `trip_id` FK trips CASCADE NULL, `kind` (`planner`, `chat`,
`companion`), `title`, `summary` text NULL (rolling summary for long threads), `summary_upto_message_id`,
`archived_at`. Index `(user_id, updated_at DESC)`, `(trip_id)`.

**conversation_messages**: `id`, `conversation_id` FK CASCADE, `role` (`user`, `assistant`, `tool`), `content`
text, `parts` jsonb NULL (structured UI parts: place cards, proposal refs), `tool_call_id` text NULL,
`ai_request_id` FK SET NULL, `token_count` integer NULL, `created_at`. Index `(conversation_id, created_at)`.

**ai_requests** — one row per model call (handoff's `ai_actions`, split for clarity)
| Column | Notes |
|---|---|
| id, user_id (FK SET NULL), trip_id (SET NULL), conversation_id (SET NULL), job_id (SET NULL) | |
| purpose | `extract_requirements`, `suggest_destinations`, `rank_places`, `plan_summary`, `chat`, `summarize_conversation`, … |
| provider, model, tier | |
| prompt_name, prompt_version | |
| provider_request_id | |
| input_tokens, output_tokens, cached_tokens, reasoning_tokens | integer NULL |
| cost_usd | numeric(10,6) — computed from configured price table |
| latency_ms | integer |
| status | `ok`, `error`, `timeout`, `invalid_output`, `refused` |
| error_code | text NULL |
| created_at | |
Index `(user_id, created_at)`, `(created_at)`. **Prompts and completions are not stored here** (privacy); message
content lives in `conversation_messages` where the user can delete it.

**ai_tool_calls**: `id`, `ai_request_id` FK CASCADE, `tool_name`, `arguments` jsonb (redacted), `status`
(`ok`, `error`, `denied`, `timeout`), `latency_ms`, `result_summary` text (short, no raw provider dumps),
`error_code`.

**ai_jobs**: `id`, `user_id` FK CASCADE, `trip_id` FK CASCADE NULL, `kind` (`plan_trip`, …), `status`
(`queued`, `running`, `succeeded`, `failed`, `cancelled`), `progress` jsonb (stage, percent), `input` jsonb,
`proposal_id` FK NULL, `error_code`, `idempotency_key` text, `started_at`, `finished_at`.
Unique `(user_id, idempotency_key)`.

**ai_proposals** — explicit, user-confirmed AI changes
| Column | Notes |
|---|---|
| id, user_id FK CASCADE, trip_id FK CASCADE NULL, conversation_id FK SET NULL | |
| kind | `create_itinerary`, `itinerary_ops`, `save_place`, `update_preferences`, `budget_items` |
| summary | human-readable ("Move Garden Visit to May 12?") |
| payload | jsonb — validated operation list (`{op: "move", item_id, to_day_id, position}`…) |
| base_trip_version | integer — reject apply if trip changed incompatibly |
| status | `pending`, `accepted`, `rejected`, `expired`, `failed`, `superseded` |
| expires_at, decided_at | |
Index `(user_id, status)`, `(trip_id, status)`.

### Later phases (designed, not migrated until the phase starts)

| Table | Phase | Key fields |
|---|---|---|
| weather_snapshots | 11 | `provider`, `lat_r`, `lng_r` (2 decimals), `date`, `kind` (`forecast`/`historical`), `data` jsonb, `fetched_at`, `expires_at`; unique `(provider, lat_r, lng_r, date, kind)` |
| packing_lists / packing_items | 15 | `trip_id`, `user_id`, `label`, `category`, `quantity`, `checked`, `source`, `reason` |
| trip_invitations | 16 | `trip_id`, `email`, `token_hash`, `role`, `expires_at`, `accepted_at` |
| votes / comments | 16 | `trip_id`, `user_id`, `subject_type`, `subject_id`, `value` / `body` |
| trip_timeline_events | 17 | `trip_id`, `user_id`, `occurred_at`, `kind` (`visit`, `photo`, `expense`, `note`), `place_id`, `ref_id` |
| memories | 17 | `user_id`, `trip_id`, `place_id`, `title`, `body`, `favorite`, `occurred_on` |
| media | 17 | `user_id`, `trip_id`, `memory_id`, `storage_key`, `content_type`, `bytes`, `width`, `height`, `taken_at`, `lat`, `lng` (EXIF stripped on public derivatives) |
| reservations | 17+ | `trip_id`, `kind`, `provider_name`, `confirmation_code` (encrypted), `starts_at`, `ends_at`, `place_id` |
| notifications | 12+ | `user_id`, `kind`, `payload`, `read_at`, `send_after` |
| memory_embeddings | 18 | `user_id`, `source_type`, `source_id`, `content_hash`, `embedding vector(N)`, `model`; HNSW index `vector_cosine_ops`; **every query filters by `user_id` first** |

## 4. Ownership & authorization map

| Resource | Owner path | Policy |
|---|---|---|
| sessions, travel_profiles, travel_preferences, preference_signals, user_places, conversations, ai_* | `user_id` | `row.user_id == current_user.id` |
| trips | `owner_id` + `trip_travelers` | view: active traveler; edit: owner/editor; delete: owner |
| trip_days, trip_places, itinerary_items, budgets, budget_items, expenses | `trip_id` | inherit trip policy |
| places, destinations, routes, weather_snapshots, fx_rates | shared | readable by any authenticated user; written only by services |

Repositories for user-owned data take `user_id` as a required argument; there is no unscoped fetch-by-ID method.
Not found and not permitted both return 404.

## 5. Seed data

`app/seed` creates deterministic data (fixed UUIDs, fixed dates relative to a constant anchor) clearly prefixed
`[DEV]` in names, with users on the reserved `example.com` domain (`dev@example.com`; RFC 2606 — `.test` is
rejected by the email validator as a special-use TLD). The dev password comes from `SEED_DEV_PASSWORD`. Places in seed data come from the
**fake** place provider fixtures, never invented as if real. Seeding refuses to run when `APP_ENV=production`.

## 6. Migration workflow

1. Change SQLAlchemy models.
2. `make migration m="add trip_days"` → Alembic autogenerate.
3. Review the generated revision by hand (autogenerate misses CHECK constraints, partial indexes, deferrable
   constraints — write them explicitly).
4. `make migrate` + tests. CI runs `alembic upgrade head` from empty and `alembic check`.
5. Production: migrations run as a release step before new code takes traffic; changes are expand → migrate →
   contract across deploys for anything destructive.
