"""Bid / watch / skip, from typed reports and config thresholds only (no free-text parsing)."""
from __future__ import annotations

from agent.handoffs import BidDecision
from agent.nodes.common import update
from agent.settings import config


def decide(risk: dict, fit: dict) -> BidDecision:
    t = config()["thresholds"]
    flags = set(risk.get("flags", []))
    if flags & {"scam", "free_work", "off_platform"}:
        names = {"scam": "looks like a scam", "free_work": "asks for free work", "off_platform": "asks to move off the platform"}
        return BidDecision(action="skip", reason="Skipped: " + ", ".join(names[f] for f in sorted(flags & set(names))))
    if risk.get("score", 0) > t["maximum_risk_score"]:
        return BidDecision(action="skip", reason=f"Skipped: risk {risk['score']:.0%} is above your limit of {t['maximum_risk_score']:.0%}")
    score = fit.get("score", 0)
    if score >= t["minimum_fit_score"]:
        return BidDecision(action="bid", reason=f"Bid: {score:.0%} fit and {risk.get('score', 0):.0%} risk")
    if score >= t["watch_fit_score"]:
        return BidDecision(action="watch", reason=f"Watch: {score:.0%} fit is borderline")
    return BidDecision(action="skip", reason=f"Skipped: {score:.0%} fit is below {t['watch_fit_score']:.0%}")


async def decision_node(state):
    if state.get("status") in {"dead_letter", "marketplace_unavailable"}:
        return {"steps": 1}
    d = decide(state.get("risk_report", {}), state.get("fit_report", {}))
    status = "analysing" if d.action == "bid" else ("skipped" if d.action == "skip" else "watching")
    return update("decision", decision=d.model_dump(), status=status)
