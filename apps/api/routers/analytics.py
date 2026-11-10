import statistics

from fastapi import APIRouter, Depends

from apps.api import db
from apps.api.auth.security import current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
GOOD = {"replied", "interview", "hired"}


@router.get("")
def analytics(user=Depends(current_user)):
    rows = db.list_jobs(user["id"])
    sent = [r for r in rows if r["stage"] in {"submitted", "viewed", "replied", "interview", "hired", "lost"}]
    by_cat: dict[str, dict] = {}
    for r in sent:
        c = by_cat.setdefault(r["category"] or "general", {"sent": 0, "replied": 0, "hired": 0, "connects": 0})
        c["sent"] += 1
        c["replied"] += r["stage"] in GOOD
        c["hired"] += r["stage"] == "hired"
        c["connects"] += r["connects"] or 0
    secs = sorted(r["seconds"] for r in rows if r["seconds"])
    costs = [r["cost_usd"] for r in rows if r["cost_usd"] is not None]
    reasons: dict[str, int] = {}
    for r in rows:
        if r["action"] == "skip" and r["reason"]:
            key = r["reason"].removeprefix("Skipped: ").split(",")[0].split(" is ")[0]
            reasons[key] = reasons.get(key, 0) + 1
    return {
        "jobs_analysed": len(rows), "proposals_sent": len(sent), "by_category": by_cat,
        "connects_spent": sum(r["connects"] or 0 for r in sent),
        "p50_seconds": statistics.median(secs) if secs else None,
        "p95_seconds": secs[int(0.95 * (len(secs) - 1))] if secs else None,
        "avg_cost_usd": round(sum(costs) / len(costs), 5) if costs else None,
        "skip_reasons": reasons,
    }
