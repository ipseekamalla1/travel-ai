# AI

The AI is an **orchestration layer** over verified data, not a source of facts.

```
USER ─▶ INTENT ─▶ TRIP CONTEXT ─▶ TOOLS ─▶ VALIDATED DATA ─▶ PLANNING / REASONING ─▶ STRUCTURED RESULT ─▶ PROPOSAL ─▶ USER
```

## 1. Non-negotiable rules

1. The LLM never produces operational data: coordinates, opening hours, prices, distances, travel times, weather,
   availability. Those come from providers via tools and are attached by the backend, not copied from model text.
2. Any model output that drives application logic is a **structured output** validated by Pydantic. Invalid output
   is never written to the database.
3. The model may only reference entities by IDs that the backend gave it in this request (place IDs, item IDs, day
   IDs). Unknown IDs → output rejected or item dropped with a logged `invalid_reference`.
4. Every tool enforces authorization with the same policy functions as REST. **The AI is not a security boundary.**
5. Meaningful changes are **proposals** the user accepts (`ai_proposals`), never silent writes.
6. Context is selected and bounded per task; no database dumps.
7. Every model call is measured (`ai_requests`) — tokens, cost, latency, status.
8. When data is missing or uncertain, the AI says so (e.g. "Opening hours unavailable for this place").

## 2. Components (`services/api/app/ai`)

### 2.1 `AIProvider` (providers/)

```python
class AIProvider(Protocol):
    name: str
    async def generate_structured(self, *, model: str, messages: list[Msg], schema: type[T],
                                  timeout_s: float, metadata: CallMeta) -> StructuredResult[T]: ...
    async def generate_with_tools(self, *, model: str, messages: list[Msg], tools: list[ToolSpec],
                                  timeout_s: float, metadata: CallMeta) -> ToolTurn: ...
    def stream_with_tools(self, *, model: str, messages: list[Msg], tools: list[ToolSpec],
                          metadata: CallMeta) -> AsyncIterator[StreamEvent]: ...
    async def embed(self, *, model: str, texts: list[str]) -> list[list[float]]: ...   # Phase 18
```

- `OpenAIProvider`: OpenAI Responses API; structured outputs via strict JSON schema derived from the Pydantic model;
  function tools for tool calls; streaming for chat. Returns usage (input/output/cached/reasoning tokens).
- `FakeAIProvider`: scripted responses keyed by `(purpose, call index)` for tests, E2E and offline development.
  Clearly dev/test-only; refuses to load when `APP_ENV=production`.
- Domain code never imports the OpenAI SDK.

### 2.2 `ModelRouter`

Maps a **tier** to a configured model; flows ask for a tier, never a model name.

| Tier | Used for | Env |
|---|---|---|
| `simple` | Requirement extraction, classification, titles, conversation summaries | `AI_MODEL_SIMPLE` |
| `standard` | Place ranking + reasons, chat turns, recommendations | `AI_MODEL_STANDARD` |
| `advanced` | Hard multi-constraint planning narratives, conflict resolution (groups) | `AI_MODEL_ADVANCED` |
| `vision` | Image understanding (Phase 14) | `AI_MODEL_VISION` |
| `voice` | STT/TTS (Phase 13) | `AI_MODEL_STT`, `AI_MODEL_TTS` |
| `embedding` | Semantic memory (Phase 18) | `AI_MODEL_EMBEDDING` |

Router also supports per-purpose overrides (`AI_MODEL_OVERRIDES='{"rank_places":"…"}'`) and a fallback model per
tier used on provider 5xx/timeouts. Model **prices** live in `ai/pricing.py` (per-model input/output/cached price
per 1M tokens), updated by hand and versioned — cost is an estimate, labeled as such.

### 2.3 `PromptRegistry` (prompts/)

One module per prompt family; each exports versioned prompt objects:

```python
TRIP_REQUIREMENTS = Prompt(
    name="trip_requirements", version="2026-10-06.1", tier="simple",
    system=..., render=lambda inp: [...],   # pure function of typed input
    output_schema=TripRequirementsDraft,
)
```

Files: `trip_requirements.py`, `destination_suggestions.py`, `place_ranking.py`, `plan_summary.py`, `chat.py`,
`conversation_summary.py`, later `companion.py`, `vision.py`, `memory_story.py`, `packing.py`.
The prompt name + version is logged on every `ai_requests` row so regressions can be traced to a prompt change.
User-provided text is always placed in delimited user content, never concatenated into system instructions.

### 2.4 `ContextBuilder` (context/)

Builds the minimum context for a task from typed "slices", each with a token budget:

| Slice | Contents | Budget (approx.) |
|---|---|---|
| `profile` | travel profile + top-N preferences by |weight| | 400 |
| `trip_header` | name, dates, destinations, travelers, currency, requirements | 300 |
| `itinerary_window` | e.g. today ± 1 day, compact item lines with IDs | 1,200 |
| `budget_summary` | computed totals | 200 |
| `weather` | relevant days only | 300 |
| `candidates` | place candidates with ID, name, category, price level, rating, area, hours today | 3,000 |
| `conversation` | rolling summary + last K turns | 2,000 |
| `client_context` | location, local time (companion) | 100 |

Each flow declares which slices it needs. Slices render compact text (not JSON dumps of rows). Older conversation
turns are folded into `conversations.summary` by a `simple`-tier summarization when the thread exceeds the budget.

### 2.5 `ToolRegistry` (tools/)

```python
@tool(name="search_places", kind=ToolKind.READ, timeout_s=8, cache=True)
async def search_places(ctx: ToolContext, args: SearchPlacesArgs) -> SearchPlacesResult: ...
```

- `ToolContext` = `user`, `db session`, `providers`, `trip` (pre-authorized when the conversation is trip-bound),
  `request_id`, `budget` (remaining tool calls/time).
- Args and results are Pydantic models; the JSON schema sent to the model is generated from them.
- Tools that take a `trip_id` call `require_trip_access(ctx.user, trip_id, …)` — even if the conversation is bound
  to a trip (the model could pass a different ID).
- Results are compact, include IDs, and mark provenance (`source: "google_places"`, `fetched_at`).
- Errors are returned to the model as structured `{ "error": "PROVIDER_UNAVAILABLE", "retryable": true }`, not
  exceptions, so it can explain gracefully.
- Write tools (`propose_itinerary_change`, `propose_save_place`, `propose_preference_update`) only create
  `ai_proposals` and return the proposal ID + summary.

| Tool | Args | Returns |
|---|---|---|
| `get_trip_context` | `trip_id` | header, destinations, days with IDs |
| `get_itinerary` | `trip_id`, `day_ids?` | compact items with IDs, times, places |
| `get_user_preferences` | — | profile + top preferences |
| `geocode_location` | `query`, `near?` | candidates with provider coords |
| `search_places` | `query?`, `destination_id \| near`, `categories?`, `open_at?`, `price_max?` | ≤ 15 summaries |
| `get_place_details` | `place_id` | hours, price level, rating, address |
| `get_route` | `from`, `to` (place IDs or coords), `mode` | distance, duration (provider) |
| `get_weather` | `destination_id \| lat,lng`, `dates` | daily/hourly forecast or `unavailable` |
| `calculate_budget` | `trip_id`, `hypothetical_changes?` | deterministic summary |
| `propose_itinerary_change` | `trip_id`, `ops[]`, `summary` | proposal ID (validated ops) |
| `propose_save_place` | `place_id`, `trip_id?` | proposal ID |

### 2.6 Flows (flows/)

Flows are explicit async pipelines. They are not autonomous agents; the only open-ended loop is the chat tool loop,
which is bounded.

#### Flow A — `extract_trip_requirements` (Phase 9, sync)
1. Input: free text (≤ 2,000 chars) + profile slice.
2. `simple` tier → `TripRequirementsDraft`:
   ```python
   class TripRequirementsDraft(BaseModel):
       destinations: list[DestinationMention]       # names as written, e.g. "Japan"
       duration_days: int | None
       start_date: date | None; end_date: date | None
       traveler_count: int | None
       budget: MoneyMention | None                   # amount + currency as stated; currency None if unstated
       budget_scope: Literal["total","per_person","per_day"] | None
       interests: list[InterestKey]                   # from registry
       pace: Literal["relaxed","balanced","packed"] | None
       walking: Literal["low","medium","high"] | None
       must_have: list[str]; avoid: list[str]
       assumptions: list[str]                         # anything inferred, shown to user
       missing_fields: list[str]
   ```
3. Backend post-processing: geocode destination mentions (provider) → `destination_candidates`; validate dates
   (end ≥ start, not in the past, ≤ 90 days); interests validated against registry (unknown dropped).
4. Return draft to UI; user edits/confirms → normal `POST /trips`. **Nothing is committed from AI output directly.**

#### Flow B — `plan_trip` (Phase 9, background job)
| Stage | Kind | Detail |
|---|---|---|
| 1. Load | deterministic | trip, requirements, profile, saved places for destinations |
| 2. City split | AI (`standard`) + deterministic | If trip is country-level ("Japan"): model suggests cities + nights from a geocoded candidate list; backend validates nights sum = trip length |
| 3. Candidate generation | provider | Per city × interest: `search_places` (dining by meal type, scenery → parks/viewpoints, shopping, romance → e.g. viewpoints/fine dining/bars); dedupe; drop rejected places; fetch details for top-N |
| 4. Rank | AI (`standard`) | Input: compact candidates with IDs + preferences. Output `RankedCandidates { items: [{ place_id, score 0–1, role: "activity"\|"lunch"\|"dinner"\|"evening", suggested_duration_minutes, reason }] }`. IDs validated; reasons ≤ 200 chars |
| 5. Schedule | deterministic (OR-Tools) | Travel-time matrix (routing provider), opening hours, meal windows, pace caps (relaxed ≤ 3 activities + 2 meals), walking cap, day start/end → `ScheduledDay[]` + `unscheduled[]` with reasons |
| 6. Cost estimate | deterministic | price level → per-category cost table per country (configurable), labeled `price_level_model` |
| 7. Summary | AI (`simple`/`standard`) | `PlanSummary { trip_summary, day_titles[{day_id, title}] }` from the *scheduled* result only |
| 8. Proposal | deterministic | `ai_proposals(kind=create_itinerary)` with full payload; job → `succeeded` |

Progress events per stage. Each AI stage has a deterministic fallback: rank failure → score by rating × preference
match; summary failure → template titles. The plan still succeeds with a visible "AI explanations unavailable" note.

#### Flow C — `chat` (Phase 10, streaming)
1. Persist user message.
2. Build context (trip header, itinerary window, profile, conversation summary + last K turns).
3. Loop: model call with tools → execute tool calls (parallel where independent, each with timeout) → feed results
   back. Limits: **max 6 model calls and 12 tool calls per turn, 45 s wall clock**; on limit, answer with what's
   known.
4. Stream assistant text + tool status events + `proposal.created` cards over SSE.
5. Persist assistant message with `parts` (place cards, proposal refs) and usage.

#### Flow D — `companion` (Phase 12)
Same loop as chat, with mandatory pre-fetched slices (location, local time, weather now/next 3 h, today's remaining
items, budget remaining, nearby open places within walking tolerance) so the common question ("I'm tired, it's
raining") is answered in ~1 model call. Ranking of nearby options is deterministic first (open now, distance,
indoor if raining, preference score, price vs remaining budget); the model explains and chooses among the top few.

### 2.7 Itinerary operations (proposal payload)

```python
Op = Annotated[
    AddItem | RemoveItem | MoveItem | UpdateTimes | ReplacePlace | SwapDays,
    Field(discriminator="op"),
]
```
Validated on proposal creation **and** re-validated on accept against the current trip state
(`base_trip_version`; non-conflicting ops still apply if the version moved but touched items are unchanged).

## 3. Memory

| Kind | Store | Phase |
|---|---|---|
| Working memory | Request context (ContextBuilder) | 9 |
| Conversation memory | `conversation_messages` + rolling `conversations.summary` | 10 |
| Preference memory | `travel_profiles`, `travel_preferences`, updated from `preference_signals` by a deterministic aggregator; AI-inferred preference changes go through `propose_preference_update` | 3 / 10 |
| Episodic travel memory | `memories`, `trip_timeline_events` | 17 |
| Semantic memory | `memory_embeddings` (pgvector), user-scoped retrieval | 18 |

## 4. Cost tracking & control

- `UsageTracker` wraps every provider call → `ai_requests` row (async, non-blocking) + tool calls → `ai_tool_calls`.
- Limits: per-user daily request cap (`AI_USER_DAILY_REQUEST_LIMIT`), per-user daily cost cap, global monthly
  budget (`AI_MONTHLY_BUDGET_USD`) — exceeded → `429 AI_QUOTA_EXCEEDED` with friendly UI.
- Cheap-first: `simple` tier for extraction/summaries; candidate lists trimmed before ranking; provider results
  cached; plan regeneration can target specific days.
- Internal endpoint/CLI (`make ai-usage`) for cost by purpose/model/day. No billing system.

## 5. Failure handling

| Failure | Handling |
|---|---|
| Provider 429/5xx/timeout | Retry ×2 with jittered backoff → fallback model → graceful error event; circuit breaker opens after repeated failures |
| Invalid structured output | One repair attempt (send validation errors back, same schema) → else deterministic fallback or `invalid_output` error |
| Unknown/foreign IDs in output | Drop offending items, log `invalid_reference`; if > 30% dropped, treat as invalid output |
| Tool timeout / provider outage | Structured tool error to model; model explains limitation; UI shows degraded chip |
| Refusal / off-topic request | Polite redirect within travel scope; logged as `refused` |
| Impossible request (e.g. 3 cities in 1 day, end < start, unknown destination) | Caught in validation; returned as `missing_fields`/`assumptions`/`warnings`, not "solved" by the model |
| Prompt injection via provider data (e.g. place names/reviews) | Provider text delivered as data in tool results; tools can't escalate privileges; write tools only create proposals |

## 6. LangGraph decision

Not used at MVP (ADR-005). Flows are linear pipelines plus one bounded tool loop — plain async Python is simpler to
test and debug. Re-evaluate at Phase 12–16 if we need durable, resumable multi-step state with human-in-the-loop
interrupts across requests (e.g. group conflict resolution with votes). The flow/tool/provider interfaces are
designed so a LangGraph graph could call them unchanged.

## 7. Testing AI

- **Unit:** prompt rendering is pure → snapshot tests; schema generation; ID validation; op validation.
- **Flow tests with `FakeAIProvider`:** happy path; malformed JSON; schema-valid but unknown IDs; tool timeout;
  provider 503 → fallback; loop-limit exhaustion; refusal.
- **Authorization:** for every tool, call with another user's trip/place-state → `NOT_FOUND` result; ensure no data
  from the other trip appears in the model's context.
- **Hallucination resistance:** assert that every operational field in outputs (hours, coordinates, durations,
  costs) equals provider/scheduler values, never model text.
- **Evals (manual/nightly, real model):** a small golden set of trip requests (incl. the MVP Japan prompt) with
  rubric checks (constraint satisfaction, pace, walking cap, budget sanity). Results stored as JSON for comparison
  across prompt versions.
