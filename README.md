# CaseGraph 

A self-contained, fully interactive Demo Mode for CaseGraph built on a **synthetic** financial-fraud case
("Operation Silver Ledger", 239 records). Every name, number, account, place and record is fictional and labelled
`SYNTHETIC DEMO DATA`.

> This was built **without access to your existing CaseGraph source**, so it is delivered as a drop-in module plus a
> standalone host app. It was tested standalone (38 backend tests + a 31-check browser run), **not** against your real code base.

## Layout
```
backend/
  main.py                 standalone host (NOT needed inside CaseGraph)
  demo/                   <- drop this package into your FastAPI project
    config.py db.py models.py   isolated engine + demo_* tables (SQLite default, PostgreSQL via DEMO_DATABASE_URL)
    dataset.py            synthetic dataset generator (deterministic, planted clues)
    seed.py               seed / reset
    analytics.py          computed: CCTV gaps, tower co-location, identity features, NetworkX graph
    scenarios.py          seeded contradictions, 3 scenarios + critic challenges
    reconstruction.py     5-agent workflow (Extractor, Correlator, Hypothesis, Critic, Report)
    assistant.py llm.py   grounded assistant; precomputed / Ollama / cloud modes with citation validation
    report.py             ReportLab PDF with watermark
    router.py             /api/demo/* endpoints
  tests/                  pytest suite
frontend/
  src/Landing.jsx         Live Investigation vs Explore Demo Case
  src/demo/               layout (DEMO MODE header), guided tour, 11 pages
```

## Run it
```bash
# backend
cd backend && pip install fastapi uvicorn sqlalchemy httpx networkx reportlab pillow pytest
uvicorn main:app --port 8000
pytest tests -q

# frontend (new terminal)
cd frontend && npm install && npm run dev      # http://localhost:5173  (proxies /api to :8000)
```

## Integrate into CaseGraph
1. Copy `backend/demo/` into your backend. `pip install` the packages above (add `psycopg` for PostgreSQL).
2. In your FastAPI app: `from demo import demo_router` then `app.include_router(demo_router)`. No auth dependency is attached on purpose.
3. Optional: set `DEMO_DATABASE_URL=postgresql+psycopg://user:pw@host/casegraph_demo` (a separate database/schema is recommended).
4. Copy `frontend/src/demo/`, `Landing.jsx` pieces and `api.js`; add the `/demo/*` routes and the two landing options.
   Import `reactflow/dist/style.css` and `leaflet/dist/leaflet.css` from JS (not CSS `@import` after `@tailwind`).
5. AI modes (all optional): `OLLAMA_URL`, `OLLAMA_MODEL`; `CLOUD_LLM_API_KEY` (+ `CLOUD_LLM_PROVIDER=anthropic|openai`, `CLOUD_LLM_MODEL`, `CLOUD_LLM_BASE_URL`).

## Isolation guarantees (tested)
Separate engine, `demo_`-prefixed tables, `DEMO-` ids, separate files directory, no imports from the live app, reset only touches demo tables/files.

## Known limitations / not done
- Sentence-Transformers is not used; identity scoring is explicit feature-based computation (Jaccard, string similarity, co-location).
- Local/Cloud AI paths are tested with a mocked transport only (no real Ollama or API call was made).
- Tests don't cover your real database, auth or existing UI, since that code was not available.
- Seeded confidence values are analyst-style estimates, not calibrated probabilities.

## Browser end-to-end check
With both servers running: `mkdir -p e2e-screens && NODE_PATH=$(npm root -g) node frontend/e2e/run.js` (needs `playwright` + Chromium).
Covers landing → vault → identity accept/reject → graph → timeline → contradictions → reconstruction → assistant → PDF download → reset → tour.
The final "no console errors" check fails only if your browser can't reach Google Fonts.
