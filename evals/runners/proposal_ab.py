"""X2 signature extension: two proposal strategies as an A/B test in GigSim, with a significance test.

1. Set experiments.proposal_ab.enabled: true in agent/config.yaml (arms are assigned by job id).
2. Run the bid graph on a fixed GigSim job set and approve/submit the drafts (GigSim only, never live mode).
3. python -m evals.runners.proposal_ab   -> reads outcomes from GigSim and runs a two-proportion z-test.
"""
from __future__ import annotations

import asyncio
import math
import os

import httpx

from evals.runners.common import save
from evals.runners.gigsim_outcomes import OUTCOME_PATH

REPLIED = {"replied", "interview", "hired"}


def two_proportion_z(s1: int, n1: int, s2: int, n2: int) -> tuple[float, float]:
    """Returns (z, two-sided p). Normal approximation; report n so readers can judge it."""
    if not n1 or not n2:
        return float("nan"), float("nan")
    p = (s1 + s2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)) or float("inf")
    z = (s1 / n1 - s2 / n2) / se
    return round(z, 4), round(math.erfc(abs(z) / math.sqrt(2)), 4)


async def main(user: str = "eval"):
    base = (os.getenv("GIGSIM_BASE_URL") or "http://localhost:8081").rstrip("/")
    async with httpx.AsyncClient(timeout=30, headers={"Authorization": f"Bearer {os.getenv('GIGSIM_API_TOKEN')}"} if os.getenv("GIGSIM_API_TOKEN") else {}) as c:
        r = await c.get(base + OUTCOME_PATH.format(user=user))
        r.raise_for_status()
        data = r.json()
    props = data if isinstance(data, list) else data.get("proposals", [])
    from agent.nodes.writer import strategy_for
    arms: dict[str, list[int]] = {}
    for p in props:
        arm = strategy_for(p.get("job_id", ""))[0]
        arms.setdefault(arm, []).append(int(p.get("status") in REPLIED))
    a, b = arms.get("A", []), arms.get("B", [])
    z, pval = two_proportion_z(sum(a), len(a), sum(b), len(b))
    save("proposal_ab", {"A": {"n": len(a), "reply_rate": round(sum(a) / len(a), 4) if a else None},
                         "B": {"n": len(b), "reply_rate": round(sum(b) / len(b), 4) if b else None},
                         "z": z, "p_value": pval, "significant_at_0.05": bool(pval == pval and pval < 0.05)})


if __name__ == "__main__":
    asyncio.run(main())
