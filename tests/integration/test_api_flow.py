"""Inbox -> analysis -> approval -> submit through the HTTP API, including an API restart while a proposal
waits for approval (C6: approve after restart, submitted exactly once)."""
import asyncio
import os
import time

from fastapi.testclient import TestClient

from agent.llm import set_llm
from tests.fakes import FakeLLM


def wait(client, h, job_id, statuses, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        row = next((r for r in client.get("/api/jobs", headers=h).json() if r["job_id"] == job_id), None)
        if row and row["status"] in statuses:
            return row
        time.sleep(0.3)
    raise AssertionError(f"{job_id} never reached {statuses}: {row}")


def test_full_flow_with_restart(tmp_path):
    set_llm(FakeLLM())
    from apps.api.main import app
    with TestClient(app) as c:
        s = c.post("/api/auth/signup", json={"email": f"t{time.time()}@x.io", "password": "password123",
                                             "persona": "sample-ai-engineer", "saved_searches": [""]}).json()
        h = {"Authorization": f"Bearer {s['token']}"}
        assert set(c.post("/api/jobs/scout", headers=h).json()["queued"]) == {"sample-job-001", "sample-job-002"}
        assert wait(c, h, "sample-job-002", {"skipped"})["action"] == "skip"
        wait(c, h, "sample-job-001", {"awaiting_approval"})
        assert c.get("/api/approvals", headers=h).json()[0]["payload"]["dry_run"]["dry_run"] is True
    # --- the API process "crashes" here; a new one starts on the same database ---
    set_llm(FakeLLM())
    with TestClient(app) as c:
        pending = c.get("/api/approvals", headers=h).json()
        assert [p["job_id"] for p in pending] == ["sample-job-001"]
        assert c.post("/api/approvals/sample-job-001", headers=h, json={"action": "approve"}).status_code == 200
        wait(c, h, "sample-job-001", {"submitted"})
        detail = c.get("/api/jobs/sample-job-001", headers=h).json()["state"]
        assert detail["submission"]["submit"]["replayed"] is False
        assert c.post("/api/approvals/sample-job-001", headers=h, json={"action": "approve"}).status_code == 409
        hist = c.get("/api/runs/sample-job-001/history", headers=h).json()
        assert len(hist) > 5
