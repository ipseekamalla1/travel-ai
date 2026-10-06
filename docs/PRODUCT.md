# Product

## 1. Vision

AI Travel Universe is a personal travel operating system. Its goal is that the user feels:

> "I have an AI that understands how I travel."

The product covers the full lifecycle, and each stage feeds the next:

```
DREAM → DISCOVER → PLAN → EXPLORE → REMEMBER → LEARN → NEXT TRIP
  ▲                                                       │
  └───────────────────────────────────────────────────────┘
```

| Stage | What the user does | What the system learns / stores |
|---|---|---|
| Dream | Browse destinations, save "someday" places | Destination interests |
| Discover | Save / reject / rate places | Preference signals (rejections matter) |
| Plan | Describe a trip, edit itinerary, set budget | Pace, budget tolerance, edit patterns |
| Explore | Use today view, companion, log expenses | Actual pace, visited places, spending |
| Remember | Review timeline, favorites, story | Favorites, ratings |
| Learn | (implicit) profile is refined | Updated weighted preferences |
| Next trip | Better first-draft plans | — |

This is not "enter destination → get itinerary". The itinerary is one artifact of a long-lived model of the user.

## 2. Target users

**Primary (MVP): the independent leisure traveler.**
- Solo travelers and couples, 22–55, taking 1–4 trips per year of 3–21 days.
- Plan independently (no travel agent), mix of domestic and international.
- Today they juggle Google Maps saved lists, blogs, TikTok/Instagram saves, spreadsheets, and general chat assistants.
- Pain: planning takes 10+ hours; generic AI plans ignore real opening hours, distances and their taste; plans break
  on the ground (rain, fatigue, closures).

**Secondary (post-MVP):**
- Small groups / families (Phase 16): conflicting preferences, shared budgets.
- Frequent travelers who want a searchable travel history (Phases 17–18).

**Not targeted:** business travel management, travel agents, booking-first users (we are not an OTA).

## 3. Personas

| Persona | Snapshot | Key need |
|---|---|---|
| **Maya, the food-led couple traveler** | 31, plans a 7-day Japan trip with partner, $2,500 budget, hates rushing | "Plan something romantic around great food without exhausting us." |
| **Leo, the spontaneous solo explorer** | 26, books flights, figures out the rest on the ground | "What should I do *right now* near me?" |
| **Priya, the meticulous planner** | 40, color-codes spreadsheets | "Show me the real hours, distances and costs so I trust the plan." |

## 4. User journeys

### J1 — Onboarding (MVP)
1. Register (email + password).
2. Onboarding (≤ 2 minutes, skippable per step): travel style, pace, budget style, accommodation style, food
   interests, activity interests, walking tolerance, dietary constraints.
3. Land on **Universe** with a "Plan your first trip" call to action.

### J2 — Plan a trip by describing it (MVP, flagship)
1. `/trips/new` → free-text prompt ("I want a 7-day Japan trip…").
2. AI extracts structured requirements → shown as an **editable requirements card** (destinations, dates or
   duration, budget + currency, travelers, interests, pace, walking tolerance, must-haves/avoid). Missing or
   ambiguous fields are highlighted, not guessed (e.g. "Dates? You said 7 days — pick a start date").
3. User confirms → trip created (status `planning`).
4. User clicks **Generate itinerary** → background job: geocode → real place candidates → AI ranking with reasons →
   deterministic scheduling → itinerary **proposal**.
5. User reviews proposal (map + days + "Why this?" per item + estimated costs) → **Accept** (writes itinerary) or
   refine ("less walking on day 3").

### J3 — Plan a trip with the form (MVP)
Destination(s), dates, travelers, budget, currency, style tags → trip created → same generate flow or manual build.

### J4 — Edit itinerary (MVP)
Drag to reorder, move to another day, change times/duration, add place from search/saved/trip places, remove, notes.
Map stays synchronized; travel times between items recompute (provider-backed, cached).

### J5 — Discover and save (MVP)
Search places near a destination by category/interest → save / reject / rate / add to trip / add to a day.
Rejections are recorded as preference signals.

### J6 — Budget (MVP)
Set total budget and currency, see estimated cost from itinerary items, per-category and per-day breakdowns, log
actual expenses, see remaining budget. All math is server-side and deterministic.

### J7 — Trip-aware chat (MVP)
Ask "Is day 3 too packed?", "Find a romantic dinner near our hotel on day 2", "What will the weather be in Kyoto?".
AI uses tools; any change is a proposal card with **Accept / Cancel**.

### J8 — Live companion (Phase 12, north star)
"I'm in Kyoto. I'm tired. It's raining. What should I do?" → location + time + weather + itinerary + preferences +
budget + nearby places → ranked options → optional itinerary adjustment proposal.

### J9 — Remember (Phase 17+)
After the trip: timeline, visited places, favorites, photos, spending summary, AI story generated only from recorded
data. Later: "Where did I eat sushi in Japan?"

## 5. MVP definition

A real user can:

| # | Capability | Phase |
|---|---|---|
| 1 | Register / log in / log out | 2 |
| 2 | Complete travel profile | 3 |
| 3 | Create trip (form) | 4 |
| 4 | Describe trip naturally → structured requirements | 9 |
| 5 | Get AI-assisted place recommendations with reasons | 9 |
| 6 | Generate itinerary (real places, deterministic schedule) | 9 |
| 7 | View itinerary on map | 6–7 |
| 8 | Modify itinerary | 7 |
| 9 | Save places | 5 |
| 10 | Manage basic budget | 8 |
| 11 | Chat with AI about the trip (tool-using, proposals) | 10 |

Plus a thin slice of Phase 11 (forecast shown on trip days) because the MVP test expects weather-aware planning to
be at least visible.

## 6. MVP acceptance test

Input:

> "I want a 7-day Japan trip. I want amazing food. I want beautiful scenery. I want shopping. I want some romantic
> experiences. I don't want to rush. My budget is $2,500. I don't want to walk too much."

The system must:

| Requirement | How it is satisfied | Verifiable by |
|---|---|---|
| Structure the requirements | `TripRequirements` structured output: duration 7, country JP, interests [food, scenery, shopping, romance], pace relaxed, budget 2500 USD, walking low; dates flagged as missing | Requirements card |
| Suggest destinations | Destination suggestion step returns e.g. Tokyo + Kyoto split with rationale; geocoded via provider | Card with geocoded cities |
| Find real places | Places come only from `PlaceProvider`; every item has a provider ID | No item without `place_id` (except free time / transit) |
| Sensible itinerary | Relaxed pace ⇒ ≤ 4 activities/day, meals at meal times, clustered by area, opening hours respected | Scheduler constraint tests |
| Approximate costs | Price level → category cost model; budget engine totals; clearly labeled "estimate" | Budget page |
| Map | All items plotted; selected day route shown | Map view |
| Editable | Reorder, move, remove, add | Itinerary UI |
| Explain | `reason` per item references user preferences | "Why this?" |
| Questions | Chat with trip context and tools | Chat |
| Preserve preferences | Extracted interests merged into travel preferences (with user consent) | Profile page |

## 7. Product principles

1. **Real data over fluent text.** Operational facts come from providers; the AI interprets.
2. **Proposals, not surprises.** AI never changes user data without explicit acceptance (unless the user enables
   auto-adaptation in a later phase).
3. **Learn from behavior, not vanity scores.** No fake "personality score"; preferences must change recommendations.
4. **Calm, cinematic, personal.** Not an admin panel. Map and imagery are primary visual elements.
5. **Mobile during, desktop before.** Every screen works on mobile; desktop gets richer planning layouts.
6. **Graceful degradation.** A failed weather call shows a chip, not a broken page.

## 8. Success metrics (instrumented from Phase 9)

- Time from first prompt to accepted itinerary (target: < 5 minutes).
- Itinerary acceptance rate; edits per accepted itinerary (lower over time per user = learning works).
- % of AI items with valid provider place IDs (target: 100% by construction).
- AI cost per generated itinerary and per chat turn.
- D7/D30 retention; trips per user.

## 9. Future roadmap (beyond MVP)

Weather intelligence → live companion → voice → vision → packing → group travel → memories → semantic memory →
polish → production. See [ROADMAP.md](ROADMAP.md).
