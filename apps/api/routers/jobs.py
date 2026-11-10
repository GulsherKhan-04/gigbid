from fastapi import APIRouter, Depends, HTTPException

from agent.marketplace_port import marketplace
from agent.mcp_client import ServerDown
from agent.nodes.scout import fingerprint
from apps.api import db
from apps.api.auth.security import current_user
from apps.api.runtime import runtime
from apps.api.schemas.models import JobRow, Outcome
from apps.api.streaming import sse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRow])
def inbox(user=Depends(current_user)):
    return [JobRow(**{k: v for k, v in r.items() if k in JobRow.model_fields}) for r in db.list_jobs(user["id"])]


@router.post("/scout")
async def scout_now(user=Depends(current_user)):
    """Run the saved searches once now (the worker also runs them on a schedule) and analyse new jobs."""
    m, known = marketplace("scout"), {r["job_id"] for r in db.list_jobs(user["id"])}
    seen, queued = set(), []
    try:
        for q in (user.get("profile") or {}).get("saved_searches") or [""]:
            for j in await m.search_jobs(user["id"], q):
                fp = fingerprint(j)
                if j["job_id"] in known or fp in seen:
                    continue
                seen.add(fp)
                known.add(j["job_id"])
                db.upsert_job(user["id"], j["job_id"], title=j.get("title"), status="queued", stage="queued",
                              connects=j.get("connects_cost"))
                await runtime.enqueue_bid(user, j)
                queued.append(j["job_id"])
    except ServerDown as e:
        raise HTTPException(503, f"marketplace unavailable: {e}")
    return {"queued": queued}


@router.get("/{job_id}")
async def detail(job_id: str, user=Depends(current_user)):
    row = db.get_job_row(user["id"], job_id)
    if not row:
        raise HTTPException(404, "job not in your inbox")
    state = await runtime.state(runtime.thread(user["id"], job_id))
    return {"row": row, "state": state}


@router.post("/{job_id}/analyse")
async def analyse(job_id: str, user=Depends(current_user)):
    row = db.get_job_row(user["id"], job_id)
    await runtime.enqueue_bid(user, {"job_id": job_id, "title": (row or {}).get("title", job_id)})
    return {"thread_id": runtime.thread(user["id"], job_id)}


@router.post("/{job_id}/skip")
def skip(job_id: str, user=Depends(current_user)):
    db.upsert_job(user["id"], job_id, status="skipped", stage="skipped", action="skip", reason="skipped by you")
    return {"ok": True}


@router.post("/{job_id}/outcome")
async def outcome(job_id: str, body: Outcome, user=Depends(current_user)):
    """Pipeline events from the marketplace; outcomes feed the outcome memory through its promotion rule."""
    from agent.memory.store import record_outcome
    row = db.get_job_row(user["id"], job_id) or {}
    state = await runtime.state(runtime.thread(user["id"], job_id))
    words = len((state.get("proposal_draft") or {}).get("cover_letter", "").split())
    insight = await record_outcome(runtime.store, user["id"], row.get("category") or "general", job_id,
                                   body.outcome, words)
    db.upsert_job(user["id"], job_id, stage=body.outcome, outcome=body.outcome)
    return {"ok": True, "promoted_insight": insight}


@router.get("/{job_id}/stream")
def stream(job_id: str, user=Depends(current_user)):
    return sse(runtime.thread(user["id"], job_id))
