"""Offline backend over data/sample/*.json for development and tests until GigSim is running."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "data" / "processed" / "fixture_market.json"


class FixtureBackend:
    def __init__(self):
        self.jobs = {j["job_id"]: j for j in json.loads((ROOT / "data/sample/jobs.json").read_text())}
        self.clients = {c["client_id"]: c for c in json.loads((ROOT / "data/sample/client_history.json").read_text())}
        self.state = json.loads(STATE.read_text()) if STATE.exists() else {
            "connects": {}, "drafts": {}, "messages": {}}

    def _save(self):
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(self.state, indent=1))

    async def search_jobs(self, query, limit):
        q = query.lower().split()
        hits = [j for j in self.jobs.values()
                if not q or any(w in (j["title"] + " " + j["description"] + " " + " ".join(j.get("required_skills", []))).lower()
                              for w in q)]
        return hits[:limit]

    async def get_job(self, job_id):
        j = dict(self.jobs[job_id])
        j.setdefault("client_id", next(iter(self.clients), None))
        return j

    async def get_client_history(self, client_id):
        return self.clients.get(client_id, {"client_id": client_id, "completed_projects": 0,
                                            "payment_verified": False})

    async def get_connects_balance(self, user):
        return {"user": user, "balance": self.state["connects"].setdefault(user, 80)}

    async def list_messages(self, user, thread_id):
        msgs = self.state["messages"].get(user, [])
        return [m for m in msgs if thread_id in (None, m["thread_id"])]

    async def create_proposal_draft(self, user, payload):
        did = "draft-" + uuid.uuid4().hex[:8]
        self.state["drafts"][did] = {**payload, "user": user, "status": "draft", "draft_id": did}
        self._save()
        return self.state["drafts"][did]

    async def submit_proposal(self, user, draft_id):
        d = self.state["drafts"][draft_id]
        if d["status"] != "submitted":
            cost = int(d.get("connects_cost", 0))
            bal = self.state["connects"].setdefault(user, 80)
            if cost > bal:
                raise ValueError("not enough Connects")
            self.state["connects"][user] = bal - cost
            d["status"] = "submitted"
            self._save()
        return d

    async def send_message(self, user, thread_id, text):
        m = {"thread_id": thread_id, "from": user, "text": text, "id": uuid.uuid4().hex[:8]}
        self.state["messages"].setdefault(user, []).append(m)
        self._save()
        return m
