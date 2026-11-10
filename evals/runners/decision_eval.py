"""Bid/skip F1, scam precision/recall, price-in-band, unsupported claims, latency and cost, running the real
bid graph (stops at the approval interrupt; nothing is submitted).

    python -m evals.runners.decision_eval --limit 30 [--name smoke]
"""
from __future__ import annotations

import argparse
import asyncio
import time
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from agent.graphs.bid_graph import build_bid_graph
from agent.mcp_client import hub
from evals.runners.common import f1, load_dev, mean, pct, save


async def run(limit: int | None, name: str):
    import random
    rows = load_dev()
    random.Random(1).shuffle(rows)            # mixed personas and job kinds, same sample every run
    rows = rows[:limit] if limit else rows
    if not rows:
        raise SystemExit("No dev rows. Put the provided dev set in evals/datasets/<persona>/.")
    g = build_bid_graph(InMemorySaver(), InMemoryStore())
    results = []
    for r in rows:
        t0 = time.monotonic()
        job = {**r["job"], "job_id": r["job"].get("job_id") or uuid.uuid4().hex[:8]}
        s = await g.ainvoke({"user_id": "eval", "persona": r["persona"], "profile": {}, "job": job},
                            {"configurable": {"thread_id": f"eval-{uuid.uuid4().hex}"}})
        usage = s.get("usage", {})
        d = s.get("proposal_draft") or {}
        price = (s.get("price_quote") or {}).get("amount_usd")
        band = r["price_band"]
        results.append({
            "gold": r["action"], "pred": (s.get("decision") or {}).get("action"),
            "scam_gold": r["is_scam"], "scam_pred": bool({"scam", "free_work", "off_platform"} &
                                                          set((s.get("risk_report") or {}).get("flags", []))),
            "in_band": (band[0] <= price <= band[1]) if (price and band) else None,
            "unsupported_before": d.get("unsupported_before"),
            "unsupported_after": 0.0 if d else None,
            "drafted": bool(d), "seconds": time.monotonic() - t0,
            "usd": sum(u.get("usd", 0) for u in usage.values()), "status": s.get("status"),
            "persona": r["persona"], "job_type": r["job_type"],
            "_draft": {"job": job.get("title", ""), "proposal": d.get("cover_letter")} if d else None})
    bid = lambda x: x == "bid"
    tp = sum(bid(x["pred"]) and bid(x["gold"]) for x in results)
    fp = sum(bid(x["pred"]) and not bid(x["gold"]) for x in results)
    fn = sum(not bid(x["pred"]) and bid(x["gold"]) for x in results)
    stp = sum(x["scam_pred"] and x["scam_gold"] for x in results)
    sp, sg = sum(x["scam_pred"] for x in results), sum(x["scam_gold"] for x in results)
    secs, drafts = [x["seconds"] for x in results], [x for x in results if x["drafted"]]
    summary = {"n": len(results), "bid_skip_f1": f1(tp, fp, fn),
               "scam_precision": round(stp / sp, 4) if sp else None, "scam_recall": round(stp / sg, 4) if sg else None,
               "price_in_band": mean(x["in_band"] for x in results if x["in_band"] is not None),
               "unsupported_rate_before_verification": mean(x["unsupported_before"] for x in drafts),
               "p50_s_per_job": pct(secs, .5), "p95_s_per_job": pct(secs, .95),
               "usd_per_job": mean(x["usd"] for x in results), "usd_per_proposal": mean(x["usd"] for x in drafts),
               "dead_letter": sum(x["status"] == "dead_letter" for x in results)}
    print(summary)
    drafts = [x.pop("_draft") for x in results if x.get("_draft")]
    for x in results:
        x.pop("_draft", None)
    save(f"decisions_{name}", {"summary": summary, "rows": results, "drafts": drafts,
                               "dataset": "GigSim-lite substitute dev set"})
    await hub().close()
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--name", default="dev")
    a = ap.parse_args()
    asyncio.run(run(a.limit, a.name))
