"""Marketplace MCP server wrapping GigSim (read + write). Writes take an idempotency key and a dry_run flag;
every call is rate-limited per user and appended to the audit log."""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from agent.settings import config
from mcp_servers.marketplace import ledger

mcp = FastMCP("gigbid-marketplace", instructions="Freelance marketplace tools. Writes are drafts or need an "
              "idempotency key; use dry_run=true to preview exactly what would be sent and what it costs.")
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
DRAFT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True)
SEND = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True)
limiter = ledger.RateLimiter(config()["marketplace"]["max_requests_per_minute"])
_backend = None


def backend():
    global _backend
    if _backend is None:
        if (os.getenv("MARKETPLACE_BACKEND") or "gigsim") == "fixtures":
            from mcp_servers.marketplace.adapters.fixtures import FixtureBackend
            _backend = FixtureBackend()
        else:
            from mcp_servers.marketplace.adapters.gigsim import GigSimBackend
            _backend = GigSimBackend()
    return _backend


async def _run(user: str, tool: str, args: dict, call, trace_id: str | None = None):
    await asyncio.sleep(limiter.acquire(user))
    try:
        result = await call
    except Exception as e:
        ledger.audit(user, tool, args, {"error": str(e)}, trace_id)
        raise
    ledger.audit(user, tool, args, result, trace_id)
    return result


class ProposalInput(BaseModel):
    user: str = Field(min_length=1, max_length=64)
    job_id: str = Field(min_length=1, max_length=64)
    cover_letter: str = Field(min_length=50, max_length=5000)
    screening_answers: list[str] = Field(default_factory=list, max_length=10)
    bid_amount_usd: float = Field(gt=0, le=100000)
    rate_type: str = Field("fixed", pattern="^(fixed|hourly)$")
    connects_cost: int = Field(ge=0, le=50)
    idempotency_key: str = Field(min_length=8, max_length=128)
    dry_run: bool = False
    trace_id: str | None = None


class WriteResult(BaseModel):
    dry_run: bool
    preview: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    replayed: bool = False


@mcp.tool(annotations=READ)
async def search_jobs(user: str, query: str = Field("", max_length=200), limit: int = Field(20, ge=1, le=50)) -> list[dict]:
    """Search open jobs by keywords."""
    return await _run(user, "search_jobs", {"query": query}, backend().search_jobs(query, limit))


@mcp.tool(annotations=READ)
async def get_job(user: str, job_id: str) -> dict:
    """Full job post including budget, screening questions and Connects cost."""
    return await _run(user, "get_job", {"job_id": job_id}, backend().get_job(job_id))


@mcp.tool(annotations=READ)
async def get_client_history(user: str, client_id: str) -> dict:
    """Client's hiring history: spend, hires, rating, payment verification."""
    return await _run(user, "get_client_history", {"client_id": client_id}, backend().get_client_history(client_id))


@mcp.tool(annotations=READ)
async def get_connects_balance(user: str) -> dict:
    """The freelancer's remaining Connects."""
    return await _run(user, "get_connects_balance", {}, backend().get_connects_balance(user))


@mcp.tool(annotations=READ)
async def list_messages(user: str, thread_id: str | None = None) -> list[dict]:
    """Client conversation messages, optionally for one thread."""
    return await _run(user, "list_messages", {"thread_id": thread_id}, backend().list_messages(user, thread_id))


@mcp.tool(annotations=DRAFT, structured_output=True)
async def create_proposal_draft(p: ProposalInput) -> WriteResult:
    """Create a proposal DRAFT. dry_run=true returns exactly what would be sent and its Connects cost."""
    preview = p.model_dump(exclude={"dry_run", "trace_id"})
    if p.dry_run:
        return WriteResult(dry_run=True, preview=preview)
    key = f"draft:{p.user}:{p.idempotency_key}"
    if (prev := ledger.seen(key)) is not None:
        return WriteResult(dry_run=False, preview=preview, result=prev, replayed=True)
    res = await _run(p.user, "create_proposal_draft", preview, backend().create_proposal_draft(p.user, preview),
                     p.trace_id)
    ledger.remember(key, res)
    return WriteResult(dry_run=False, preview=preview, result=res)


@mcp.tool(annotations=SEND, structured_output=True)
async def submit_proposal(user: str, draft_id: str, idempotency_key: str = Field(min_length=8),
                          connects_cost: int = Field(0, ge=0, le=50), dry_run: bool = False,
                          trace_id: str | None = None) -> WriteResult:
    """Submit an approved draft and spend its Connects. Retrying with the same key never submits twice."""
    preview = {"draft_id": draft_id, "connects_cost": connects_cost}
    if dry_run:
        return WriteResult(dry_run=True, preview=preview)
    key = f"submit:{user}:{idempotency_key}"
    if (prev := ledger.seen(key)) is not None:
        return WriteResult(dry_run=False, preview=preview, result=prev, replayed=True)
    res = await _run(user, "submit_proposal", preview, backend().submit_proposal(user, draft_id), trace_id)
    ledger.remember(key, res)
    return WriteResult(dry_run=False, preview=preview, result=res)


@mcp.tool(annotations=SEND, structured_output=True)
async def send_message(user: str, thread_id: str, text: str = Field(min_length=1, max_length=4000),
                       idempotency_key: str = Field(min_length=8), dry_run: bool = False,
                       trace_id: str | None = None) -> WriteResult:
    """Send an approved message to a client thread."""
    preview = {"thread_id": thread_id, "text": text}
    if dry_run:
        return WriteResult(dry_run=True, preview=preview)
    key = f"msg:{user}:{idempotency_key}"
    if (prev := ledger.seen(key)) is not None:
        return WriteResult(dry_run=False, preview=preview, result=prev, replayed=True)
    res = await _run(user, "send_message", preview, backend().send_message(user, thread_id, text), trace_id)
    ledger.remember(key, res)
    return WriteResult(dry_run=False, preview=preview, result=res)


if __name__ == "__main__":
    if "--stdio" in sys.argv:
        mcp.run("stdio")
    else:
        import uvicorn
        from mcp_servers.auth import BearerAuth
        uvicorn.run(BearerAuth(mcp.streamable_http_app(), "MARKETPLACE_MCP_TOKEN"), host="0.0.0.0",
                    port=int((os.getenv("PORT") or 8102)))
