from __future__ import annotations

import time
from typing import Any

from agent.guards import mask_pii


def job_text(job: dict) -> str:
    b = job.get("budget") or {}
    return (f"Title: {job.get('title', '')}\nBudget: {b.get('min')}-{b.get('max')} {b.get('currency', 'USD')}"
            f" ({job.get('budget_type', b.get('type', 'fixed'))})\nDuration: {job.get('duration_days', '?')} days\n"
            f"Skills: {', '.join(job.get('required_skills', []))}\n\n{job.get('description', '')}\n\n"
            f"Screening questions: {job.get('screening_questions', [])}")


def update(node: str, usage: dict | None = None, t0: float | None = None, **fields: Any) -> dict:
    """Every node returns its fields plus a trace entry, its usage, and one step."""
    u = dict(usage or {})
    if t0 is not None:
        u["seconds"] = round(time.monotonic() - t0, 3)
    entry = {"node": node, "at": time.time(), **{k: v for k, v in u.items()},
             "summary": mask_pii(str({k: v for k, v in fields.items() if k not in ("evidence",)})[:600])}
    prev = fields.pop("_usage_key", node)
    return {**fields, "trace": [entry], "usage": {prev: u}, "steps": 1}


def add_usage(a: dict, b: dict) -> dict:
    if not a:
        return dict(b)
    return {**b, "prompt_tokens": a.get("prompt_tokens", 0) + b.get("prompt_tokens", 0),
            "completion_tokens": a.get("completion_tokens", 0) + b.get("completion_tokens", 0),
            "usd": round(a.get("usd", 0) + b.get("usd", 0), 6),
            "seconds": round(a.get("seconds", 0) + b.get("seconds", 0), 3)}
