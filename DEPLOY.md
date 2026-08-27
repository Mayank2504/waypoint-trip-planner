# Deploy to Streamlit Community Cloud

Waypoint is deployed at:

**https://waypoint-trip-planner-mayank.streamlit.app/**

## Repository and deployment source

- Repository: `Mayank2504/waypoint-trip-planner`
- Branch: `main`
- Main file: `app.py`
- Python: 3.11
- OpenAI: BYO-key only; no shared secret

## Connected deployment

Streamlit watches `main` and redeploys after a push. New work must pass all local tests on a feature branch before merging to `main`.

## 3. Post-deploy smoke test

1. Open the app URL in an incognito window.
2. Paste your OpenAI key; set a real User-Agent email.
3. Generate a 2-day itinerary (Fast mode on, RAG off).
4. Confirm routed map, walking legs, weather, JSON, and PDF downloads.
5. Open a second browser profile and confirm itinerary, votes, key, routes, and weather are not shared.

## Notes

- Cloud state is session-only; shared disk persistence is disabled.
- Respect Nominatim’s 1 req/s policy; caching is enabled in the app.
- Overpass uses global `lz4`, OSMF, and Private.coffee mirrors with bounded failover; the sidebar reports each mirror independently.
- Respect FOSSGIS OSRM’s 1 req/s policy and Open-Meteo’s non-commercial limits.
- Do not commit `.streamlit/secrets.toml` or `.env`.
