"""Standalone app for running/testing Demo Mode.

In the real CaseGraph codebase you would NOT use this file; just add

    from demo import demo_router
    app.include_router(demo_router)

to your existing FastAPI app. See INTEGRATION.md.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from demo import demo_router

app = FastAPI(title="CaseGraph (Demo Mode host)")

# Allow CORS from local dev as well as production Render frontend
cors_origins_env = os.environ.get("CORS_ORIGINS", "*")
if cors_origins_env == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    for default_origin in ["http://localhost:5173", "http://127.0.0.1:5173"]:
        if default_origin not in allowed_origins:
            allowed_origins.append(default_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True if allowed_origins != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(demo_router)


@app.get("/api/health")
def health():
    return {"ok": True}

