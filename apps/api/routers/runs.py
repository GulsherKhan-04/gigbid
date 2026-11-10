from fastapi import APIRouter, Depends

from apps.api.auth.security import current_user
from apps.api.runtime import runtime

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("/{job_id}/history")
async def history(job_id: str, user=Depends(current_user)):
    """Checkpoint history: every step of the run, replayable from any checkpoint (C6)."""
    cfg = {"configurable": {"thread_id": runtime.thread(user["id"], job_id)}}
    out = []
    async for snap in runtime.bid.aget_state_history(cfg):
        out.append({"checkpoint_id": snap.config["configurable"]["checkpoint_id"], "next": list(snap.next),
                    "status": snap.values.get("status"), "steps": snap.values.get("steps"),
                    "created_at": snap.created_at})
    return out


@router.get("/{job_id}/trace")
async def trace(job_id: str, user=Depends(current_user)):
    s = await runtime.state(runtime.thread(user["id"], job_id))
    return {"trace": s.get("trace", []), "usage": s.get("usage", {}), "errors": s.get("errors", [])}


@router.post("/{job_id}/replay/{checkpoint_id}")
async def replay(job_id: str, checkpoint_id: str, user=Depends(current_user)):
    cfg = runtime.cfg(runtime.thread(user["id"], job_id))
    cfg["configurable"]["checkpoint_id"] = checkpoint_id
    runtime.spawn(runtime._stream(runtime.bid, None, cfg, runtime.thread(user["id"], job_id)))
    return {"ok": True}
