"""Standalone FastAPI host for the isolated CaseGraph Demo Mode."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from demo import demo_router

app = FastAPI(title="CaseGraph Demo API")
origins = [
    origin.strip()
    for origin in os.environ.get(
        "FRONTEND_ORIGIN",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(demo_router)


@app.get("/api/health")
def health():
    return {"ok": True}
