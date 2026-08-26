# Deploy to Streamlit Community Cloud

Waypoint is ready for Cloud deploy once the code is on a public GitHub repo.

## 1. Push to GitHub

If `gh` is not authenticated on this machine:

```bash
gh auth login -h github.com
```

Then from the project root:

```bash
git remote add origin https://github.com/<YOUR_USER>/waypoint-trip-planner.git
git branch -M main
git push -u origin main
```

Or create the repo in one step:

```bash
gh repo create waypoint-trip-planner --public --source=. --remote=origin --push
```

## 2. Create the Streamlit app

1. Open [https://share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. **New app** → select `waypoint-trip-planner` (or your repo name).
3. Branch: `main`
4. Main file path: `app.py`
5. Deploy **without** putting an OpenAI key in Secrets (BYO-key in the sidebar).

## 3. Post-deploy smoke test

1. Open the app URL in an incognito window.
2. Paste your OpenAI key; set a real User-Agent email.
3. Generate a 2-day itinerary (Fast mode on, RAG off).
4. Confirm map, JSON download, and PDF download work.

## Notes

- Cloud filesystem is ephemeral — session state is the source of truth between reruns.
- Respect Nominatim’s 1 req/s policy; caching is enabled in the app.
- Do not commit `.streamlit/secrets.toml` or `.env`.
