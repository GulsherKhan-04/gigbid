"""GigSim-lite: a STUDENT-BUILT stand-in for the instructor's GigSim (which was not in the starter kit).

REST API with jobs, clients, Connects, proposals, messages, per-token rate limits and occasional 5xx errors, plus
simulated clients with hidden preferences that decide reply / interview / hire. Deterministic per seed.

    python -m simulator.generate          # once, creates the data
    python -m uvicorn simulator.server:app --port 8081

Environment: SIM_POLICY=v1|v2 (v2 = the simulated 2 November policy update, see docs/POLICY_UPDATE_SIMULATED.md),
SIM_ERROR_RATE (default 0.02), SIM_RATE_LIMIT_PER_MIN (default 60), SIM_STATE (state file path).
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

DATA = Path(__file__).resolve().parent / "data"
STATE = Path(os.getenv("SIM_STATE") or DATA / "state.json")
POLICY = os.getenv("SIM_POLICY") or "v2"
ERROR_RATE = float(os.getenv("SIM_ERROR_RATE") or 0.02)
LIMIT = int(os.getenv("SIM_RATE_LIMIT_PER_MIN") or 60)
GENERIC = re.compile(r"^\s*(hi|hello|dear|i am|i'm)\b|passionate|expert|perfectly", re.I)

app = FastAPI(title="GigSim-lite (student-built stand-in)")
JOBS = {j["job_id"]: j for j in json.loads((DATA / "jobs_live.json").read_text())} if (DATA / "jobs_live.json").exists() else {}
CLIENTS = {c["client_id"]: c for c in json.loads((DATA / "clients.json").read_text())} if (DATA / "clients.json").exists() else {}
_hits: dict[str, list[float]] = {}


def load() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"connects": {}, "proposals": {}, "threads": {}, "idem": {}}


def save(s: dict) -> None:
    STATE.write_text(json.dumps(s, indent=1))


@app.middleware("http")
async def limits(request: Request, call_next):
    who = request.headers.get("authorization", "anon")
    now = time.time()
    hits = [t for t in _hits.get(who, []) if now - t < 60]
    if len(hits) >= LIMIT:
        return JSONResponse({"error": "rate limited"}, status_code=429, headers={"Retry-After": "5"})
    _hits[who] = hits + [now]
    if request.method == "GET" and random.random() < ERROR_RATE:
        return JSONResponse({"error": "simulated upstream failure"}, status_code=503)
    return await call_next(request)


def public(job: dict) -> dict:
    j = {k: v for k, v in job.items() if k != "persona_hint"}
    if POLICY == "v2" and not CLIENTS.get(job.get("client_id"), {}).get("payment_verified", True):
        j["connects_cost"] = job["connects_cost"] + 2           # policy v2: surcharge for unverified clients
    return j


@app.get("/health")
def health():
    return {"ok": True, "policy": POLICY, "jobs": len(JOBS)}


@app.get("/policy")
def policy():
    rules = ["No off-platform contact or payment", "No fabricated experience", "No guarantees"]
    if POLICY == "v2":
        rules += ["Proposals to clients without verified payment cost 2 extra Connects",
                  "Cover letters longer than 250 words are rejected"]
    return {"version": POLICY, "rules": rules}


@app.get("/jobs")
def search(q: str = "", limit: int = 20):
    words = q.lower().split()
    hits = [public(j) for j in JOBS.values()
            if not words or any(w in (j["title"] + " " + j["description"] + " " + " ".join(j["required_skills"])).lower()
                                for w in words)]
    return {"jobs": hits[:limit]}


@app.get("/jobs/{job_id}")
def job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "no such job")
    return public(JOBS[job_id])


@app.get("/clients/{client_id}")
def client(client_id: str):
    c = CLIENTS.get(client_id)
    if not c:
        raise HTTPException(404, "no such client")
    return {k: v for k, v in c.items() if k != "hidden"}          # hidden preferences never leave the simulator


@app.get("/freelancers/{user}/connects")
def connects(user: str):
    s = load()
    return {"user": user, "balance": s["connects"].setdefault(user, 100)}


@app.get("/freelancers/{user}/messages")
def messages(user: str, thread_id: str | None = None):
    out = []
    for tid, t in load()["threads"].items():
        if t["user"] == user and thread_id in (None, tid):
            out += [{**m, "thread_id": tid} for m in t["messages"]]
    return out


@app.get("/freelancers/{user}/proposals")
def proposals(user: str):
    return [p for p in load()["proposals"].values() if p["user"] == user and p["status"] != "draft"]


@app.post("/proposals")
async def create_draft(request: Request, idempotency_key: str | None = Header(None)):
    body = await request.json()
    s = load()
    if idempotency_key and idempotency_key in s["idem"]:
        return s["proposals"][s["idem"][idempotency_key]]
    if body.get("job_id") not in JOBS:
        raise HTTPException(404, "no such job")
    if POLICY == "v2" and len(body.get("cover_letter", "").split()) > 250:
        raise HTTPException(422, "policy v2: cover letter exceeds 250 words")
    did = "prop-" + uuid.uuid4().hex[:8]
    s["proposals"][did] = {"draft_id": did, "user": body.get("freelancer") or body.get("user"), "job_id": body["job_id"],
                           "cover_letter": body.get("cover_letter", ""), "bid_amount_usd": body.get("bid_amount_usd"),
                           "connects_cost": public(JOBS[body["job_id"]])["connects_cost"], "status": "draft"}
    if idempotency_key:
        s["idem"][idempotency_key] = did
    save(s)
    return s["proposals"][did]


def client_decides(p: dict) -> str:
    """Hidden-preference rules. Deterministic per proposal so reruns give the same outcome."""
    job, c = JOBS[p["job_id"]], CLIENTS.get(JOBS[p["job_id"]]["client_id"], {})
    h = c.get("hidden", {"budget_ceiling_factor": 1.1, "dislikes_generic": True, "must_have_skill_weight": 0.7})
    rnd = random.Random(int(hashlib.sha256((p["draft_id"] + p["cover_letter"]).encode()).hexdigest(), 16))
    text = p["cover_letter"].lower()
    skill_share = sum(s.lower() in text for s in job["required_skills"]) / max(1, len(job["required_skills"]))
    score = skill_share * h["must_have_skill_weight"]
    if h["dislikes_generic"] and GENERIC.search(p["cover_letter"]):
        score -= 0.5
    if (p.get("bid_amount_usd") or 0) > job["budget"]["max"] * h["budget_ceiling_factor"]:
        score -= 0.4
    if "?" in p["cover_letter"]:
        score += 0.1
    roll = rnd.random()
    if score > 0.55 and roll < 0.25:
        return "hired"
    if score > 0.45 and roll < 0.45:
        return "interview"
    if score > 0.25 and roll < 0.6:
        return "replied"
    return "ignored"


@app.post("/proposals/{draft_id}/submit")
def submit(draft_id: str, idempotency_key: str | None = Header(None)):
    s = load()
    p = s["proposals"].get(draft_id)
    if not p:
        raise HTTPException(404, "no such draft")
    if p["status"] != "draft":
        return p                                                  # already submitted: never charge twice
    bal = s["connects"].setdefault(p["user"], 100)
    if p["connects_cost"] > bal:
        raise HTTPException(402, "not enough Connects")
    s["connects"][p["user"]] = bal - p["connects_cost"]
    p["status"] = client_decides(p)
    p["submitted_at"] = time.time()
    if p["status"] in {"replied", "interview", "hired"}:
        tid = "thread-" + draft_id
        text = {"replied": "Thanks for the proposal. Can you tell me how you would handle testing?",
                "interview": "Your proposal stood out. Could we schedule a short call this week?",
                "hired": "We'd like to hire you. Can you start on Monday?"}[p["status"]]
        s["threads"][tid] = {"user": p["user"], "job_id": p["job_id"],
                             "messages": [{"id": uuid.uuid4().hex[:8], "from": "client", "text": text}]}
    save(s)
    return p


@app.post("/threads/{thread_id}/messages")
async def send(thread_id: str, request: Request):
    body = await request.json()
    s = load()
    t = s["threads"].get(thread_id)
    if not t:
        raise HTTPException(404, "no such thread")
    m = {"id": uuid.uuid4().hex[:8], "from": body.get("from") or t["user"], "text": body.get("text", "")}
    t["messages"].append(m)
    save(s)
    return m
