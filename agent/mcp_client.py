"""MCP client setup. Agents reach every capability through MCP; each agent gets only its allowlisted tools.

Transport: stdio (spawns servers locally, default for dev/tests) or http (docker compose / deployment).
Timeouts, bounded retries with backoff, and a clear degraded signal when a server is down (A6).
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

ALLOWLIST: dict[str, set[str]] = {
    "scout": {"marketplace.search_jobs", "marketplace.get_job"},
    "risk_assessor": {"marketplace.get_client_history"},
    "fit_matcher": {"portfolio.search_evidence", "portfolio.list_skills"},
    "pricing": {"marketplace.get_connects_balance"},
    "writer": {"portfolio.search_evidence", "portfolio.get_case_study"},
    "critic": {"portfolio.get_case_study"},
    "client_liaison": {"marketplace.list_messages", "workspace.free_slots", "workspace.create_hold",
                       "workspace.create_email_draft"},
    "approval": {"marketplace.create_proposal_draft", "marketplace.submit_proposal", "marketplace.send_message"},
    "api": {"marketplace.search_jobs", "marketplace.get_job", "marketplace.get_connects_balance",
            "marketplace.list_messages", "portfolio.list_skills", "portfolio.search_evidence"},
}


class ServerDown(RuntimeError):
    def __init__(self, server: str, detail: str):
        super().__init__(f"{server} MCP server unavailable: {detail}")
        self.server = server


class ToolNotAllowed(PermissionError):
    pass


def connections() -> dict[str, dict]:
    if (os.getenv("MCP_TRANSPORT") or "stdio") == "http":
        def http(name: str, default: str, token: str) -> dict:
            return {"transport": "streamable_http", "url": os.getenv(f"{name.upper()}_MCP_URL", default),
                    "headers": {"Authorization": f"Bearer {os.getenv(token, '')}"}}
        return {"portfolio": http("portfolio", "http://portfolio-mcp:8101/mcp", "PORTFOLIO_MCP_TOKEN"),
                "marketplace": http("marketplace", "http://marketplace-mcp:8102/mcp", "MARKETPLACE_MCP_TOKEN"),
                "workspace": http("workspace", "http://workspace-mcp:8103/mcp", "WORKSPACE_MCP_TOKEN")}
    env = {**os.environ}
    return {name: {"transport": "stdio", "command": sys.executable,
                   "args": ["-m", f"mcp_servers.{name}.server", "--stdio"], "env": env}
            for name in ("portfolio", "marketplace", "workspace")}


class ToolHub:
    def __init__(self, timeout: float = 30, retries: int = 2):
        self.client = MultiServerMCPClient(connections())
        self.timeout, self.retries = timeout, retries
        self.sessions: dict[str, Any] = {}
        self.owners: dict[str, tuple[asyncio.Task, asyncio.Event]] = {}
        self.lock = asyncio.Lock()

    async def _own(self, server: str, ready: asyncio.Future, stop: asyncio.Event):
        # One long-lived task owns each session, so it is entered and exited in the same task (anyio rule).
        try:
            async with self.client.session(server) as s:
                ready.set_result(s)
                await stop.wait()
        except Exception as e:  # noqa: BLE001
            if not ready.done():
                ready.set_exception(e)

    async def _session(self, server: str):
        async with self.lock:
            if server not in self.sessions:
                ready, stop = asyncio.get_running_loop().create_future(), asyncio.Event()
                task = asyncio.create_task(self._own(server, ready, stop))
                self.sessions[server] = await asyncio.wait_for(ready, 30)
                self.owners[server] = (task, stop)
            return self.sessions[server]

    def _drop(self, server: str):
        self.sessions.pop(server, None)
        owner = self.owners.pop(server, None)
        if owner:
            owner[1].set()

    async def call(self, agent: str, qualified: str, args: dict) -> Any:
        if qualified not in ALLOWLIST.get(agent, set()):
            raise ToolNotAllowed(f"{agent} may not call {qualified}")
        server, tool = qualified.split(".", 1)
        last = None
        for attempt in range(self.retries + 1):
            try:
                session = await self._session(server)
                res = await asyncio.wait_for(session.call_tool(tool, args), self.timeout)
                if res.isError:
                    text = " ".join(getattr(c, "text", "") for c in res.content)
                    raise RuntimeError(f"{qualified} failed: {text[:300]}")
                if res.structuredContent is not None:
                    sc = res.structuredContent
                    return sc.get("result", sc) if isinstance(sc, dict) and set(sc) == {"result"} else sc
                texts = [getattr(c, "text", "") for c in res.content]
                parsed = [_maybe_json(t) for t in texts]
                return parsed[0] if len(parsed) == 1 else parsed
            except RuntimeError:
                raise
            except Exception as e:      # transport errors -> reconnect with backoff
                last = e
                self._drop(server)
                await asyncio.sleep(min(8, 2 ** attempt))
        raise ServerDown(server, str(last))

    async def health(self) -> dict[str, bool]:
        out = {}
        for server in ("portfolio", "marketplace", "workspace"):
            try:
                s = await self._session(server)
                await asyncio.wait_for(s.list_tools(), 5)
                out[server] = True
            except Exception:
                self._drop(server)
                out[server] = False
        return out

    async def close(self):
        tasks = [t for t, _ in self.owners.values()]
        for server in list(self.owners):
            self._drop(server)
        for t in tasks:
            try:
                await asyncio.wait_for(t, 10)
            except Exception:  # noqa: BLE001
                t.cancel()


def _maybe_json(t: str) -> Any:
    try:
        return json.loads(t)
    except (json.JSONDecodeError, TypeError):
        return t


_hub: ToolHub | None = None


def hub() -> ToolHub:
    global _hub
    if _hub is None:
        _hub = ToolHub()
    return _hub
