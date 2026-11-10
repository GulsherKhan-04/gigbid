import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("EMBEDDINGS_PROVIDER", "hash")
os.environ.setdefault("MARKETPLACE_BACKEND", "fixtures")
os.environ.setdefault("MCP_TRANSPORT", "stdio")
os.environ.setdefault("MARKETPLACE_LEDGER", str(ROOT / "data/processed/test_ledger.db"))
os.environ.setdefault("START_SIMULATOR", "0")
os.environ.setdefault("LANGSMITH_TRACING", "false")
