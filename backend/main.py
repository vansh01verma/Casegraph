"""Standalone app for running/testing Demo Mode.

In the real CaseGraph codebase you would NOT use this file; just add

    from demo import demo_router
    app.include_router(demo_router)

to your existing FastAPI app. See INTEGRATION.md.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from demo import demo_router

app = FastAPI(title="CaseGraph (Demo Mode host)")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(demo_router)


@app.get("/api/health")
def health():
    return {"ok": True}
