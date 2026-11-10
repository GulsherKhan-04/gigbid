"""Starts the API with the scripted FakeLLM, for UI tests and screenshots without any API key.
Never used in production:  python -m tests.demo_server"""
import os

os.environ.setdefault("EMBEDDINGS_PROVIDER", "hash")
os.environ.setdefault("MARKETPLACE_BACKEND", "fixtures")
os.environ.setdefault("REVIEWER_EMAIL", "reviewer@gigbid.dev")
os.environ.setdefault("REVIEWER_PASSWORD", "reviewer-demo-pass")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:8000")

import uvicorn  # noqa: E402

from agent.llm import set_llm  # noqa: E402
from tests.fakes import FakeLLM  # noqa: E402

set_llm(FakeLLM())
uvicorn.run("apps.api.main:app", host="127.0.0.1", port=int((os.getenv("PORT") or 8000)))
