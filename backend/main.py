"""Standalone app for running/testing Demo Mode.

In the real CaseGraph codebase you would NOT use this file; just add

    from demo import demo_router
    app.include_router(demo_router)

to your existing FastAPI app. See INTEGRATION.md.
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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

# API routes
app.include_router(demo_router)


@app.api_route("/api/health", methods=["GET", "HEAD"])
def health():
    return {"ok": True}


# Frontend static files & SPA fallback
_backend_dist = Path(__file__).resolve().parent / "dist"
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
STATIC_DIR = _backend_dist if _backend_dist.exists() else (_frontend_dist if _frontend_dist.exists() else None)

if STATIC_DIR and (STATIC_DIR / "index.html").exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.api_route("/", methods=["GET", "HEAD"])
    def root():
        return {
            "name": "CaseGraph Backend API",
            "status": "online",
            "health": "/api/health",
            "demo_api": "/api/demo/overview",
            "message": "Backend is active."
        }


