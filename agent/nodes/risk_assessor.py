from __future__ import annotations

import json
import time

from agent.guards import find_injections, untrusted
from agent.handoffs import RiskReport
from agent.llm import get_llm
from agent.marketplace_port import marketplace
from agent.nodes.common import job_text, update
from agent.settings import prompt


async def risk_node(state):
    t0, job = time.monotonic(), state["job"]
    history = {}
    if job.get("client_id"):
        history = await marketplace("risk_assessor").get_client_history(state["user_id"], job["client_id"])
    report, usage = await get_llm().structured(
        "risk_assessor", prompt("risk_assessor"),
        untrusted("job_post", job_text(job)) + f"\n\nClient history (from the marketplace API):\n{json.dumps(history)}",
        RiskReport)
    # Deterministic backstops the model cannot talk its way out of.
    hits = find_injections(job.get("description", ""))
    if hits:
        report.injected_instructions = sorted(set(report.injected_instructions + hits))
        report.flags = sorted(set(report.flags) | {"injection"})
    for sig in job.get("warning_signals", []):
        if sig in {"unpaid_work", "free_work"}:
            report.flags = sorted(set(report.flags) | {"free_work"})
        if sig == "off_platform_contact":
            report.flags = sorted(set(report.flags) | {"off_platform"})
    if {"scam", "free_work", "off_platform"} & set(report.flags):
        report.score = max(report.score, 0.8)
    if history and history.get("payment_verified") is False:
        report.flags = sorted(set(report.flags) | {"unverified_payment"})
    return update("risk_assessor", usage, t0, risk_report=report.model_dump())
