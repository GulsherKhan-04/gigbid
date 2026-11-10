"""R4/C5: human approval with interrupt(), then an exactly-once submit."""
from __future__ import annotations

import hashlib
import time

from langgraph.config import get_config, get_store
from langgraph.types import interrupt

from agent.handoffs import ApprovalDecision
from agent.marketplace_port import marketplace
from agent.memory.promotion_rules import edit_diff
from agent.memory.store import learn_from_edit
from agent.nodes.common import update


def _payload(state: dict) -> dict:
    d, q = state["proposal_draft"], state.get("price_quote", {})
    return {"user": state["user_id"], "job_id": d["job_id"], "cover_letter": d["cover_letter"],
            "screening_answers": d.get("screening_answers", []), "bid_amount_usd": q.get("amount_usd", 1) or 1,
            "rate_type": q.get("rate_type", "fixed"), "connects_cost": q.get("connects_cost", 0),
            "idempotency_key": idem_key(state)}


def idem_key(state: dict) -> str:
    """Same thread + same approved text -> same key, so a crash-and-retry can never submit twice."""
    d = state["proposal_draft"]
    raw = f"{get_config()['configurable']['thread_id']}|{d['job_id']}|{d['cover_letter']}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def approval_node(state):
    preview = await marketplace("approval").create_proposal_draft(state["user_id"], _payload(state), dry_run=True)
    decision = ApprovalDecision.model_validate(interrupt({
        "kind": "proposal",
        "draft": state["proposal_draft"],
        "evidence": {e["evidence_id"]: e for e in state.get("evidence", [])},
        "risk_report": state.get("risk_report"),
        "fit_report": state.get("fit_report"),
        "price_quote": state.get("price_quote"),
        "critiques": state.get("critiques", []),
        "compliance": state.get("compliance_verdict"),
        "dry_run": preview,
    }))
    if decision.action == "reject":
        return update("approval", approval=decision.model_dump(), status="rejected")
    if decision.action == "edit" and decision.edited_text:
        original = state["proposal_draft"]["cover_letter"]
        learned = await learn_from_edit(get_store(), state["user_id"], original, decision.edited_text)
        draft = {**state["proposal_draft"], "cover_letter": decision.edited_text}
        return update("approval", approval={**decision.model_dump(), "diff": edit_diff(original, decision.edited_text),
                                            "promoted_style_rules": learned},
                      proposal_draft=draft, status="rechecking")
    return update("approval", approval=decision.model_dump(), status="approved")


async def submit_node(state):
    t0 = time.monotonic()
    m, key = marketplace("approval"), idem_key(state)
    trace_id = get_config()["configurable"].get("trace_id")
    draft = await m.create_proposal_draft(state["user_id"], {**_payload(state), "trace_id": trace_id})
    draft_id = (draft.get("result") or {}).get("draft_id") or (draft.get("result") or {}).get("id")
    sub = await m.submit_proposal(state["user_id"], draft_id, key, int(state["price_quote"].get("connects_cost", 0)),
                                  trace_id)
    return update("submit", t0=t0, submission={"draft": draft, "submit": sub, "idempotency_key": key},
                  status="submitted")
