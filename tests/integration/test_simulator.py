"""Bid graph against GigSim-lite over real HTTP: scam skipped, good job drafted, submit idempotent, client decides."""
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def sim(tmp_path_factory):
    if not (ROOT / "simulator/data/jobs_live.json").exists():
        subprocess.run([sys.executable, "-m", "simulator.generate"], cwd=ROOT, check=True)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {**os.environ, "SIM_STATE": str(tmp_path_factory.mktemp("sim") / "state.json"), "SIM_ERROR_RATE": "0"}
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "simulator.server:app", "--port", str(port)], cwd=ROOT, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            httpx.get(url + "/health")
            break
        except httpx.HTTPError:
            time.sleep(0.2)
    old = {k: os.environ.get(k) for k in ("MARKETPLACE_BACKEND", "GIGSIM_BASE_URL")}
    os.environ.update({"MARKETPLACE_BACKEND": "gigsim", "GIGSIM_BASE_URL": url})
    yield url
    p.terminate()
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.mark.asyncio
async def test_against_simulator(sim):
    from agent.graphs.bid_graph import build_bid_graph
    from agent.llm import set_llm
    from agent.mcp_client import hub
    from tests.fakes import FakeLLM
    import agent.mcp_client as mc
    await hub().close()
    mc._hub = None              # new hub so the marketplace server starts with the GigSim backend env
    set_llm(FakeLLM())
    jobs = json.loads((ROOT / "simulator/data/jobs_live.json").read_text())
    scam = next(j for j in jobs if "unpaid_work" in j["warning_signals"])
    good = next(j for j in jobs if not j["warning_signals"] and j["persona_hint"] == "ai-ml-engineer"
                and "Ignore" not in j["description"])
    g = build_bid_graph(InMemorySaver(), InMemoryStore())
    s = await g.ainvoke({"user_id": "t", "persona": "ai-ml-engineer", "profile": {}, "job": {"job_id": scam["job_id"]}},
                        {"configurable": {"thread_id": str(uuid.uuid4())}})
    assert s["status"] == "skipped"
    cfg = {"configurable": {"thread_id": str(uuid.uuid4())}}
    s = await g.ainvoke({"user_id": "t", "persona": "ai-ml-engineer", "profile": {}, "job": {"job_id": good["job_id"]}}, cfg)
    assert "__interrupt__" in s, (s.get("status"), s.get("errors"))
    done = await g.ainvoke(Command(resume={"action": "approve"}), cfg)
    assert done["status"] == "submitted", done.get("errors")
    props = httpx.get(f"{sim}/freelancers/t/proposals").json()
    assert len(props) == 1 and props[0]["status"] in {"replied", "interview", "hired", "ignored"}
    await hub().close()
    mc._hub = None
