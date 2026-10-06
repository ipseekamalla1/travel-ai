# UX

## 1. Design direction

**Feel:** premium, cinematic, calm, immersive, intelligent, personal, visual. **Not:** ERP, admin panel, generic
SaaS dashboard, spreadsheet.

| Element | Direction |
|---|---|
| Layout | Generous whitespace, few elements per view, content-first; one primary action per screen |
| Imagery | Large destination photography (licensed / provider photos with attribution) in hero areas; never stock filler in dense views |
| Map | A primary visual surface, not a widget — full-bleed on mobile trip views, half-screen on desktop planning |
| Typography | Expressive display serif for headings (e.g. Fraunces / Instrument Serif) + neutral sans for UI (e.g. Inter / Geist); tabular numerals for money and times |
| Color | Warm neutral base, one deep accent (dusk blue), semantic category colors for map markers (food, culture, nature, shopping, nightlife); full dark mode |
| Motion | Subtle, purposeful: shared-element transitions (card → detail), map fly-to, staggered list reveal; respects `prefers-reduced-motion` |
| AI presence | Inline, contextual: "Why this?" chips, proposal cards, a calm planner prompt — not a chatbot pasted onto every page |
| Copy | Warm and specific ("A slow morning in Yanaka before lunch") rather than system-speak |

### Design tokens (`apps/web/src/styles/tokens.css`)
Colors (`--surface`, `--surface-raised`, `--ink`, `--ink-muted`, `--accent`, `--accent-ink`, `--danger`,
`--warning`, `--success`, `--cat-food` …), radius scale (`--radius-sm/md/lg/xl`, cards use `xl`), spacing
(4-pt base), shadow scale (soft, layered), z-index scale, motion durations/easings. Tailwind theme maps to these
variables; shadcn/ui components consume them.

### Design system components (built once, reused)
Button, IconButton, Input, Textarea, Select, Combobox, DatePicker/DateRange, Dialog, Drawer (mobile bottom sheet),
Sheet (desktop side panel), DropdownMenu, Tabs/SegmentedControl, Card, Badge/Chip, Toast, Tooltip, Skeleton,
Spinner, EmptyState, ErrorState, Avatar, ProgressSteps, **MapControls**, **Timeline**, **ItineraryItem**,
**PlaceCard**, **AIMessage**, **AIActionCard (proposal)**, **WhyThis**, **BudgetMeter**, **MoneyText**,
**WeatherChip**.

## 2. Navigation

### Mobile (< 768 px) — primary target
- Bottom tab bar (thumb zone, 56 px + safe area): **Universe · Trips · Discover · Companion · Profile**.
- Inside a trip: top segmented control **Overview · Plan · Map · Budget**; floating AI button (bottom-right, above
  tab bar) opens the trip-aware assistant as a bottom sheet.
- Detail views (place, item) open as bottom sheets with snap points (peek / half / full) so the map stays visible.
- Back gestures/buttons always return to the previous context (sheet → list → trip).

### Desktop (≥ 1024 px)
- Collapsible left rail with the same five destinations + Settings.
- Trip workspace: **itinerary column (≈ 420 px) | map (fluid)**, AI panel slides over from the right (380 px).
- Keyboard shortcuts: `/` search, `⌘K` command palette (later), `[`/`]` previous/next day, `A` open AI.

Tablet (768–1023 px) uses the mobile structure with wider sheets.

## 3. Screen inventory

Each screen lists purpose, key content, states, and mobile/desktop notes. All API-backed regions define
**loading / success / empty / error (+ retry)**; partial failures degrade locally.

### Marketing
| Route | Purpose | Notes |
|---|---|---|
| `/` | Story of the product; CTA "Start planning" | Cinematic hero (map flythrough or imagery), lifecycle strip Dream→Next trip, sample itinerary visual (illustrative, labeled as example) |
| `/about` | Mission, principles (real data, proposals not surprises) | Static |
| `/how-it-works` | Describe → plan → explore → remember | Static, illustrated steps |

### Auth
| Route | Content | States |
|---|---|---|
| `/register` | Email, display name, password (show/hide, strength hint) | Field errors inline; `EMAIL_TAKEN` on email field; submit spinner; network error toast with retry |
| `/login` | Email, password, `next` param | Generic invalid-credentials message; rate-limited message with wait time |

Signed-in users visiting these are redirected to `/universe`.

### Onboarding `/onboarding`
5 short steps with progress: travel style (multi-select visual tiles) → pace → budget style → food & dietary →
walking tolerance + interests. Every step skippable; "Finish later" saves partial. Ends on Universe with
personalized greeting. Empty/error: save failure keeps local state and offers retry.

### Universe `/universe` — "Your world of travel"
Not a dashboard grid. A vertical, story-like feed:
1. **Hero:** next upcoming trip (cover image, countdown, "Continue planning" or "Today in Kyoto" when active).
2. **AI suggestion:** one contextual card (e.g. "Day 3 has no dinner yet — want ideas?") → opens proposal flow.
3. **Dream destinations / saved places** carousel.
4. **Your travel style:** plain-language summary of real stored preferences ("Food-first, relaxed pace, low
   walking") with "Refine" link — no fake scores.
5. **Recent memories** (Phase 17).

Empty (new user): single large prompt "Where do you want to go?" → `/trips/new`.

### Trips `/trips`
Upcoming / Planning / Past groups as image cards (cover, name, dates, travelers). Primary action "New trip".
Empty: illustrated empty state with the natural-language prompt inline.

### New trip `/trips/new`
- Default tab **Describe it**: large textarea with example chips ("7 days in Japan, food & scenery…"); submit →
  **Requirements card**: each extracted field editable; assumptions listed ("Assumed USD"); missing fields
  highlighted (dates); destination candidates as selectable chips with map thumbnail. Confirm → trip created →
  trip overview with "Generate itinerary" primary action.
- Tab **Fill in details**: destination combobox (geocoded), date range or duration, travelers stepper, budget +
  currency, style chips.
- States: extraction loading ("Understanding your trip…", ≤ 10 s, cancellable); AI failure → keeps text, offers
  "Try again" or switch to form with whatever was parsed.

### Trip overview `/trips/[tripId]`
Desktop: hero band (name, dates, travelers, destinations) → two columns: left = summary, itinerary preview by day,
saved/candidate places; right = map preview, budget meter, weather strip. AI panel available.
Mobile (before trip): hero, "Generate / continue plan" CTA, day carousel, map preview, budget meter.
Mobile (during trip, `status=active` or today within dates): **Today first** — next activity card with leg time,
then remaining items, map, weather now, companion shortcut.
Itinerary generation in progress: stage-by-stage progress ("Finding places in Kyoto…", "Building your days…"),
leave-safe (job continues; banner on return). Result shows as a **proposal preview** with Accept / Refine / Discard.

### Itinerary `/trips/[tripId]/itinerary`
Day tabs (mobile) / scrollable day columns (desktop) + unscheduled bucket. ItineraryItem shows time, title, category
icon, duration, leg to next (mode + minutes), cost estimate, warnings (closed, tight transfer), "Why this?".
Interactions: drag handle reorder (keyboard accessible: pick up with Space, arrows, drop), move to day (menu),
edit sheet (times, duration, notes, transport), lock, remove (undo toast), add (search / saved / trip places).
Map is synchronized (desktop side by side; mobile via "Show on map").
Conflict (412): toast "This trip changed elsewhere — refreshed" and refetch.

### Map `/trips/[tripId]/map`
Full-bleed map; day filter chips; category filter; markers numbered by order for the selected day, clustered when
zoomed out; route polyline for the day; user location (permission requested only on tap of "locate").
Bottom sheet lists items of the selected day; tapping a marker selects the item and expands its card.
Empty (no items): destination centered, "Add places" CTA. Tile failure: inline banner, list still usable.

### Trip places `/trips/[tripId]/places`
Candidate/shortlisted places with filters; add to day; reject (feeds preferences).

### Budget `/trips/[tripId]/budget`
BudgetMeter (planned vs spent vs total), category breakdown (bars, not pie), per-day view, planned items list,
expenses list with quick-add (amount, currency, category, note). Every estimate shows its basis on tap
("Estimated from price level ££"). Empty: "Set a budget" CTA. FX unavailable: show original currency with notice.

### Discover `/discover`
Destination search + place search with category chips (Restaurants, Cafés, Attractions, Museums, Parks, Shopping,
Experiences). Results as large PlaceCards with save / reject (swipe on mobile, buttons always present for
accessibility) / rate / add to trip. "Because you like…" explanations only when backed by stored preferences.

### Place detail `/places/[placeId]`
Photos (provider, attributed), name, category, rating, price level, hours (today highlighted, "Open now"), address,
mini-map, actions (save, reject, add to trip/day, directions link). Data freshness note for cached details.

### Companion `/companion`
Trip-aware conversation (trip picker if multiple). Messages render rich parts: place cards, mini-maps, proposal cards
(Accept / Cancel), tool activity lines ("Checking weather in Kyoto…"). Input with quick actions ("What's next?",
"Find food nearby", "Is tomorrow too packed?"). Phase 12 adds location chip + voice button. AI failure: message with
retry; never a blank bubble.

### Profile `/profile`
Travel profile editor (same controls as onboarding), preferences list with strength sliders and source labels
("From onboarding", "Learned from your saves" — inferred items can be removed), saved places.

### Settings `/settings`
Account (name, email), units, home currency, sessions ("Sign out everywhere"), data (delete conversations, delete
account — Phase 20), AI preferences (later: auto-adapt itinerary toggle).

## 4. AI interaction patterns

| Pattern | Where | Behavior |
|---|---|---|
| Planner prompt | New trip, Universe empty state | Natural language → editable requirements card |
| Recommendation card | Discover, chat, overview | Place card + "Why this?" grounded in preferences + provider facts |
| Proposal card | Anywhere AI wants to change data | Plain-language summary ("Move Garden Visit to May 12?"), visual diff (before → after), **Accept** / **Cancel**; expires; shows conflict if trip changed |
| Contextual nudge | Overview, itinerary | Small, dismissible ("Rain at 3 PM on Day 2 — swap garden and museum?") |
| Quick actions | Companion input | One-tap prompts tuned to context |
| Progress narration | Long jobs | Stage names, not fake percentages |

## 5. Global states

- **Loading:** skeletons matching final layout (no spinners for page loads); spinners only inside buttons.
- **Empty:** illustration-light, one sentence, one primary action.
- **Error:** what happened in human terms + Retry + (dev) request ID; component-level, so the rest of the page works.
- **Offline (mobile):** banner; cached itinerary readable (TanStack Query persisted cache for active trip — Phase 12).
- **Permissions:** location/camera/mic requested in context with a pre-prompt explaining why.

## 6. Accessibility

Semantic landmarks and headings; all interactive elements reachable and operable by keyboard; visible focus rings
(token `--focus-ring`); Radix-based dialogs/sheets with focus trap and `Esc`; labels for all inputs; error text
linked via `aria-describedby`; drag-and-drop has keyboard and menu alternatives; map has a list equivalent (map is
never the only way to reach information); contrast ≥ 4.5:1 text / 3:1 UI; `prefers-reduced-motion` honored; live
regions for streaming AI text (polite) and toasts. Automated: `eslint-plugin-jsx-a11y` + axe in Playwright.
