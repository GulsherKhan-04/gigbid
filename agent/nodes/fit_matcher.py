from __future__ import annotations

import re
import time

from agent.handoffs import FitReport
from agent.llm import get_llm
from agent.mcp_client import hub
from agent.nodes.common import update
from agent.settings import config, prompt


def quick_requirements(job: dict) -> list[str]:
    """Runs in parallel with the Analyst, so it derives its own requirement list without waiting."""
    reqs = list(job.get("required_skills", []))
    for s in re.split(r"(?<=[.;])\s+", job.get("description", "")):
        if any(w in s.lower() for w in ("build", "create", "compare", "report", "deploy", "need", "must",
                                        "experience", "document", "integrate", "analy")):
            reqs.append(s.strip()[:160])
    return reqs[:8] or [job.get("title", "")]


async def fit_node(state):
    t0, job = time.monotonic(), state["job"]
    reqs = quick_requirements(job)
    evidence = await hub().call("fit_matcher", "portfolio.search_evidence", {
        "requirement": f"{job.get('title', '')}. {job.get('description', '')}"[:480],
        "requirements": reqs, "k": config()["rag"]["k"], "persona": state.get("persona")})
    evidence = evidence if isinstance(evidence, list) else []
    listing = "\n".join(f"[{e['evidence_id']}] ({e['type']}, {e.get('outcome') or 'n/a'}) {e['text'][:500]}"
                        for e in evidence) or "(no evidence found)"
    report, usage = await get_llm().structured(
        "fit_matcher", prompt("fit_matcher"),
        f"Requirements:\n" + "\n".join(f"- {r}" for r in reqs) + f"\n\nEvidence:\n{listing}", FitReport)
    known = {e["evidence_id"] for e in evidence}
    for row in report.matrix:
        row.evidence_ids = [i for i in row.evidence_ids if i in known]
        if not row.evidence_ids:
            row.strength = "none"
    if not evidence:
        report.score = 0.0
    return update("fit_matcher", usage, t0, fit_report=report.model_dump(), evidence=evidence)
