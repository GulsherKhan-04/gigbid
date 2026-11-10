"""Scout: runs saved searches (worker, on a schedule), deduplicates and queues new jobs. Inside the bid graph
it is the entry node that loads the full job through the marketplace port."""
from __future__ import annotations

import hashlib
import time

from agent.marketplace_port import marketplace
from agent.nodes.common import update


def fingerprint(job: dict) -> str:
    """Duplicates in the stream are reposts with a new id: dedupe on normalised title + description."""
    text = " ".join((job.get("title", "") + " " + job.get("description", "")).lower().split())
    return hashlib.sha1(text.encode()).hexdigest()[:16]


async def run_saved_search(user: str, query: str, seen: set[str]) -> list[dict]:
    jobs = await marketplace("scout").search_jobs(user, query)
    fresh = []
    for j in jobs:
        fp = fingerprint(j)
        if fp not in seen and j.get("job_id") not in seen:
            seen.update({fp, j.get("job_id")})
            fresh.append(j)
    return fresh


async def scout_node(state):
    t0 = time.monotonic()
    job = state["job"]
    if "description" not in job:
        job = await marketplace("scout").get_job(state["user_id"], job["job_id"])
    return update("scout", t0=t0, job=job, status="analysing")
