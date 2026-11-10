"""Arq worker: scheduled scouting and long agent runs, outside web requests (E1).

    arq worker.main.WorkerSettings

Scouting uses the conservative interval from config (marketplace.scout_interval_minutes). Runs are idempotent:
a job already in a user's inbox is never re-analysed, and submits are protected by idempotency keys.
"""
from __future__ import annotations

import os

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from agent.marketplace_port import marketplace
from agent.mcp_client import ServerDown
from agent.nodes.scout import fingerprint
from agent.settings import config
from apps.api import db
from apps.api.runtime import runtime


async def startup(ctx):
    await runtime.start()


async def shutdown(ctx):
    await runtime.stop()


async def run_bid_job(ctx, user: dict, job: dict, resume: dict | None = None):
    await runtime.run_bid(user, job, resume)


async def scout_all(ctx):
    with db.engine.connect() as c:
        users = [dict(r._mapping) for r in c.execute(select(db.users))]
    for u in users:
        known = {r["job_id"] for r in db.list_jobs(u["id"])}
        seen = set()
        try:
            for q in (u.get("profile") or {}).get("saved_searches") or [""]:
                for j in await marketplace("scout").search_jobs(u["id"], q):
                    fp = fingerprint(j)
                    if j["job_id"] in known or fp in seen:
                        continue
                    seen.add(fp)
                    known.add(j["job_id"])
                    db.upsert_job(u["id"], j["job_id"], title=j.get("title"), status="queued", stage="queued")
                    await runtime.run_bid(u, j)
        except ServerDown:
            # Degraded mode: leave work queued; the next tick retries. The UI shows the banner from /api/health.
            return {"degraded": True}
    return {"users": len(users)}


_every = max(5, int(config()["marketplace"]["scout_interval_minutes"]))


class WorkerSettings:
    functions = [run_bid_job]
    cron_jobs = [cron(scout_all, minute=set(range(0, 60, min(_every, 59))) if _every < 60 else {0},
                      run_at_startup=False)]
    on_startup, on_shutdown = startup, shutdown
    redis_settings = RedisSettings.from_dsn((os.getenv("REDIS_URL") or "redis://localhost:6379/0"))
    max_jobs = 4
    job_timeout = 600
