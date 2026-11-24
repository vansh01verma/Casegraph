"""Configuration for the isolated synthetic Demo Mode."""
from __future__ import annotations

import os
from pathlib import Path

DEMO_ROOT = Path(os.environ.get("DEMO_DATA_DIR", Path(__file__).resolve().parent.parent / "demo_data"))
DEMO_FILES_DIR = DEMO_ROOT / "files"
DEMO_REPORTS_DIR = DEMO_ROOT / "reports"
DEMO_DATABASE_URL = os.environ.get("DEMO_DATABASE_URL", f"sqlite:///{DEMO_ROOT / 'demo.db'}")
# SQLAlchemy's PostgreSQL dialect needs the psycopg v3 driver explicitly.
if DEMO_DATABASE_URL.startswith("postgres://"):
    DEMO_DATABASE_URL = "postgresql+psycopg://" + DEMO_DATABASE_URL[len("postgres://"):]
elif DEMO_DATABASE_URL.startswith("postgresql://"):
    DEMO_DATABASE_URL = "postgresql+psycopg://" + DEMO_DATABASE_URL[len("postgresql://"):]

DEMO_NAMESPACE = "DEMO"
DEMO_CASE_ID = "DEMO-CASE-0001"
SYNTHETIC_LABEL = "SYNTHETIC DEMO DATA"
WATERMARK = "SYNTHETIC DEMONSTRATION DATA – NOT A REAL INVESTIGATION"
MASTER_CLOCK = "UTC+05:30 (IST) master clock"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
CLOUD_LLM_PROVIDER = os.environ.get("CLOUD_LLM_PROVIDER", "anthropic")
CLOUD_LLM_API_KEY = os.environ.get("CLOUD_LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
CLOUD_LLM_MODEL = os.environ.get("CLOUD_LLM_MODEL", "")
CLOUD_LLM_BASE_URL = os.environ.get("CLOUD_LLM_BASE_URL", "")


def ensure_dirs() -> None:
    for directory in (DEMO_ROOT, DEMO_FILES_DIR, DEMO_REPORTS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
