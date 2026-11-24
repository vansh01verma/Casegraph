import os
import sys
import tempfile
from pathlib import Path

# Must be set BEFORE importing the demo package (config reads env at import time).
_TMP = tempfile.mkdtemp(prefix="demo_tests_")
os.environ["DEMO_DATA_DIR"] = _TMP
os.environ["DEMO_DATABASE_URL"] = f"sqlite:///{_TMP}/demo.db"
for k in ("CLOUD_LLM_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_URL"):
    os.environ.pop(k, None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from demo import config, llm, seed  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def fresh_demo(client):
    """Every test starts from the pristine demo state with no AI configured."""
    llm.set_transport(None)
    config.CLOUD_LLM_API_KEY = ""
    config.OLLAMA_URL = ""
    seed.seed()
    yield
    llm.set_transport(None)
    config.CLOUD_LLM_API_KEY = ""
    config.OLLAMA_URL = ""
