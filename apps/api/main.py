"""GigBid API. Run: uvicorn apps.api.main:app --port 8000"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from apps.api.routers import analytics, approvals, auth, jobs, messages, runs, settings
from apps.api.runtime import runtime


def start_simulator():
    """START_SIMULATOR=1: run GigSim-lite (student-built stand-in) next to the API, e.g. on a single Render box."""
    import subprocess
    import sys
    if (os.getenv("START_SIMULATOR") or "0") != "1":
        return None
    root = Path(__file__).resolve().parents[2]
    if not (root / "simulator/data/jobs_live.json").exists():
        subprocess.run([sys.executable, "-m", "simulator.generate"], cwd=root, check=True)
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "simulator.server:app", "--port", "8081",
                             "--log-level", "warning"], cwd=root)
    import time
    time.sleep(2)
    return proc


@asynccontextmanager
async def lifespan(app: FastAPI):
    sim = start_simulator()
    await runtime.start()
    from apps.api.seed import ensure_reviewer
    ensure_reviewer()
    yield
    await runtime.stop()
    if sim:
        sim.terminate()


app = FastAPI(title="GigBid API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=(os.getenv("CORS_ORIGINS") or "http://localhost:5173").split(","),
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def trace_id(request: Request, call_next):
    """One trace id flows from the UI request through the API and into graph config / MCP audit log."""
    request.state.trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex
    response = await call_next(request)
    response.headers["x-trace-id"] = request.state.trace_id
    return response


for r in (auth, jobs, approvals, messages, runs, analytics, settings):
    app.include_router(r.router)

WEB = Path(__file__).resolve().parents[1] / "web" / "dist"
if WEB.exists():   # single-container deploys serve the built frontend from the API
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        return FileResponse(WEB / "index.html")
