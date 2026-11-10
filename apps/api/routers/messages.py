from fastapi import APIRouter, Depends, HTTPException

from agent.marketplace_port import marketplace
from apps.api import db
from apps.api.auth.security import current_user
from apps.api.runtime import runtime
from apps.api.schemas.models import Approval
from apps.api.streaming import sse

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("")
async def threads(user=Depends(current_user)):
    msgs = await marketplace("api").list_messages(user["id"])
    by_thread: dict[str, list] = {}
    for m in msgs if isinstance(msgs, list) else []:
        by_thread.setdefault(m["thread_id"], []).append(m)
    status = {c["thread_id"]: c for c in db.list_convos(user["id"])}
    return [{"thread_id": t, "messages": ms, "status": (status.get(t) or {}).get("status"),
             "intent": (status.get(t) or {}).get("intent")} for t, ms in by_thread.items()]


@router.post("/{thread_id}/draft")
async def draft_reply(thread_id: str, user=Depends(current_user)):
    runtime.spawn(runtime.run_convo(user, thread_id))
    return {"ok": True}


@router.get("/{thread_id}")
async def thread_state(thread_id: str, user=Depends(current_user)):
    return await runtime.state(f"convo:{user['id']}:{thread_id}", runtime.convo)


@router.post("/{thread_id}/approval")
async def approve_reply(thread_id: str, body: Approval, user=Depends(current_user)):
    s = await runtime.state(f"convo:{user['id']}:{thread_id}", runtime.convo)
    if not s["pending_approval"]:
        raise HTTPException(409, "no reply is waiting for approval")
    runtime.spawn(runtime.run_convo(user, thread_id, resume=body.model_dump()))
    return {"ok": True}


@router.get("/{thread_id}/stream")
def stream(thread_id: str, user=Depends(current_user)):
    return sse(f"convo:{user['id']}:{thread_id}")
