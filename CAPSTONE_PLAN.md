# Trip Planner AI Agent Capstone — Research, Architecture, and Implementation Plan

**Status:** Planning and research only. No application code in this document’s scope.  
**Date:** 26 August 2026  
**Goal:** Ship a unique, production-grade trip planner that fully covers the course rubric, is clearly stronger than the sample solution, and is deployable as a portfolio piece.

**Reference sample (do not clone):** [Codecademy-Curriculum/AI-Engineer-Career-Path-Capstone-Trip-Planner](https://github.com/Codecademy-Curriculum/AI-Engineer-Career-Path-Capstone-Trip-Planner)

---

## 1. How to use this document

This file is the single source of truth for the capstone until implementation starts. It contains:

1. The full course brief, objectives, setup, and API guidance you provided.
2. A module-by-module rubric checklist (what graders / reviewers will look for).
3. Research notes on the sample solution: what to keep, what is weak, what would look copied.
4. The recommended architecture and “top candidate” strategy.
5. A sequenced implementation plan (build order, acceptance criteria, risks).
6. Deployment, demo, and README plan.

When implementation begins, treat each numbered phase in Section 10 as a mergeable increment with its own acceptance tests.

---

## 2. Course brief (source of requirements)

### 2.1 Why this project exists

Creating a capstone that demonstrates real-world AI engineering skills is essential for a portfolio. This project goes beyond simple chatbots to showcase production-grade AI applications with:

- External data integration
- Agentic workflows
- Persistent state management

Three core components:

1. **Agent architecture with tool calling**
   - Implement OpenAI’s Responses API with function calling
   - Design and integrate custom tools for POI search and travel guide retrieval
   - Handle multi-step reasoning and tool orchestration
   - Debug and trace agent execution paths

2. **Real-time data integration**
   - Connect to OpenStreetMap’s Nominatim API for geocoding
   - Query Overpass API for live Points of Interest
   - Implement optional Wikivoyage RAG (Retrieval-Augmented Generation)
   - Handle API rate limiting, retries, and error cases

3. **User experience and feedback loops**
   - Interactive Streamlit interface with session state management
   - Interactive maps with PyDeck for itinerary visualization
   - User feedback collection to improve future recommendations
   - Itinerary persistence and refinement capabilities

Throughout: work with real APIs, handle authentication and rate limiting, validate AI-generated outputs against available data, and create a polished UI — skills essential for production AI engineering.

### 2.2 Project objectives (must all be visible in the final app)

- Build a production-ready AI application using Streamlit
- Implement agentic AI workflows with OpenAI’s function calling
- Integrate multiple external APIs (OpenStreetMap, Wikivoyage)
- Create interactive data visualizations with PyDeck
- Design feedback loops to improve model performance
- Handle state management and data persistence
- Validate and constrain AI outputs for reliability

### 2.3 Prerequisites assumed

- Python fundamentals
- API integration: REST APIs, authentication, error handling
- Data science libraries: NumPy, Pandas, scikit-learn
- AI/ML foundations: prompt engineering, RAG
- OpenAI API: chat completions, function calling, Responses API
- Streamlit: UI components, session state, callbacks

### 2.4 Off-platform setup (course instructions)

**Python:** 3.8+ (plan to use **3.11** for closer match to the sample and fewer Streamlit/openai issues).

**Virtual environment:**

```bash
python -m venv trip-planner-env
source trip-planner-env/bin/activate  # Windows: trip-planner-env\Scripts\activate
```

**Packages named by the course:**

```bash
pip install streamlit openai pydeck requests scikit-learn numpy pandas
```

**Suggested starter structure (course):**

```text
trip-planner/
├── app.py
├── data/
│   ├── app_state.json
│   └── feedback.jsonl
└── README.md
```

**Run:**

```bash
streamlit run app.py
```

The course starter is a *minimum*. A top candidate should keep this *runtime* shape (Streamlit entrypoint + local `data/`) but use a modular package layout underneath (see Section 6).

### 2.5 API keys and access (course guidance)

#### OpenAI API key (required)

- Purpose: powers the AI agent that generates itineraries using function calling
- Obtain: [platform.openai.com](https://platform.openai.com) → API Keys → Create new secret key (`sk-…`)
- Default model in the brief: **gpt-4.1-mini**
  - Rough cost cited by the course: ~$0.15 / 1M input tokens, ~$0.60 / 1M output tokens
  - Typical itinerary: **$0.01–$0.05**
- Set usage limits in the OpenAI account
- **Never hardcode the key.** Use session-state BYO-key, env vars, or Streamlit secrets

**Key management options from the course:**

1. **User input (recommended for deployment)** — `st.text_input(..., type="password")` + “Remember for this session”
2. **Environment variables (local development)** — `OPENAI_API_KEY`
3. **Streamlit secrets (cloud)** — `.streamlit/secrets.toml` (never commit)

**Cost estimates from the course:**

- Development: $1–5
- Typical generation: $0.01–0.05
- Moderate monthly: $5–20

#### OpenStreetMap APIs (free, no key)

- **Nominatim** — geocoding
- **Overpass** — POI data
- Must send a descriptive User-Agent with contact email
- Respect rate limits (Nominatim: **1 request per second**, application-wide)
- Caching + retry logic required

Example:

```python
user_agent = "trip-planner-capstone/1.0 (your-email@example.com)"
headers = {"User-Agent": user_agent}
```

#### Wikivoyage API (optional, free, no key)

- Wikimedia API, no key
- Proper User-Agent required
- Can be disabled if 403s occur
- Cache responses; fail gracefully

**Public-API etiquette (course + OSM policy research):**

- Nominatim: valid identifying User-Agent (library defaults like `python-requests/x.x` are forbidden); cache results; 1 req/s hard ceiling for the *entire app*, not per user; display OSM attribution ([Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/))
- Overpass: identify the app; avoid hammering; backoff on 429; safety margin roughly ~10k requests/day and ~1 GB/day on the public instance
- Wikivoyage: User-Agent with contact; 403 is expected if headers are weak — disable RAG and continue

**Security checklist (course):**

- Never commit API keys
- Add `.streamlit/secrets.toml` to `.gitignore`
- Use env vars or user input
- Usage limits and monitoring
- Rotate keys if exposed

### 2.6 Course reminder about uniqueness

> Remember: your project doesn’t have to look anything like the sample. It should be unique to your skills and vision.

This is the most important portfolio instruction. Meeting the rubric *and* looking like a fork of the sample is a mid-tier outcome. Meeting the rubric with a cleaner architecture, stronger guardrails, and one memorable product feature is a top-candidate outcome.

---

## 3. Course modules (the actual build rubric)

These are the graded / reviewed work items. Every one must be demonstrable in the finished app.

### Module A — Set up project structure and API integration

- Install: streamlit, openai, pydeck, requests, scikit-learn (plus numpy, pandas)
- Secure OpenAI key entry via session state
- Test connections to Nominatim and Overpass
- Proper User-Agent headers
- `data/` directory for feedback and app state
- Option to clear the key after use

**Hint from course:** `st.text_input(type="password")`; store in `st.session_state`; include identifying contact in User-Agent.

### Module B — Build POI search tool

- Geocode city names with Nominatim
- Overpass queries filtered by category
- Map user interests (`outdoors`, `food`, `history`, …) to OSM tags
- `@st.cache_data` to reduce API calls
- Return: `poi_id`, `name`, `category`, `lat`, `lon`, `url`
- Retry logic and error handling

**Interest mapping pattern from the course:**

```python
INTEREST_TO_TAGS = {
    "museums": [("tourism", "museum|gallery")],
    "food": [("amenity", "restaurant|cafe|fast_food")],
    "outdoors": [("leisure", "park|nature_reserve"), ("natural", "peak|beach")],
}
```

### Module C — Implement Wikivoyage RAG (optional but expected for a strong submission)

- Query Wikivoyage for destination articles
- Clean HTML → plain text
- Chunk 800–1000 characters, preserve paragraph boundaries, avoid mid-sentence splits
- TF-IDF vectorizer + cosine similarity (scikit-learn)
- Top-k chunks with `chunk_id`, `source`, `text`, `score`
- Cache vectorized indices
- On 403 / empty: continue with `sources=[]`

### Module D — Design agent system with function calling

- Strict function schemas for `search_pois` and `retrieve_guides`
- Agent loop: call model → execute tools → return results → repeat
- Parse tool arguments and route to Python functions
- `tool_state` accumulating POIs, chunks, city metadata
- Max step limits
- Execution tracing
- Validate final itinerary only references POIs returned by tools
- `strict: True`; `required` includes every property; `additionalProperties: false`

```python
def validate_itinerary_poi_ids(itin, allowed_pois):
    ...
```

### Module E — Streamlit UI with itinerary display

- Inputs: destination, trip length, pace, interests, constraints
- Generate button triggering the agent
- Status indicator for progress and tool calls
- Day / block (Morning / Afternoon / Evening) layout
- POI name, category, explanation (`why`)
- Source citations if RAG was used
- Download itinerary JSON
- Session state persistence across refreshes

### Module F — Interactive map visualization

- Lat/lon from selected POIs
- PyDeck `ScatterplotLayer` (radius in meters + pixel clamps)
- `PathLayer` connecting POIs in temporal order
- Day filter: All / Day 1 / Day 2 …
- Zoom from POI spread
- Tooltips: name, category, day/block
- Light and dark map styles
- Changing the filter must not clear the itinerary (render from session state, outside the button handler)

### Module G — Itinerary refinement

- Natural-language refinement of the full itinerary
- Single-day regeneration; other days must remain unchanged
- Re-validate POI IDs
- Persist updates
- Multiple refinement rounds
- Before/after comparison when helpful

### Module H — Feedback loop

- Upvote / downvote per itinerary POI
- JSONL events with timestamps
- Boost: **+0.25 upvote**, **−0.35 downvote**
- Apply boosts in `search_pois` ranking
- Scope by city (`city_key`)
- Optional: feedback statistics / trends

```python
feedback_event = {
    "ts": time.time(),
    "city_key": "santa fe, nm",
    "poi_id": "osm_way_12345",
    "vote": "up",  # or "down"
}
```

### Module I — Error handling and edge cases

- Geocoding returns no results
- Rate limits with exponential backoff
- Validate user inputs before the agent
- No POIs matching criteria
- JSON parse errors with expandable raw output
- Timeouts on long agent calls
- Cities with sparse POI data
- Malformed API responses must not crash the app

### Module J — Performance and UX

- Execution trace with steps and timings
- Fast mode (fewer tool calls)
- Cache geocoding and RAG indices
- Spinners and status indicators
- Sensible map dot sizes
- Instructions and tooltips
- Sidebar config: model, max steps, etc.

Fast-mode pattern from the course:

```text
if fast_mode:
    instructions = "Call search_pois ONCE with broad criteria (limit=40)"
    max_steps = 5
else:
    instructions = "Call search_pois 2-3 times with different queries (limit=30)"
```

### Module K — Polish and deploy

- Comprehensive README: setup, features, screenshots, architecture diagram
- Example outputs and use cases
- API requirements and rate limits documented
- Deploy (Streamlit Community Cloud, Hugging Face Spaces, or similar)
- BYO-key or secrets; never hardcoded keys
- Session isolation between users
- Optional: demo video, light usage notes

### Module L — Enhance and extend (optional; pick one, not all)

Course ideas:

- User authentication / saved trip library
- Database of historical searches
- Image generation for destination previews
- Side-by-side trip comparison
- Real-time weather
- Budget tracking
- Shareable PDF export

**Plan decision:** implement **one** signature enhancement (see Section 7), not a pile of extras.

---

## 4. Research: sample solution (what it actually is)

The public sample is a **single ~1,240-line `app.py`** plus `requirements.txt` and README. It is a valid complete solution. It is also the thing every other student can download.

### 4.1 What the sample already does well (keep the *behaviors*)

| Area | Sample behavior to preserve |
|---|---|
| Agent | OpenAI `client.responses.create` with `tools=TOOLS`, `store=False`, loop until no more function calls |
| Tools | `search_pois` + `retrieve_guides`, both `strict: True` |
| OSM | Nominatim geocode (`sleep(1.0)`), Overpass POST, OSM tag mapping, `osm_{type}_{id}` IDs |
| RAG | Wikivoyage search + parse HTML, TF-IDF, cosine similarity, degrade on 403 |
| Guardrails | `validate_itinerary_poi_ids`; day-regen uses `other_days_unchanged` |
| UX | Tabs: Plan / Refine / Feedback; itinerary rendered **outside** the generate button; autosave `data/app_state.json` |
| Map | Scatterplot radius in meters + `radius_min_pixels` / `radius_max_pixels`; PathLayer; light/dark Carto styles |
| Feedback | JSONL, +0.25 / −0.35, city-scoped boosts |
| Speed | Fast mode, max_steps slider, trace expander |
| Keys | BYO key in session state; optional clear-after-use |

Default model: `gpt-4.1-mini`. Fast-mode default max steps: 5.

### 4.2 Sample weaknesses (this is where a top candidate wins)

1. **Monolith.** Everything in one file. Hard to test, review, or extend. Looks like a tutorial dump.
2. **Fragile final JSON.** `extract_json` finds the first `{` and last `}` and `json.loads`. No schema for the *itinerary itself*. Hallucinated fields, missing days, extra commentary all become parse-time surprises.
3. **No structured output for the itinerary.** Tools are strict; the final answer is free text that happens to contain JSON. Production pattern: **function calling for tools + JSON schema / Pydantic for the itinerary.**
4. **Naive POI ranking.** Sort by (name substring match, feedback boost, name). No popularity, no distance-to-center, no “already used today”, no opening-hours awareness.
5. **No geographic coherence.** The model can put a morning POI on one side of the city and afternoon on the opposite side. Paths look chaotic.
6. **PathLayer is incomplete.** Sample connects only the *first* item of each block, not the full morning → afternoon → evening sequence of all items.
7. **Duplicates allowed.** Same museum can appear on Day 1 morning and Day 3 afternoon.
8. **No connection tester.** Module A explicitly asks to test Nominatim and Overpass. Sample just uses them inside the agent.
9. **No before/after on refine.** Course asks for it “when helpful.” Sample overwrites immediately.
10. **Feedback tab has no stats.** Course marks stats as optional; showing a small city-level chart is easy differentiation.
11. **Token-bucket missing.** `time.sleep(1)` on geocode is polite for a single user, but not a real 1 req/s limiter under Streamlit reruns / concurrent sessions.
12. **Single Overpass host.** `overpass-api.de` is often slow or 429. Fallbacks (`overpass.kumi.systems`, `lz4.overpass-api.de`) are a reliability win.
13. **RAG HTML cleaning is brittle.** Regex HTML strip; paragraph splitting often collapses because tags become spaces, so chunks become one giant blob.
14. **No tests.** Zero unit tests for validation, ranking, or JSON extraction.
15. **UI copy is tutorial-ish.** Title is “Trip Planner Capstone (Agent + POIs + Optional RAG + Feedback)” — reads as homework, not a product.
16. **No OSM attribution** in the UI despite policy requiring it.

### 4.3 What *not* to copy visually or structurally

- The exact three-tab homework layout titled like a rubric
- Santa Fe hardcoded as the only example
- The exact prompt dump with “Hard rules: 1) 2) 3)”
- A single `app.py` with banner comments like `# ============================================================`

Borrow *algorithms and policies* (strict tools, POI ID validation, autosave outside the button). Rewrite *product, architecture, and prompts*.

---

## 5. Evaluation: what “top candidate” actually means here

This workspace is named for an **FDE-style** (forward-deployed / field) AI engineering capstone. Reviewers in that context typically score:

1. **Does it work on messy real APIs?** Timeouts, 403, 429, empty cities, bad JSON.
2. **Are model outputs constrained?** Tools + validation + (ideally) structured itinerary schema.
3. **Can you explain the system?** Trace, architecture diagram, README that a hiring manager can skim in 3 minutes.
4. **Is it a product, not a notebook?** Persistence, maps, feedback, deploy URL.
5. **Did you make a tasteful unique choice?** One extra capability that is *useful*, not a zoo of unfinished extras.

### 5.1 Must-have (rubric complete)

Everything in Modules A–K.

### 5.2 Should-have (separates you from the sample)

- Modular package (not one file)
- Pydantic (or JSON schema) itinerary model + structured final output
- Connection / health panel for OSM + optional Wikivoyage
- Duplicate-POI and “other days unchanged” validators
- Full temporal path on the map (all stops in order, color by day)
- Feedback stats
- OSM attribution
- Overpass fallbacks + Nominatim rate limiter
- Before/after refinement view
- Tests for validators and ranking
- Polished product naming and README with architecture diagram + screenshots

### 5.3 Signature enhancement (pick one; recommended below)

See Section 7. Do **not** implement auth + weather + PDF + image gen in the first ship. Unfinished extras hurt more than they help.

---

## 6. Recommended solution architecture

### 6.1 Product framing

**Working name:** *Waypoint* (or *Atlas Itinerary*) — a BYO-key trip planner that:

1. Geocodes a city
2. Pulls live OSM POIs matched to interests
3. Optionally grounds the plan in Wikivoyage
4. Lets an agent compose a day-by-day itinerary **only from those POIs**
5. Shows the plan on a map
6. Lets you refine in English or regenerate one day
7. Learns from up/down votes for that city

Keep Streamlit-only (no FastAPI). That matches the course and keeps deployment simple.

### 6.2 Runtime data flow

```text
User (Streamlit)
    │  destination, days, pace, interests, constraints
    ▼
Input validation
    │
    ▼
Agent loop  (OpenAI Responses API)
    │  tools: search_pois, retrieve_guides  [strict schemas]
    │  optional later: estimate_travel     [signature enhancement]
    │
    ├─► Nominatim (geocode, cached, 1 req/s)
    ├─► Overpass  (POIs, cached, retries + fallback hosts)
    └─► Wikivoyage (optional RAG, TF-IDF, degrade to [])
            │
            ▼
    tool_state { pois[], chunks[], center, city_key }
            │
            ▼
    Structured itinerary (JSON schema / Pydantic)
            │
            ▼
    Validators
      - poi_ids ⊆ allowed
      - no duplicate poi_id across trip (warn or reject)
      - day count matches request
      - other days unchanged (regen path)
            │
            ▼
    Session state + data/app_state.json
            │
            ├─► Itinerary UI (day × morning/afternoon/evening)
            ├─► PyDeck map (points + full path, day filter)
            ├─► JSON download
            └─► Feedback JSONL → boosts on next search_pois
```

### 6.3 Proposed repo layout (implementation later)

```text
capstone-project-fde-role/
├── app.py                          # Streamlit entry only: layout, widgets, wiring
├── requirements.txt
├── README.md                       # portfolio README (written in polish phase)
├── CAPSTONE_PLAN.md                # this file
├── .gitignore                      # venv, data/*.json*, .streamlit/secrets.toml, __pycache__
├── .streamlit/
│   └── config.toml                 # theme; no secrets committed
├── src/waypoint/
│   ├── __init__.py
│   ├── config.py                   # model default, URLs, boost weights, TTLs
│   ├── schemas.py                  # Pydantic: Itinerary, Day, BlockItem, POI, GuideChunk
│   ├── persistence.py              # app_state.json load/save/clear
│   ├── feedback.py                 # jsonl append, boost map, stats
│   ├── rate_limit.py               # Nominatim 1 rps token bucket
│   ├── osm/
│   │   ├── geocode.py              # Nominatim
│   │   ├── overpass.py             # query builder, retries, fallbacks
│   │   └── tags.py                 # INTEREST_TO_TAGS
│   ├── rag/
│   │   ├── wikivoyage.py           # search + parse
│   │   └── retrieve.py             # chunk, TF-IDF, cosine
│   ├── agent/
│   │   ├── tools.py                # search_pois, retrieve_guides (+ optional travel)
│   │   ├── schemas_openai.py       # strict tool JSON schemas
│   │   ├── loop.py                 # responses.create agent loop + trace
│   │   └── prompts.py              # plan / refine / regen / fast-mode rules
│   ├── validate.py                 # poi ids, duplicates, other_days_unchanged
│   └── ranking.py                  # base score + feedback boost + distance
├── ui/
│   ├── sidebar.py
│   ├── itinerary.py
│   ├── map.py
│   ├── trace.py
│   └── health.py                   # API connection tester
├── tests/
│   ├── test_validate.py
│   ├── test_ranking.py
│   └── test_schemas.py
└── data/                           # created at runtime; gitkeep only
    └── .gitkeep
```

`app.py` should stay under ~200–300 lines of UI wiring. Business logic lives in `src/waypoint`. That is the single biggest “this person engineers software” signal versus the sample.

### 6.4 Agent design (aligned with current OpenAI guidance)

Use **Responses API** (as the course requires), not Chat Completions, for the agent loop.

**Tools (strict mode):**

Per [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling):

- `strict: true`
- every property listed in `required`
- `additionalProperties: false` on every object
- optional values as `"type": ["string", "null"]` if needed

**Recommended tools:**

| Tool | Required by course? | Role |
|---|---|---|
| `search_pois(city, interests, radius_km, limit, query)` | Yes | Live OSM POIs |
| `retrieve_guides(city, query, k)` | Yes (optional RAG) | Wikivoyage chunks |
| `estimate_travel(from_poi_id, to_poi_id, mode)` | No — signature enhancement | OSRM duration/distance so days are walkable |

**Final itinerary:** after the last tool round, either:

- Prefer: `client.responses.create(..., text={"format": {"type": "json_schema", ...}})` / equivalent structured output so the itinerary matches `Itinerary` exactly; or
- Fallback: prompt for JSON + Pydantic `model_validate` + repair pass (one extra model call: “fix this JSON to match the schema”).

Do **not** rely only on `extract_json` first-brace slicing.

**`tool_state` (required by course):**

```python
tool_state = {
    "pois": {},       # poi_id -> {name, category, lat, lon, url, ...}
    "chunks": {},     # chunk_id -> {source, text, score}
    "center": {},     # lat, lon
    "city_key": "",
    "display_name": "",
}
```

**Loop:**

```text
for step in 1..max_steps:
    resp = client.responses.create(model, tools, input)
    append resp.output to input
    if no function_call items:
        return structured itinerary + tool_state
    for each function_call:
        execute Python tool
        append function_call_output
raise if max_steps exceeded (user-facing: raise max_steps or enable Fast mode)
```

**Fast mode vs full:**

- Fast: one `search_pois` (limit 40), optional one `retrieve_guides`, `max_steps=5`
- Full: 2–3 `search_pois` with different queries, `retrieve_guides` if RAG on, `max_steps=8–12`

**Trace events:** `model_call`, `tool_call` (+ args), `tool_result` (+ elapsed), `tool_error`, `note`. Render in an expander with timestamps. This is both a rubric item and a demo highlight.

### 6.5 POI search design

**Geocode:** Nominatim `format=json&limit=1` (or `limit=5` with a disambiguation dropdown if multiple matches — small UX win). Cache 24h. User-Agent: `waypoint-trip-planner/1.0 (contact: {email})`. Enforce 1 rps.

**Tags (start from course + sample, then extend slightly):**

| Interest | OSM tags |
|---|---|
| outdoors | leisure=park\|nature_reserve\|garden; tourism=viewpoint; natural=peak\|beach\|wood |
| food | amenity=restaurant\|cafe\|fast_food |
| coffee | amenity=cafe |
| museums | tourism=museum\|gallery |
| history | historic=.+ ; tourism=attraction |
| art | tourism=gallery\|museum |
| nightlife | amenity=bar\|pub\|nightclub |
| scenic | tourism=viewpoint; natural=peak |
| family | tourism=zoo\|theme_park; leisure=playground |
| shopping | shop=mall; amenity=marketplace |

Default tags if none selected: museums, parks, cafes, historic.

**POI record:**

```json
{
  "poi_id": "osm_node_123",
  "name": "Palace of the Governors",
  "category": "tourism:attraction",
  "lat": 35.687,
  "lon": -105.938,
  "url": "https://...",
  "_base_score": 0.72
}
```

`_base_score` is internal (strip before sending a huge list to the model if needed). Ranking:

```text
score = popularity_heuristic
      + interest_match
      + query_substring
      + feedback_boost(city_key, poi_id)
      - 0.1 * normalized_distance_from_center
```

Popularity heuristic (no extra APIs): OSM tags such as `wikipedia`, `wikidata`, `website`, `tourism=yes` as weak signals. This is better than alphabetical sort and still honest.

**Retries:** 3 attempts, exponential backoff, special-case HTTP 429. Overpass: try next public instance on timeout/5xx.

**Empty results:** return structured error to the model *and* a user-facing Streamlit warning (“No POIs in radius — widen radius or change interests”). Do not crash.

### 6.6 RAG design

Keep **TF-IDF + cosine similarity** (course requirement). Do not replace with embeddings/FAISS as the *primary* path; that would skip the intended demonstration. Optional later toggle is fine but not Phase 1.

Pipeline:

1. `action=query&list=search` → title
2. `action=parse&prop=text` → HTML
3. Clean with a small HTML-to-text pass that preserves `\n\n` between `<p>` / headings
4. Chunk 800–1000 chars, merge short leftovers, split on paragraph then sentence
5. `TfidfVectorizer(stop_words="english")` + `cosine_similarity`
6. Return top-k with `chunk_id = "{title}__{i}"`, `source`, `text`, `score`
7. Cache index in `st.cache_data` (text) + session (vectorizer objects — sklearn objects often cannot pickle; keep vectorizer in `st.session_state` like the sample, or rebuild from cached plaintext which is cheap)

**Failure policy:** 403 / empty / timeout → `hits=[]` and a sidebar note. Agent instructions: proceed with `sources=[]`. Never block itinerary generation on RAG.

### 6.7 UI design (product, not homework)

**Sidebar**

- OpenAI key (password) + remember checkbox + clear
- Optional: “use `OPENAI_API_KEY` env if present” for local dev
- User-Agent email (warn if still a placeholder)
- Fast mode, enable RAG, show trace
- Model (default `gpt-4.1-mini`; allow override)
- Max steps slider
- Map style light/dark
- Autosave on/off, save now, clear saved
- **API health:** buttons to ping Nominatim, Overpass, Wikivoyage with last status

**Main canvas (single page with sections, or two tabs max)**

Avoid cloning “Plan / Refine / Feedback” as three equal homework tabs. Stronger product flow:

1. **Plan** — inputs + Generate
2. **Itinerary** — always visible if state exists (days as columns or expanders; morning/afternoon/evening)
3. **Map** — day filter, paths, tooltips
4. **Improve** — refine text + regenerate-one-day + before/after
5. **Votes** — compact up/down on each POI card (not a separate afterthought tab), plus a small stats expander

Keep Streamlit columns:

```python
col1, col2, col3 = st.columns(3)
```

for morning / afternoon / evening.

**Map**

- `get_radius=35`, `radius_min_pixels=3`, `radius_max_pixels=10` (course)
- Color points by day (legend)
- Path through **all** stops in time order
- Day filter does not live inside the generate-button `if` block
- Attribution caption: “Map data © OpenStreetMap contributors”

**Persistence**

- `st.session_state` is source of truth during a session
- Autosave itinerary + allowed_pois + center + city_key to `data/app_state.json`
- Reload once on startup
- Document that Streamlit Cloud filesystem is ephemeral — BYO-key users still keep state for the session; local deploy keeps files

### 6.8 Refinement

Two paths, as required:

1. **Whole-trip refine** — pass existing JSON + user request; allow extra `search_pois`; merge new POIs into `allowed_pois`; validate IDs.
2. **Single-day regen** — prompt: only modify `day == N`; run `other_days_unchanged`; if fail, **do not apply**, show diff of which days changed, offer retry.

Store previous itinerary in `st.session_state["itinerary_prev"]` for a simple before/after expander (JSON or compact day list).

### 6.9 Feedback loop

Exact course math:

- Event: `{ts, city_key, poi_id, vote}` plus optional `name` for human-readable stats
- Boost: `0.25 * ups - 0.35 * downs`
- Applied inside `search_pois` after fetch, before truncation to `limit`

Add a small stats view: votes per city, top boosted POIs, last 10 events. Enough to prove the loop; not a full analytics product.

### 6.10 Reliability

| Failure | User-facing behavior |
|---|---|
| Empty API key | Stop with sidebar instruction |
| Bad key / 401 | Clear error, do not dump stack |
| Geocode empty | “City not found — try City, Country” |
| Overpass 429/timeout | Retry, then fallback host, then “POI service busy” |
| Zero POIs | Warn + suggest larger radius / different interests |
| Wikivoyage 403 | Toast + continue without RAG |
| Invalid itinerary JSON | Error + expander with raw output + do not overwrite last good itinerary |
| Unknown `poi_id` | Reject itinerary, keep previous |
| Day regen mutates other days | Reject, show which days drifted |
| Agent max_steps | Explain Fast mode / increase slider |
| Nominatim 403 | Explain User-Agent email + 1 rps |

Wrap agent calls with timeout messaging (Streamlit spinner + status). Use `requests` timeouts (15–30s) everywhere.

### 6.11 Tech choices (locked for Phase 1)

| Choice | Decision | Why |
|---|---|---|
| UI | Streamlit | Required |
| LLM API | OpenAI Responses API | Required |
| Default model | gpt-4.1-mini | Course default; cheap enough for demos |
| Maps | PyDeck | Required |
| RAG | TF-IDF + cosine (sklearn) | Required demonstration |
| Persistence | JSON + JSONL on disk | Required; SQLite only if we pick trip library as the extra |
| Validation | Pydantic + custom poi_id checks | Stronger than sample |
| Tests | pytest on pure functions | Portfolio + safety net |
| Deploy | Streamlit Community Cloud | Course-recommended, free, BYO-key |

---

## 7. Signature enhancement (the one extra that makes you memorable)

**Recommendation: Walking-coherent days via OSRM + duplicate / clustering guards.**

Why this one (and not weather/auth/PDF):

- It is still “AI engineering + external APIs + validation,” which matches the course story.
- It visibly improves itinerary *quality* (the sample’s biggest product gap).
- OSRM public API is free and similar in spirit to OSM (good neighbor: cache, don’t spam).
- Easy to demo on a map: “Day 1 stays downtown; walking times shown.”
- Fits an FDE narrative: you constrained the agent with *real-world geometry*, not just prompts.

**Mechanics (to implement later):**

1. After POIs are fetched, optionally cluster by haversine into `days` geographic groups (or instruct the model to minimize travel and then **repair** if consecutive stops exceed a walk threshold).
2. Tool `estimate_travel(from_poi_id, to_poi_id, mode="walking")` calling OSRM `route/v1/foot/{lon1},{lat1};{lon2},{lat2}`.
3. Show walking minutes on each block in the UI.
4. Validator: warn if a day’s sequential walking time > N minutes (e.g. 90) for “relaxed” pace.

**Explicitly defer (do not start unless the core is perfect):**

- Auth0 / logins
- Image generation (cost + latency)
- Weather
- Budgets
- PDF export (nice; second extra only after deploy)
- FAISS embeddings replacing TF-IDF
- Multi-city trips

If time remains after deploy: **JSON download + a simple printable HTML/PDF** is the second extra (shareability). Not before the map, validators, and RAG work.

---

## 8. What we will *not* do

- Fork or paste the sample `app.py` as our codebase
- Hardcode API keys
- Call Nominatim without a real User-Agent email in demos
- Block the whole app when Wikivoyage 403s
- Add five optional features poorly
- Use Chat Completions-only function calling when the course asks for Responses API
- Store secrets in git
- Treat Fast mode as optional to skip — it should be the **default on** for UX

---

## 9. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| OSM / Overpass rate limits during grading | Demo fails | Cache aggressively; Fast mode; fallback Overpass hosts; pre-warm cache for 2 demo cities |
| Wikivoyage 403 | RAG looks broken | Default RAG **off**; clear copy; still show the tool exists |
| Model invents POIs | Rubric fail | Strict tools + poi_id validator + structured itinerary |
| Streamlit reruns wipe UI | Known sample bug class | Render itinerary/map from session state only |
| Key cost overrun | Personal $ | gpt-4.1-mini; Fast mode; OpenAI usage caps |
| Streamlit Cloud ephemeral disk | Lost feedback | Document it; feedback still works in-session; optional note in README |
| Public Nominatim blocks cloud IP | Geocode fails | Clear error; document; consider `nominatim.openstreetmap.org` alternatives only if needed (Photon, etc.) as last resort |
| Looks too much like the sample | Weak portfolio | Modular code, product UI, OSRM coherence, tests, architecture README |

---

## 10. Step-by-step implementation plan (when we leave research)

Do **not** start coding until you explicitly say to implement. Order is chosen so each phase is demoable and maps onto a course module.

### Phase 0 — Repo hygiene (30–45 min)

**Build**

- `.gitignore`: `.venv/`, `__pycache__/`, `.env`, `.streamlit/secrets.toml`, `data/app_state.json`, `data/feedback.jsonl`
- `requirements.txt` with pinned-enough versions (`streamlit`, `openai>=1.40`, `pydeck`, `requests`, `scikit-learn`, `numpy`, `pandas`, `pydantic`, `pytest`)
- Empty package dirs + `data/.gitkeep`
- `README.md` stub (full README in Phase 10)

**Accept**

- Fresh venv install succeeds
- `streamlit run app.py` shows a titled shell page

**Maps to:** Module A (structure)

### Phase 1 — Streamlit skeleton + key management + API health (1–2 h)

**Build**

- Sidebar: password API key, remember, clear
- Optional env-var fallback for local
- User-Agent email field with placeholder warning
- `data/` mkdir
- Health panel: Nominatim search for a known city; Overpass tiny query; Wikivoyage search (non-fatal)

**Accept**

- Key never printed back in the UI
- Health panel shows pass/fail with status codes
- Failed health does not crash the app

**Maps to:** Module A, Module I (partial)

### Phase 2 — OSM geocode + POI search (2–3 h)

**Build**

- `geocode.py` with cache + 1 rps limiter
- `tags.py` interest map
- `overpass.py` with retries, 429 backoff, fallback hosts
- `search_pois` Python function returning the required fields
- Ranking stub (name match + later feedback)

**Accept**

- “Paris” / “Santa Fe, NM” / a tiny town all handled (empty list OK for tiny town)
- Cached second call is instant
- Unit-testable query builder (string contains expected tags)

**Maps to:** Module B, Module I, Module J (cache)

### Phase 3 — Wikivoyage RAG (1–2 h)

**Build**

- Fetch, HTML clean, chunk 800–1000, TF-IDF retrieve
- Cache plaintext; session-cache vectorizer
- Tool wrapper `retrieve_guides` honoring enabled flag

**Accept**

- Known city returns scored chunks
- Forced 403/empty path returns `[]` and a note
- Chunks do not split mid-sentence when paragraphs exist

**Maps to:** Module C

### Phase 4 — Agent loop + strict tools + tracing (3–4 h)

**Build**

- OpenAI tool JSON schemas (`strict: True`)
- `loop.py` Responses API orchestration
- `tool_state` accumulation
- Trace list + UI expander with timings
- Fast vs full prompt rules
- Max steps error

**Accept**

- With a real key: one generate produces tool calls visible in the trace
- Disabling RAG never calls Wikivoyage (or calls and immediately returns disabled note)
- `store=False` (don’t leak chats to OpenAI storage if we can avoid it)

**Maps to:** Module D, Module J

### Phase 5 — Itinerary schema, validation, UI render (2–3 h)

**Build**

- Pydantic `Itinerary` model
- `validate_itinerary_poi_ids`
- Duplicate POI check
- Pretty day/block UI, `why`, category, RAG sources expander
- JSON download
- Session state persistence + autosave
- Render **outside** the generate button

**Accept**

- Injecting a fake `poi_id` is rejected
- Changing unrelated widgets does not wipe the itinerary
- Download produces valid JSON

**Maps to:** Module E, Module D (validation)

### Phase 6 — PyDeck map (1–2 h)

**Build**

- Points from allowed POIs
- Full temporal PathLayer
- Day filter + color by day
- Zoom from spread
- Light/dark
- OSM attribution

**Accept**

- Filter All vs Day 1 does not clear itinerary
- Tooltips show name, category, day, block
- Dots remain readable at two zoom levels

**Maps to:** Module F

### Phase 7 — Refine + single-day regen (2 h)

**Build**

- Full refine prompt + merge POIs
- Single-day regen + `other_days_unchanged`
- Previous snapshot for before/after
- Persist after success only

**Accept**

- A refine that cites a new POI only works if `search_pois` returned it
- A regen that edits Day 2 and also Day 1 is **rejected**
- Multiple refine rounds keep accumulating

**Maps to:** Module G

### Phase 8 — Feedback loop (1–2 h)

**Build**

- Up/down on each POI
- JSONL append
- Boost in ranking
- City scoping
- Simple stats expander

**Accept**

- Upvote then new search for same city ranks that POI higher (unit test the math)
- Different `city_key` does not apply the boost
- Malformed JSONL lines are skipped

**Maps to:** Module H

### Phase 9 — Hardening, Fast mode polish, edge-case pass (2 h)

**Build**

- Input validation (empty city, days 1–7, radius bounds)
- All error table from Section 6.10
- Fast mode default on
- Trace always available after a run
- Sparse-city test (e.g. a small town) documented

**Accept**

- Manual script of 8 edge cases (see Section 11) without a crash

**Maps to:** Module I, Module J

### Phase 10 — Signature enhancement: OSRM coherence (2–3 h)

**Build**

- `estimate_travel` tool or post-process walking minutes
- UI captions for walk time
- Optional validator/warning for over-walking on relaxed pace
- Cache OSRM routes

**Accept**

- Map path and walk times agree on order
- OSRM failure degrades to “distance unknown” without blocking

**Maps to:** Module L (one extra)

### Phase 11 — README, screenshots, architecture diagram, deploy (2–3 h)

**Build**

- Portfolio README (see Section 12)
- Mermaid architecture diagram
- Screenshots: plan form, itinerary, map, trace, feedback
- Streamlit Community Cloud deploy, BYO-key
- Short demo script (90 seconds)

**Accept**

- Cold visitor can generate a 2-day plan with their own key
- README lists APIs, rate limits, costs, and how to run locally
- Live URL in README

**Maps to:** Module K

**Total estimated build time:** ~20–28 focused hours after this plan, plus key spend of a few dollars.

---

## 11. Test plan (manual + automated)

### 11.1 Automated (pytest)

- `validate_itinerary_poi_ids` accepts known IDs, rejects unknown
- `other_days_unchanged` detects drift
- Feedback boost math
- Interest → Overpass query contains expected tag keys
- Pydantic rejects missing `days`
- Chunker respects max_chars

### 11.2 Manual demo script (use this for recording)

1. Set User-Agent email and OpenAI key; run API health (all green or RAG yellow).
2. Destination: **Kyoto, Japan** (or **Santa Fe, NM** as a known-good OSM city); 3 days; interests food + history + outdoors; Fast mode on; RAG off. Generate.
3. Show trace: `search_pois` once, then JSON itinerary.
4. Show map All / Day 1; hover tooltip; path.
5. Turn RAG on, regenerate or refine “add a neighborhood walk from local guides.”
6. Refine: “more food, less museums.”
7. Regen Day 2 only; confirm Day 1/3 identical.
8. Upvote two POIs; mention they will rank higher next time.
9. Download JSON.
10. (Optional) Show walking minutes if OSRM phase is done.

### 11.3 Edge cases to click through before calling it done

- Empty city
- Nonsense city name
- No interests selected
- RAG on but Wikivoyage 403
- Fast mode off (slower, more tool calls)
- Clear key + remember unchecked
- Map day filter after generate
- Refresh browser with autosave on
- Tiny village with few POIs
- Paste a key that is invalid

---

## 12. README outline (write in Phase 11, not now)

The final README should be a hiring-manager skim, not a homework dump:

1. One-paragraph product description + live demo URL
2. Screenshot strip
3. What this demonstrates (agents, RAG, OSM, guardrails, feedback, deploy)
4. Architecture diagram (Mermaid)
5. Features
6. Setup (venv, `pip install -r`, `streamlit run app.py`)
7. API keys, costs, OSM etiquette, attribution
8. How the agent works (tools, strict schemas, validation)
9. Feedback loop
10. Troubleshooting (403, 429, map filter, empty POIs)
11. Deployment notes
12. License / “for learning”

Include OSM attribution and a link to the [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/).

---

## 13. Deployment plan

**Primary:** [Streamlit Community Cloud](https://streamlit.io/cloud)

- Public GitHub repo
- Main file: `app.py`
- Python 3.11
- **BYO-key in the UI** (do not put your personal key in secrets for a public demo)
- Secrets optional: none required
- Warn users about OSM rate limits in the sidebar

**Backup:** Hugging Face Spaces (Streamlit SDK) if Cloud queue or GitHub org issues.

**Do not** deploy with a shared org OpenAI key unless usage caps are strict — public apps get scraped.

**Post-deploy check**

- Incognito window, paste key, generate 1-day itinerary
- Confirm no key in logs
- Confirm two browsers don’t share session state (Streamlit isolates sessions; disk files may be shared on Cloud — document that `app_state.json` on Cloud is **not** multi-tenant safe). For Cloud, prefer **session-only** persistence as default and treat disk autosave as “single-demo-user / local.”

That last point is a production insight the sample misses: **local autosave to one JSON file is fine on a laptop and wrong as a multi-user store.** Top-candidate behavior: autosave to disk when running locally; on Cloud detect and keep state in `st.session_state` only.

---

## 14. Rubric coverage matrix

| Course module | How this plan covers it | Phase |
|---|---|---|
| A Structure + keys + OSM headers + data dir | Skeleton, health panel, User-Agent | 0–1 |
| B `search_pois` | Nominatim + Overpass + tags + cache + retries | 2 |
| C Wikivoyage RAG | TF-IDF retrieve, degrade on 403 | 3 |
| D Agent + strict tools + trace + validate | Responses loop, tool_state, poi_id check | 4–5 |
| E Streamlit itinerary UI | Day/block, download, persistence | 5 |
| F PyDeck | Scatter + path + day filter + styles | 6 |
| G Refine / regen | Full + single-day + before/after | 7 |
| H Feedback | JSONL + boosts + stats | 8 |
| I Errors / edges | Table in 6.10 + Phase 9 | 9 |
| J Performance / Fast mode | Caches, default Fast mode, trace | 2–4, 9 |
| K Polish + deploy | README, diagram, Cloud | 11 |
| L Optional extra | OSRM walking coherence only | 10 |

---

## 15. Decision log (locked unless you change it)

1. **Do not clone the sample repo.** Reimplement behaviors with a modular package and a product UI.
2. **Responses API + strict tools** for `search_pois` and `retrieve_guides`.
3. **Structured itinerary** via Pydantic / JSON schema, not brace-slicing alone.
4. **RAG stays TF-IDF** to match the course; optional embeddings out of scope.
5. **Fast mode default ON.**
6. **BYO OpenAI key** for deploy.
7. **One extra:** OSRM / geographic coherence.
8. **Python 3.11**, Streamlit-only, pytest for validators.
9. **Planning-only until you ask to implement.**

---

## 16. Immediate next action (waiting on you)

When you are ready to leave research:

1. Confirm the working name (`Waypoint` vs something else).
2. Confirm the signature extra (OSRM walking coherence vs another Module L idea).
3. Confirm deploy target (Streamlit Cloud vs Hugging Face).
4. Say **start Phase 0** (or “implement the full plan”).

I will then create the repo structure and implement in the phase order above, verifying UI in the browser as Streamlit screens land.
