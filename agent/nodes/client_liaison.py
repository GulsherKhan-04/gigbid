from __future__ import annotations

import hashlib
import json
import time

from langgraph.config import get_config
from langgraph.types import interrupt
from pydantic import BaseModel

from agent.guards import find_injections, untrusted
from agent.handoffs import ApprovalDecision, ClientIntent
from agent.llm import get_llm
from agent.marketplace_port import marketplace
from agent.mcp_client import hub
from agent.nodes.common import update
from agent.nodes.compliance import check
from agent.settings import prompt


class LiaisonOut(BaseModel):
    intent: ClientIntent
    reply: str


async def liaison_node(state):
    t0, user = time.monotonic(), state["user_id"]
    msgs = state.get("messages") or await marketplace("client_liaison").list_messages(user, state["thread_id"])
    last_client = next((m["text"] for m in reversed(msgs) if m.get("from") != user), "")
    slots = await hub().call("client_liaison", "workspace.free_slots", {"days": 3})
    convo = "\n".join(f"{'ME' if m.get('from') == user else 'CLIENT'}: {m['text']}" for m in msgs[-12:])
    out, usage = await get_llm().structured(
        "client_liaison", prompt("client_liaison"),
        untrusted("client_conversation", convo) + f"\n\nAvailable interview slots: {json.dumps(slots)}", LiaisonOut)
    if find_injections(last_client):
        out.intent.intent = "scam_signal"
    proposed = slots[:3] if out.intent.intent == "interview_request" else []
    verdict, u2 = await check(out.reply)
    return update("client_liaison", {**usage, "usd": usage.get("usd", 0) + u2.get("usd", 0)}, t0, messages=msgs,
                  intent=out.intent.model_dump(), compliance_verdict=verdict.model_dump(),
                  reply_draft={"thread_id": state["thread_id"], "text": verdict.cleaned_text, "proposed_slots": proposed},
                  status="awaiting_approval" if verdict.allowed else "blocked")


async def reply_approval_node(state):
    d = ApprovalDecision.model_validate(interrupt({"kind": "message", "reply": state["reply_draft"],
                                                   "intent": state["intent"],
                                                   "compliance": state["compliance_verdict"]}))
    if d.action == "reject":
        return {"approval": d.model_dump(), "status": "rejected", "steps": 1}
    text = d.edited_text if d.action == "edit" and d.edited_text else state["reply_draft"]["text"]
    if d.action == "edit":
        verdict, _ = await check(text)
        if not verdict.allowed:
            return {"approval": d.model_dump(), "compliance_verdict": verdict.model_dump(), "status": "blocked",
                    "steps": 1}
        text = verdict.cleaned_text
    return {"approval": d.model_dump(), "reply_draft": {**state["reply_draft"], "text": text}, "status": "approved",
            "steps": 1}


async def send_node(state):
    cfg = get_config()["configurable"]
    key = hashlib.sha256(f"{cfg['thread_id']}|{state['reply_draft']['text']}".encode()).hexdigest()[:32]
    res = await marketplace("approval").send_message(state["user_id"], state["thread_id"],
                                                     state["reply_draft"]["text"], key, cfg.get("trace_id"))
    for slot in state["reply_draft"].get("proposed_slots", []):
        await hub().call("client_liaison", "workspace.create_hold", {"start": slot, "title": "Client interview (tentative)"})
    return update("send", sent=res, status="sent")
