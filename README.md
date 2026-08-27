# Waypoint — AI Trip Planner Capstone

**Waypoint** is a production-style Streamlit app that plans multi-day city itineraries with an OpenAI **Responses API** agent, live **OpenStreetMap** points of interest, optional **Wikivoyage RAG**, an interactive **PyDeck** map, a city-scoped feedback loop, and **PDF/JSON export**.

**Repo:** [Mayank2504/waypoint-trip-planner](https://github.com/Mayank2504/waypoint-trip-planner)

**Live app:** [waypoint-trip-planner-mayank.streamlit.app](https://waypoint-trip-planner-mayank.streamlit.app/)

> Bring your own OpenAI API key. No keys are required for Nominatim, Overpass, or Wikivoyage.

## Screenshots

![Waypoint plan form](assets/screenshots/waypoint-plan.png)

![Waypoint routed map with weather and walking summary](assets/screenshots/waypoint-routed-map.png)

![Waypoint refinement controls](assets/screenshots/waypoint-refinement.png)

![Waypoint refinement and feedback controls](assets/screenshots/waypoint-feedback.png)

## What this demonstrates

| Skill | How it shows up |
| --- | --- |
| Agentic tool calling | Strict `search_pois` / `retrieve_guides` schemas on the Responses API |
| External data | Nominatim geocoding + Overpass POIs with retries and host fallbacks |
| RAG | Optional Wikivoyage fetch → TF-IDF + cosine similarity |
| Guardrails | Pydantic itinerary schema + `poi_id` validation + single-day regen check |
| UX | Day/block itinerary, PyDeck map, execution trace, Fast mode |
| Feedback loop | Up/down votes → ranking boosts for the same city |
| Persistence | Private Cloud session state + atomic local JSON autosave |
| Enrichment | OSRM walking routes + date-aligned Open-Meteo forecasts |
| Portfolio polish | PDF export, modular package layout, comprehensive pytest coverage |

## Course requirement coverage

All required capstone capabilities from `CAPSTONE_PLAN.md` are implemented:

- [x] **Project and API setup** — modular Python 3.11 application, secure BYO OpenAI key input, identifying User-Agent, API health controls, and gitignored runtime state.
- [x] **Live POI search** — Nominatim geocoding with Open-Meteo/Photon fallbacks, bounded Overpass node/way/relation queries, interest mapping, caching, retries, mirror fallback, and structured POIs.
- [x] **Wikivoyage RAG** — article retrieval, HTML cleanup, paragraph-aware chunks, TF-IDF indexing, cosine ranking, source IDs, caching, and graceful degradation.
- [x] **Agent orchestration** — OpenAI Responses API, strict function schemas, multi-step tools, accumulated tool state, step/time limits, and execution traces.
- [x] **Output guardrails** — per-run POI/source ID enums, strict Pydantic models, structured output, exact day checks, duplicate detection, bounded repair, and preservation of the last valid plan.
- [x] **Streamlit experience** — destination, date, pace, interests, constraints, progress, day/block cards, JSON/PDF downloads, and state-safe reruns.
- [x] **Interactive map** — PyDeck markers, tooltips, day filters, light/dark styles, filtered framing, temporal paths, OSRM geometry, and straight-line fallback.
- [x] **Refinement** — whole-trip refinement, protected single-day regeneration, repeated changes, validation, persistence, and before/after comparison.
- [x] **Feedback loop** — up/down votes, exact `+0.25`/`-0.35` boosts, destination scoping, statistics, local JSONL, and private Cloud-session feedback.
- [x] **Reliability and performance** — bounded requests, exponential retries, provider fallbacks, Fast mode, non-blocking enrichments, actionable errors, and caches.
- [x] **Deployment and portfolio** — public repository, live Streamlit app, architecture, screenshots, example output, test guide, and provider attribution.
- [x] **Enhancements** — walking routes/times, weather forecasts, and Unicode-aware PDF export.

Release verification:

- **88 deterministic tests passing**
- **5 low-volume live provider contracts passing**
- **89% combined backend/UI coverage**
- **Python 3.11 compile, dependency, lint, diff, and secret checks passing**

## Architecture

![Waypoint AI Trip Planner architecture](AI-trip-planner-architecture-diagram.png)

The editable diagram source is available in [`docs/architecture.mmd`](docs/architecture.mmd); the reproducible PNG renderer is [`docs/render_architecture.py`](docs/render_architecture.py).

### Mermaid data-flow view

```mermaid
flowchart TD
  user["Traveler"]
  streamlit["Streamlit UI"]
  inputValidation["Input validation"]
  agentLoop["OpenAI Responses agent loop"]
  toolRouter["Strict tool dispatcher"]
  geocoder["Nominatim geocoder"]
  geocodeFallback["Open-Meteo and Photon fallbacks"]
  overpass["Overpass POI search"]
  wikivoyage["Wikivoyage article retrieval"]
  tfidf["TF-IDF and cosine retrieval"]
  toolState["Tool state: POIs, chunks, center"]
  itinerarySchema["Structured Pydantic itinerary"]
  semanticGuards["POI, source, day and regeneration guards"]
  sessionState["Private Streamlit session state"]
  localState["Atomic local JSON and JSONL"]
  feedback["City-scoped feedback boosts"]
  osrm["FOSSGIS OSRM walking routes"]
  forecast["Open-Meteo daily forecast"]
  map["PyDeck map and day filters"]
  itineraryUI["Day and block itinerary UI"]
  exports["JSON and PDF exports"]
  trace["Execution trace and timings"]

  user --> streamlit --> inputValidation --> agentLoop
  agentLoop --> toolRouter
  toolRouter -->|"search_pois"| geocoder
  geocoder -->|"403, 429 or empty"| geocodeFallback
  geocoder --> overpass
  geocodeFallback --> overpass
  toolRouter -->|"retrieve_guides"| wikivoyage --> tfidf
  overpass --> toolState
  tfidf --> toolState
  toolState --> agentLoop
  agentLoop --> itinerarySchema --> semanticGuards --> sessionState

  sessionState --> itineraryUI
  sessionState --> osrm --> map
  sessionState --> forecast --> itineraryUI
  sessionState --> map
  sessionState --> exports
  sessionState --> trace
  itineraryUI --> feedback -->|"ranking boost"| overpass
  sessionState -->|"local runtime only"| localState
```

### Runtime flow

1. Streamlit validates the trip request and invokes the Responses API agent.
2. The model must call `search_pois`; it may call `retrieve_guides` when RAG is enabled.
3. Tool results accumulate in `tool_state`, giving the model only approved POI and source IDs.
4. After tool execution, the final JSON schema dynamically restricts `poi_id` and source values to IDs returned during that run.
5. The response is then validated against requested days, returned POIs, retrieved chunks, duplicate rules, and regeneration invariants.
6. A valid plan enters private session state. Failures never replace the previous valid itinerary.
7. OSRM routes and Open-Meteo forecasts run as optional post-validation enrichments; their failure cannot remove the itinerary.
8. The UI renders itinerary cards, routed/fallback paths, weather, trace, feedback controls, and JSON/PDF downloads.

### Persistence and isolation

- **Streamlit Cloud:** keys, itineraries, feedback, routes, and weather remain in the current browser session; shared filesystem persistence is disabled.
- **Local development:** itinerary state is atomically saved to `data/app_state.json`; feedback appends to `data/feedback.jsonl`.
- Secrets are never written to application state, and `.env`/Streamlit secret files are excluded from version control.

## Features

- Destination, days, pace, interests, constraints
- Fast mode (default): one broad `search_pois` call for quicker plans
- Optional Wikivoyage RAG (off by default — public APIs may return 403)
- Day × Morning / Afternoon / Evening itinerary cards
- Map with day filter, colored markers, full temporal paths
- Policy-compliant OSRM walking geometry, leg times, distance, and graceful straight-line fallback
- Date-aware Open-Meteo daily forecasts that never block planning
- Refine whole trip or regenerate a single day (other days must stay unchanged)
- Upvote / downvote POIs; boosts feed the next search for that city
- Download `itinerary.json` and `itinerary.pdf`
- Sidebar API health checks (Nominatim / Overpass / Wikivoyage)
- Execution trace with timings

## Project layout

```text
app.py                 # Streamlit entry (UI wiring)
src/waypoint/          # Agent, OSM, RAG, validation, routing, weather, PDF
ui/                    # Sidebar, map, itinerary, health, trace
tests/                 # pytest
data/                  # Runtime state (gitignored JSON/JSONL)
assets/fonts/          # Optional DejaVuSans.ttf for PDF Unicode
requirements.txt
```

## Setup (local)

**Python 3.11** is recommended and used for release verification.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Optional: `export OPENAI_API_KEY=sk-...` so the sidebar picks up your key.

In the sidebar, set a **real contact email** for the OSM/Wikivoyage User-Agent.

### Tests

```bash
PYTHONPATH=src pytest -q -m "not live"
# Optional low-volume provider contract checks:
WAYPOINT_RUN_LIVE_TESTS=1 PYTHONPATH=src pytest -q -m live
```

The release suite currently contains 88 deterministic tests and enforces at least 85% combined backend/UI coverage. See [`TESTING.md`](TESTING.md) for the complete local, failure, isolation, and production-smoke matrix.

## API keys and costs

| Service | Key? | Notes |
| --- | --- | --- |
| OpenAI | Yes (BYO) | Default model `gpt-4.1-mini`. Typical plan ≈ $0.01–0.05. Set a usage cap. |
| Nominatim | No | [Usage policy](https://operations.osmfoundation.org/policies/nominatim/): 1 req/s, identifying User-Agent, cache results |
| Overpass | No | Global `lz4`, primary OSMF, and Private.coffee mirrors; bounded failover on timeout/429/5xx |
| Wikivoyage | No | May 403 without a proper User-Agent — leave RAG off |
| FOSSGIS OSRM | No | Walking routes; non-commercial reasonable use; maximum 1 request/second |
| Open-Meteo | No | Forecasts; free non-commercial limit 10,000 calls/day; attribution required |

**Never commit keys.** `.streamlit/secrets.toml` and `.env` are gitignored. For Streamlit Cloud, prefer BYO-key in the UI (no shared secret).

## How the agent works

1. User submits city / days / interests.
2. Agent loop (`client.responses.create`, `store=False`) may call:
   - `search_pois` → geocode + Overpass + feedback-aware ranking
   - `retrieve_guides` → Wikivoyage TF-IDF chunks (if RAG enabled)
3. Final JSON is validated with Pydantic and checked so every `poi_id` came from tools.
4. Validated itineraries are enriched with optional OSRM routes and Open-Meteo weather.
5. UI renders itinerary + map. Local votes use JSONL; Cloud votes remain private to the browser session.

**Feedback boosts:** `+0.25` per upvote, `-0.35` per downvote, scoped by `city_key`.

## Example output

A sanitized itinerary is checked in at [`examples/santa-fe-itinerary.json`](examples/santa-fe-itinerary.json).

Useful demonstrations:

- Food-and-outdoors weekend with routed walking legs
- Rain-aware day review using the daily forecast
- Single-day regeneration while every other day remains unchanged
- Feedback-driven POI reranking for a repeated local search

## Deploy (Streamlit Community Cloud)

**GitHub:** https://github.com/Mayank2504/waypoint-trip-planner

The app is live at [waypoint-trip-planner-mayank.streamlit.app](https://waypoint-trip-planner-mayank.streamlit.app/).

It deploys from `Mayank2504/waypoint-trip-planner`, branch `main`, entrypoint `app.py`.
Keep OpenAI as BYO-key; do not add a shared API key to Streamlit Secrets.

See [DEPLOY.md](DEPLOY.md) for more detail.

On Cloud, itineraries, votes, routes, weather, and keys are session-only. Local development can use atomic disk autosave.

## Operational constraints

- Streamlit Cloud state is intentionally session-only to prevent one visitor from reading another visitor’s itinerary. Closing/restarting the session clears the trip and feedback.
- Weather is an advisory display enrichment; it does not currently change the model’s selected POIs automatically.
- Nominatim, Overpass, Wikivoyage, FOSSGIS OSRM, and Open-Meteo are public services without uptime guarantees. Each integration has bounded timeouts and a safe fallback.
- Overpass treats an HTTP 200 response with zero matches as valid data instead of retrying every mirror. Mirror health is shown separately in the sidebar.
- Walking routes use the free FOSSGIS service for reasonable non-commercial use. A production/commercial deployment should use a contracted or self-hosted routing provider.
- The public demo remains BYO-key so OpenAI usage and billing stay with the person generating the itinerary.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Nominatim / Wikivoyage 403 | Set a real User-Agent email; wait if rate-limited |
| Overpass timeout | Check mirror details; retry later or use Fast mode. Smaller radii reduce public-server load. |
| Empty itinerary / unknown `poi_id` | Check execution trace; raise max steps |
| Map filter clears UI | Fixed: itinerary renders from session state outside the Generate button |
| PDF looks wrong for CJK names | Add `assets/fonts/DejaVuSans.ttf` or rely on system Unicode fonts |
| Walking route unavailable | The app safely falls back to straight map paths; retry later |
| Forecast unavailable | Confirm dates are within the next 16 days; itinerary generation still works |

## License

Use freely for learning and portfolio demos. Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.
