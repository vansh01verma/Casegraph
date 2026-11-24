"""Demo Mode configuration.

Demo Mode uses its OWN SQLAlchemy engine and its OWN tables (all prefixed
``demo_``). It never imports or touches the live application's session, so a
demo action cannot modify live records by construction.

Set DEMO_DATABASE_URL to a PostgreSQL URL (e.g.
``postgresql+psycopg://user:pw@host/casegraph_demo``) to use PostgreSQL;
the default is a local SQLite file so the demo works with zero setup.
"""
from __future__ import annotations

import os
from pathlib import Path

DEMO_ROOT = Path(os.environ.get("DEMO_DATA_DIR", Path(__file__).resolve().parent.parent / "demo_data"))
DEMO_FILES_DIR = DEMO_ROOT / "files"          # synthetic CCTV frames etc. (separate from live uploads)
DEMO_REPORTS_DIR = DEMO_ROOT / "reports"
DEMO_DATABASE_URL = os.environ.get("DEMO_DATABASE_URL", f"sqlite:///{DEMO_ROOT / 'demo.db'}")

# Namespace: every demo case/record id carries this prefix, so a demo id can
# never collide with (or be mistaken for) a live case id.
DEMO_NAMESPACE = "DEMO"
DEMO_CASE_ID = "DEMO-CASE-0001"
SYNTHETIC_LABEL = "SYNTHETIC DEMO DATA"
WATERMARK = "SYNTHETIC DEMONSTRATION DATA – NOT A REAL INVESTIGATION"

# Master clock reference used for timestamp correction.
MASTER_CLOCK = "UTC+05:30 (IST) master clock"

# Optional AI backends. Nothing here is required.
OLLAMA_URL = os.environ.get("OLLAMA_URL", "")            # e.g. http://localhost:11434
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
CLOUD_LLM_PROVIDER = os.environ.get("CLOUD_LLM_PROVIDER", "anthropic")  # anthropic | openai
CLOUD_LLM_API_KEY = os.environ.get("CLOUD_LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
CLOUD_LLM_MODEL = os.environ.get("CLOUD_LLM_MODEL", "")
CLOUD_LLM_BASE_URL = os.environ.get("CLOUD_LLM_BASE_URL", "")


def ensure_dirs() -> None:
    for d in (DEMO_ROOT, DEMO_FILES_DIR, DEMO_REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
