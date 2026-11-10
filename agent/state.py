"""Graph state. State (now) is kept apart from the execution trace (audit) and long-term memory (store)."""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


def merge_dicts(left: dict | None, right: dict | None) -> dict:
    return {**(left or {}), **(right or {})}


class BidState(TypedDict, total=False):
    # --- state: what this job needs right now ---
    user_id: str
    persona: str
    profile: dict[str, Any]          # rates, floor, autonomy, weekly Connects budget
    job: dict[str, Any]
    job_spec: dict[str, Any]
    risk_report: dict[str, Any]
    fit_report: dict[str, Any]
    evidence: Annotated[list[dict[str, Any]], operator.add]   # parallel branches append
    decision: dict[str, Any]
    price_quote: dict[str, Any]
    proposal_draft: dict[str, Any]
    critiques: Annotated[list[dict[str, Any]], operator.add]
    compliance_verdict: dict[str, Any]
    approval: dict[str, Any]
    submission: dict[str, Any]
    status: str                       # analysing | skipped | awaiting_approval | submitted | rejected | needs_attention | dead_letter
    # --- execution trace: kept for audit, never promoted to memory ---
    trace: Annotated[list[dict[str, Any]], operator.add]
    usage: Annotated[dict[str, Any], merge_dicts]             # per-node tokens/cost/latency
    steps: Annotated[int, operator.add]
    errors: Annotated[list[str], operator.add]


class ConversationState(TypedDict, total=False):
    user_id: str
    thread_id: str
    client_id: str
    messages: list[dict[str, Any]]
    intent: dict[str, Any]
    reply_draft: dict[str, Any]
    compliance_verdict: dict[str, Any]
    approval: dict[str, Any]
    sent: dict[str, Any]
    status: str
    trace: Annotated[list[dict[str, Any]], operator.add]
    usage: Annotated[dict[str, Any], merge_dicts]
    steps: Annotated[int, operator.add]
    errors: Annotated[list[str], operator.add]
