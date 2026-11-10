"""Bid graph (one thread per job). Hand-written StateGraph:

scout -> Send(analyst | risk_assessor | fit_matcher) in parallel -> decision -> pricing -> writer -> verifier
-> critic (back to writer at most `max_revisions` times) -> compliance -> approval (interrupt) -> submit
"""
from __future__ import annotations

import traceback
from typing import Any, Awaitable, Callable

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from agent.mcp_client import ServerDown
from agent.nodes.analyst import analyst_node
from agent.nodes.approval import approval_node, submit_node
from agent.nodes.compliance import compliance_node
from agent.nodes.critic import critic_node
from agent.nodes.decision import decision_node
from agent.nodes.fit_matcher import fit_node
from agent.nodes.pricing import pricing_node
from agent.nodes.risk_assessor import risk_node
from agent.nodes.scout import scout_node
from agent.nodes.verifier import verifier_node
from agent.nodes.writer import writer_node
from agent.settings import config
from agent.state import BidState


def guarded(name: str, fn: Callable[[dict], Awaitable[dict]], attempts: int = 2):
    """Per-node retries; marketplace outages become a visible queued state; other failures go to dead letter."""
    async def run(state: dict) -> dict:
        last = ""
        for _ in range(attempts):
            try:
                return await fn(state)
            except ServerDown as e:
                return {"status": "marketplace_unavailable", "errors": [f"{name}: {e}"], "steps": 1}
            except Exception as e:                       # noqa: BLE001
                if type(e).__name__ == "GraphInterrupt" or "Interrupt" in type(e).__name__:
                    raise
                last = f"{name}: {type(e).__name__}: {e}"
                traceback.print_exc()
        return {"status": "dead_letter", "errors": [last], "steps": 1}
    run.__name__ = name
    return run


def over_budget(state: dict) -> bool:
    b = config()["budgets"]
    tokens = sum(u.get("prompt_tokens", 0) + u.get("completion_tokens", 0) for u in state.get("usage", {}).values())
    return state.get("steps", 0) > b["max_graph_steps"] or tokens > b["max_tokens_per_job"]


def halted(state: dict) -> bool:
    return state.get("status") in {"dead_letter", "marketplace_unavailable", "needs_attention"}


def fan_out(state: dict) -> list[Send] | str:
    if halted(state):
        return END
    return [Send("analyst", state), Send("risk_assessor", state), Send("fit_matcher", state)]


def after_decision(state: dict) -> str:
    if halted(state):
        return END
    return "pricing" if state["decision"]["action"] == "bid" else END


def after_pricing(state: dict) -> str:
    if halted(state):
        return END
    return "writer" if state["price_quote"]["worth_connects"] else "not_worth"


async def not_worth(state):
    return {"decision": {"action": "skip", "reason": "Connects cost not justified: " + state["price_quote"]["rationale"]},
            "status": "skipped", "steps": 1}


def after_critic(state: dict) -> str:
    if halted(state):
        return END
    if over_budget(state):
        return "needs_attention"
    passed = state["critiques"][-1]["passed"]
    if passed or state["proposal_draft"].get("revision", 0) >= config()["budgets"]["max_revisions"]:
        return "compliance"
    return "writer"


def after_compliance(state: dict) -> str:
    if halted(state):
        return END
    return "approval" if state["status"] == "awaiting_approval" else END


def after_approval(state: dict) -> str:
    return {"approved": "submit", "rechecking": "compliance"}.get(state["status"], END)


async def needs_attention(state):
    return {"status": "needs_attention", "errors": ["step or token budget exceeded"], "steps": 1}


def build_bid_graph(checkpointer=None, store=None):
    g = StateGraph(BidState)
    for name, fn in [("scout", scout_node), ("analyst", analyst_node), ("risk_assessor", risk_node),
                     ("fit_matcher", fit_node), ("decision", decision_node), ("pricing", pricing_node),
                     ("writer", writer_node), ("verifier", verifier_node), ("critic", critic_node),
                     ("compliance", compliance_node), ("submit", submit_node)]:
        g.add_node(name, guarded(name, fn))
    g.add_node("approval", approval_node)          # not wrapped: interrupt() must propagate
    g.add_node("not_worth", not_worth)
    g.add_node("needs_attention", needs_attention)

    g.add_edge(START, "scout")
    g.add_conditional_edges("scout", fan_out, ["analyst", "risk_assessor", "fit_matcher", END])
    for n in ("analyst", "risk_assessor", "fit_matcher"):
        g.add_edge(n, "decision")
    g.add_conditional_edges("decision", after_decision, ["pricing", END])
    g.add_conditional_edges("pricing", after_pricing, ["writer", "not_worth", END])
    g.add_edge("not_worth", END)
    g.add_edge("writer", "verifier")
    g.add_edge("verifier", "critic")
    g.add_conditional_edges("critic", after_critic, ["writer", "compliance", "needs_attention", END])
    g.add_conditional_edges("compliance", after_compliance, ["approval", END])
    g.add_conditional_edges("approval", after_approval, ["submit", "compliance", END])
    g.add_edge("submit", END)
    g.add_edge("needs_attention", END)
    return g.compile(checkpointer=checkpointer, store=store)
