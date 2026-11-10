from fastapi import APIRouter, Depends, HTTPException

from apps.api import db
from apps.api.auth.security import current_user
from apps.api.runtime import runtime
from apps.api.schemas.models import Approval

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("")
async def pending(user=Depends(current_user)):
    """Pending approvals are read from the checkpointer, so a page refresh or API restart never loses one."""
    out = []
    for r in db.list_jobs(user["id"]):
        if r["status"] == "awaiting_approval":
            s = await runtime.state(runtime.thread(user["id"], r["job_id"]))
            if s["pending_approval"]:
                out.append({"job_id": r["job_id"], "title": r["title"], "payload": s["pending_approval"][0]})
    return out


@router.post("/{job_id}")
async def decide(job_id: str, body: Approval, user=Depends(current_user)):
    s = await runtime.state(runtime.thread(user["id"], job_id))
    if not s["pending_approval"]:
        raise HTTPException(409, "nothing is waiting for approval on this job")
    if body.action == "reject" and not body.reason:
        raise HTTPException(422, "a reason is required when rejecting")
    db.upsert_job(user["id"], job_id, status="submitting" if body.action == "approve" else "rechecking")
    await runtime.enqueue_bid(user, {"job_id": job_id}, resume=body.model_dump())
    return {"ok": True}
