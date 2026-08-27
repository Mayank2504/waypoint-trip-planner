# Waypoint release testing

Run all commands from the repository root with Python 3.11.

## Automated pre-push gates

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -r requirements.txt

python -m compileall app.py src ui
pip check
pytest -q -m "not live"
pytest --cov=src/waypoint --cov=ui --cov-report=term-missing -m "not live"
git diff --check
```

The deterministic suite mocks external I/O. It must pass without an OpenAI key.

## Low-volume live provider contracts

Run once before release, not on every commit:

```bash
WAYPOINT_RUN_LIVE_TESTS=1 pytest -q -m live
```

These tests make small requests to geocoding, Overpass, Wikivoyage, FOSSGIS OSRM, and Open-Meteo. Respect public-provider limits.

## Local manual scenarios

Start the app:

```bash
streamlit run app.py
```

### Generation matrix

- Generate 1-, 3-, and 7-day trips.
- Use a major city, Unicode destination, ambiguous city, sparse town, and nonsense input.
- Run Fast mode on and off.
- Run Wikivoyage RAG on and off.
- Confirm an invalid key, unavailable model, and quota error show actionable messages.

### Itinerary and guardrails

- Every generated `poi_id` must appear in the fetched POI state.
- Returned day count and ordered day numbers must match the request.
- Duplicate POIs and invented RAG source IDs must be rejected.
- Final generation and repair schemas must enumerate only IDs returned by tools; an invented POI ID must be replaced or rejected.
- A failed generation must preserve the previous valid itinerary.
- Whole-trip refinement can change multiple days.
- Single-day regeneration must reject any mutation to another day or the city.
- Before/after comparison remains visible after rerun.

### Map and OSRM

- All/day filters retain the itinerary.
- Markers, tooltip day/block, and route geometry match the displayed stop order.
- Walking leg totals match the route summary.
- Disable routing and confirm straight-line paths.
- Simulate or disconnect OSRM and confirm the itinerary still renders with fallback paths.
- Confirm Overpass mirror health reports each global endpoint separately.
- Confirm a valid empty Overpass response returns “no matches” without exhausting the operation deadline.

### Weather

- Test today, a near-future date, and a date beyond the 16-day forecast horizon.
- Verify itinerary day numbers map to the correct calendar dates.
- Confirm timezone, units, rain probability, and attribution.
- Simulate Open-Meteo failure and confirm planning still works.

### Persistence and isolation

- Locally: test autosave on/off, refresh, Save now, and Clear saved.
- Confirm the OpenAI key is never written to disk.
- On Cloud: open two browser profiles/incognito sessions.
- Generate different trips and votes in each session.
- Confirm itinerary, key, votes, routes, and weather never cross sessions.

### Export and accessibility

- Download JSON and validate it parses.
- Download PDF and inspect Unicode POI names and attribution.
- Check light/dark map styles and common desktop widths.
- Inspect app logs and git diff for secrets.

## Production smoke

After merging and Streamlit redeployment:

1. Open https://waypoint-trip-planner-mayank.streamlit.app/ in incognito.
2. Use BYO OpenAI key and a real contact email.
3. Generate a two-day trip with Fast mode on and RAG off.
4. Verify weather, walking route, map filter, refine, day regeneration, vote, JSON, and PDF.
5. Repeat isolation check in a second browser profile.
6. If core generation regresses, revert to the previous verified commit. Optional providers must degrade without taking down the itinerary.
