"""Pricing Strategist: market statistics + client budget + the user's floor, and whether the Connects are worth it.
Deterministic so it is cheap, explainable and easy to change when the platform policy changes."""
from __future__ import annotations

import json
import statistics
import time
from functools import lru_cache
from pathlib import Path

from agent.handoffs import PriceQuote
from agent.marketplace_port import marketplace
from agent.nodes.common import update
from agent.settings import config

ROOT = Path(__file__).resolve().parents[2]


@lru_cache
def market_stats() -> dict[str, list[float]]:
    """Historical job budgets by category (GigSim's ~1,500 historical jobs once present in data/)."""
    out: dict[str, list[float]] = {}
    for f in list((ROOT / "data").rglob("historical_jobs*.json*")) + [ROOT / "data/sample/jobs.json"]:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        rows = [json.loads(x) for x in text.splitlines() if x.strip()] if f.suffix == ".jsonl" else json.loads(text)
        for j in rows:
            b = j.get("budget") or {}
            val = b.get("max") or b.get("min") or j.get("price") or j.get("final_price")
            if val:
                out.setdefault(j.get("category", "general"), []).append(float(val))
    return out


def quote(job: dict, spec: dict, profile: dict, balance: int) -> PriceQuote:
    pol = config()["policy"]["connects"]
    b = job.get("budget") or {}
    lo, hi = spec.get("budget_min") or b.get("min"), spec.get("budget_max") or b.get("max")
    floor = float(profile.get("minimum_project_budget_usd", 0))
    cat = spec.get("category", "general")
    hist = market_stats().get(cat) or [v for vs in market_stats().values() for v in vs]
    median = statistics.median(hist) if hist else None
    if lo is not None and hi:
        amount = lo + 0.65 * (hi - lo)              # upper-middle of the client's band
        basis = f"65% into the client's band {lo:.0f}-{hi:.0f}"
    elif median:
        amount, basis = median, f"market median for '{cat}' ({median:.0f}, n={len(hist)})"
    else:
        amount, basis = floor, "the freelancer's floor (no budget or market data)"
    amount = max(amount, floor)
    cost = int(job.get("connects_cost", 0))
    ev = amount * 0.1                                 # crude expected value: ~10% win probability
    worth = cost == 0 or (ev / max(cost, 1) >= pol["min_expected_value_per_connect_usd"] and cost <= balance)
    why = (f"{basis}; floor {floor:.0f}. Connects {cost} of {balance} left; expected value per Connect "
           f"${ev / max(cost, 1):.2f} vs minimum ${pol['min_expected_value_per_connect_usd']:.2f}.")
    return PriceQuote(amount_usd=round(amount, 2), rate_type="hourly" if job.get("budget_type") == "hourly" else "fixed",
                      connects_cost=cost, worth_connects=worth, rationale=why)


async def pricing_node(state):
    t0 = time.monotonic()
    bal = await marketplace("pricing").get_connects_balance(state["user_id"])
    balance = int(bal.get("balance", 0)) if isinstance(bal, dict) else 0
    q = quote(state["job"], state.get("job_spec", {}), state.get("profile", {}), balance)
    return update("pricing", t0=t0, price_quote=q.model_dump())
