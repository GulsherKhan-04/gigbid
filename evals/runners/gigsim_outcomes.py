"""Outcome metric: submit proposals for a FIXED job set to GigSim and read back simulated reply/hire rates.

GigSim's simulated clients decide reply/interview/hire. The endpoint below is a placeholder: check the GigSim
docs for how outcomes are exposed and edit OUTCOME_PATH. Run only against GigSim, never live mode.
"""
from __future__ import annotations

import asyncio
import os

import httpx

from evals.runners.common import save

OUTCOME_PATH = "/freelancers/{user}/proposals"


async def main(user: str = "eval"):
    base = (os.getenv("GIGSIM_BASE_URL") or "http://localhost:8081").rstrip("/")
    async with httpx.AsyncClient(timeout=30, headers={"Authorization": f"Bearer {os.getenv('GIGSIM_API_TOKEN')}"} if os.getenv("GIGSIM_API_TOKEN") else {}) as c:
        r = await c.get(base + OUTCOME_PATH.format(user=user))
        r.raise_for_status()
        props = r.json() if isinstance(r.json(), list) else r.json().get("proposals", [])
    n = len(props)
    replied = sum(p.get("status") in {"replied", "interview", "hired"} for p in props)
    hired = sum(p.get("status") == "hired" for p in props)
    save("gigsim_outcomes", {"n": n, "reply_rate": round(replied / n, 4) if n else None,
                             "hire_rate": round(hired / n, 4) if n else None})


if __name__ == "__main__":
    asyncio.run(main())
