"""Workspace MCP server: free calendar slots, tentative interview holds, email drafts (local mock store).
Swap the store for Google Calendar / Gmail later; the agent only ever sees these MCP tools."""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import uuid
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

mcp = FastMCP("gigbid-workspace")
STORE = Path(__file__).resolve().parents[2] / "data/processed/workspace.json"


def _load() -> dict:
    return json.loads(STORE.read_text()) if STORE.exists() else {"holds": [], "drafts": []}


def _save(d: dict) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(d, indent=1))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
def free_slots(days: int = Field(5, ge=1, le=14), duration_minutes: int = Field(30, ge=15, le=120),
               tz: str = "Asia/Karachi") -> list[str]:
    """Free interview slots on weekdays 10:00-17:00, excluding existing holds."""
    held = {h["start"] for h in _load()["holds"]}
    out, day = [], dt.date.today()
    while len(out) < days * 2:
        day += dt.timedelta(days=1)
        if day.weekday() >= 5:
            continue
        for hour in (11, 15):
            start = dt.datetime.combine(day, dt.time(hour)).isoformat(timespec="minutes")
            if start not in held:
                out.append(f"{start} ({tz}, {duration_minutes} min)")
    return out


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False))
def create_hold(start: str, title: str = Field(max_length=200)) -> dict:
    """Create a tentative calendar hold for a proposed interview slot."""
    d = _load()
    hold = {"id": uuid.uuid4().hex[:8], "start": start.split(" ")[0], "title": title, "status": "tentative"}
    d["holds"].append(hold)
    _save(d)
    return hold


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False))
def create_email_draft(to: str, subject: str = Field(max_length=200), body: str = Field(max_length=5000)) -> dict:
    """Create an email draft (never sends)."""
    d = _load()
    draft = {"id": uuid.uuid4().hex[:8], "to": to, "subject": subject, "body": body}
    d["drafts"].append(draft)
    _save(d)
    return draft


if __name__ == "__main__":
    if "--stdio" in sys.argv:
        mcp.run("stdio")
    else:
        import uvicorn
        from mcp_servers.auth import BearerAuth
        uvicorn.run(BearerAuth(mcp.streamable_http_app(), "WORKSPACE_MCP_TOKEN"), host="0.0.0.0",
                    port=int((os.getenv("PORT") or 8103)))
