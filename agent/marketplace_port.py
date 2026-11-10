"""R1: the single marketplace interface. Two adapters, switched by config (marketplace.mode):

* GigSimPort      -> our own Marketplace MCP server, which wraps GigSim
* UpworkLivePort  -> Upwork's official MCP server (OAuth 2.1, Streamable HTTP); writes are drafts only

The graph only ever sees MarketplacePort, so it cannot tell which marketplace it is using.
"""
from __future__ import annotations

import os
from typing import Any, Protocol

from agent.mcp_client import hub
from agent.settings import config


class MarketplacePort(Protocol):
    async def search_jobs(self, user: str, query: str) -> list[dict[str, Any]]: ...
    async def get_job(self, user: str, job_id: str) -> dict[str, Any]: ...
    async def get_client_history(self, user: str, client_id: str) -> dict[str, Any]: ...
    async def get_connects_balance(self, user: str) -> dict[str, Any]: ...
    async def list_messages(self, user: str, thread_id: str | None = None) -> list[dict[str, Any]]: ...
    async def create_proposal_draft(self, user: str, payload: dict[str, Any], dry_run: bool = False) -> dict: ...
    async def submit_proposal(self, user: str, draft_id: str, key: str, connects: int, trace_id: str | None) -> dict: ...
    async def send_message(self, user: str, thread_id: str, text: str, key: str, trace_id: str | None) -> dict: ...


class GigSimPort:
    def __init__(self, agent: str):
        self.agent = agent

    async def search_jobs(self, user, query):
        return await hub().call(self.agent, "marketplace.search_jobs", {"user": user, "query": query})

    async def get_job(self, user, job_id):
        return await hub().call(self.agent, "marketplace.get_job", {"user": user, "job_id": job_id})

    async def get_client_history(self, user, client_id):
        return await hub().call(self.agent, "marketplace.get_client_history", {"user": user, "client_id": client_id})

    async def get_connects_balance(self, user):
        return await hub().call(self.agent, "marketplace.get_connects_balance", {"user": user})

    async def list_messages(self, user, thread_id=None):
        return await hub().call(self.agent, "marketplace.list_messages", {"user": user, "thread_id": thread_id})

    async def create_proposal_draft(self, user, payload, dry_run=False):
        return await hub().call(self.agent, "marketplace.create_proposal_draft",
                                {"p": {**payload, "user": user, "dry_run": dry_run}})

    async def submit_proposal(self, user, draft_id, key, connects, trace_id):
        return await hub().call(self.agent, "marketplace.submit_proposal",
                                {"user": user, "draft_id": draft_id, "idempotency_key": key,
                                 "connects_cost": connects, "trace_id": trace_id})

    async def send_message(self, user, thread_id, text, key, trace_id):
        return await hub().call(self.agent, "marketplace.send_message",
                                {"user": user, "thread_id": thread_id, "text": text, "idempotency_key": key,
                                 "trace_id": trace_id})


# Map our port methods onto Upwork MCP tool names. Check the names with MCP Inspector against
# https://mcp.upwork.com/mcp once you have connected, and edit here (or move to config) if they differ.
UPWORK_TOOLS = {
    "search_jobs": "search_jobs", "get_job": "get_job_details", "get_client_history": "get_client_info",
    "get_connects_balance": "get_connects_balance", "list_messages": "list_messages",
    "create_proposal_draft": "create_proposal_draft", "send_message": "create_message_draft",
}


class UpworkLivePort:
    """Live mode. Reads on a conservative schedule; writes are created as DRAFTS that the user confirms on
    Upwork. No scraping, no browser automation, no cookies."""

    def __init__(self, user_token: str):
        from langchain_mcp_adapters.client import MultiServerMCPClient
        self.client = MultiServerMCPClient({"upwork": {
            "transport": "streamable_http", "url": (os.getenv("UPWORK_MCP_URL") or "https://mcp.upwork.com/mcp"),
            "headers": {"Authorization": f"Bearer {user_token}"}}})

    async def _call(self, method: str, args: dict):
        async with self.client.session("upwork") as s:
            r = await s.call_tool(UPWORK_TOOLS[method], args)
            if r.isError:
                raise RuntimeError(" ".join(getattr(c, "text", "") for c in r.content))
            return r.structuredContent or [getattr(c, "text", "") for c in r.content]

    async def search_jobs(self, user, query):
        return await self._call("search_jobs", {"query": query})

    async def get_job(self, user, job_id):
        return await self._call("get_job", {"job_id": job_id})

    async def get_client_history(self, user, client_id):
        return await self._call("get_client_history", {"client_id": client_id})

    async def get_connects_balance(self, user):
        return await self._call("get_connects_balance", {})

    async def list_messages(self, user, thread_id=None):
        return await self._call("list_messages", {"room_id": thread_id} if thread_id else {})

    async def create_proposal_draft(self, user, payload, dry_run=False):
        if dry_run:
            return {"dry_run": True, "preview": payload}
        return {"dry_run": False, "result": await self._call("create_proposal_draft", {
            "job_id": payload["job_id"], "cover_letter": payload["cover_letter"],
            "bid_amount": payload["bid_amount_usd"]}), "confirm_on_upwork": True}

    async def submit_proposal(self, user, draft_id, key, connects, trace_id):
        # Upwork requires the user to confirm the draft on the platform; GigBid never auto-submits live.
        return {"result": {"draft_id": draft_id, "status": "awaiting_confirmation_on_upwork"}}

    async def send_message(self, user, thread_id, text, key, trace_id):
        return {"result": await self._call("send_message", {"room_id": thread_id, "text": text}),
                "confirm_on_upwork": True}


def marketplace(agent: str, user_token: str | None = None) -> MarketplacePort:
    if config()["marketplace"]["mode"] == "upwork_live":
        if not user_token:
            raise RuntimeError("live mode needs the user's Upwork OAuth token (connect it in Settings)")
        return UpworkLivePort(user_token)
    return GigSimPort(agent)
