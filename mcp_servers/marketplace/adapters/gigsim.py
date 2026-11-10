"""GigSim REST adapter. The instructor's simulator is the source of truth: check its API docs and adjust
ENDPOINTS below if a path differs. Retries 429/5xx with backoff and never re-sends a write without the
idempotency key."""
from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

from mcp_servers.marketplace.adapters.base import BackendUnavailable

ENDPOINTS = {
    "search_jobs": ("GET", "/jobs"),
    "get_job": ("GET", "/jobs/{job_id}"),
    "client_history": ("GET", "/clients/{client_id}"),
    "connects": ("GET", "/freelancers/{user}/connects"),
    "messages": ("GET", "/freelancers/{user}/messages"),
    "create_draft": ("POST", "/proposals"),
    "submit": ("POST", "/proposals/{draft_id}/submit"),
    "send_message": ("POST", "/threads/{thread_id}/messages"),
}


class GigSimBackend:
    def __init__(self):
        self.base = (os.getenv("GIGSIM_BASE_URL") or "http://localhost:8081").rstrip("/")
        token = os.getenv("GIGSIM_API_TOKEN")
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    async def _call(self, name: str, idem: str | None = None, params=None, json=None, **path) -> Any:
        method, tpl = ENDPOINTS[name]
        headers = {**self.headers, **({"Idempotency-Key": idem} if idem else {})}
        for attempt in range(4):
            try:
                async with httpx.AsyncClient(timeout=20) as c:
                    r = await c.request(method, self.base + tpl.format(**path), params=params, json=json,
                                        headers=headers)
            except httpx.HTTPError as e:
                if attempt == 3:
                    raise BackendUnavailable(f"GigSim unreachable: {e}") from e
                await asyncio.sleep(2 ** attempt)
                continue
            if r.status_code == 429 or r.status_code >= 500:
                if attempt == 3:
                    raise BackendUnavailable(f"GigSim {r.status_code}")
                await asyncio.sleep(float(r.headers.get("Retry-After", 2 ** attempt)))
                continue
            r.raise_for_status()
            return r.json()

    async def search_jobs(self, query, limit):
        data = await self._call("search_jobs", params={"q": query, "limit": limit})
        return data.get("jobs", data) if isinstance(data, dict) else data

    async def get_job(self, job_id):
        return await self._call("get_job", job_id=job_id)

    async def get_client_history(self, client_id):
        return await self._call("client_history", client_id=client_id)

    async def get_connects_balance(self, user):
        return await self._call("connects", user=user)

    async def list_messages(self, user, thread_id):
        return await self._call("messages", user=user, params={"thread_id": thread_id} if thread_id else None)

    async def create_proposal_draft(self, user, payload):
        return await self._call("create_draft", idem=payload["idempotency_key"], json={**payload, "freelancer": user})

    async def submit_proposal(self, user, draft_id):
        return await self._call("submit", idem=f"submit-{draft_id}", draft_id=draft_id)

    async def send_message(self, user, thread_id, text):
        return await self._call("send_message", thread_id=thread_id, json={"text": text, "from": user})
