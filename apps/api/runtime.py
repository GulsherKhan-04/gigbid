"""Shared runtime used by the API and the worker: persistence, graphs, run execution and the event bus."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import uuid
from contextlib import AsyncExitStack
from typing import Any

from langgraph.types import Command

from agent.graphs.bid_graph import build_bid_graph
from agent.graphs.conversation_graph import build_conversation_graph
from agent.guards import mask_obj
from apps.api import db


class EventBus:
    """Redis pub/sub when REDIS_URL is reachable (worker and API in different processes); in-process otherwise."""

    def __init__(self):
        self.local: dict[str, list[asyncio.Queue]] = {}
        self.redis = None

    async def connect(self):
        url = os.getenv("REDIS_URL")
        if url:
            try:
                import redis.asyncio as aioredis
                r = aioredis.from_url(url)
                await asyncio.wait_for(r.ping(), 2)
                self.redis = r
            except Exception:  # noqa: BLE001
                self.redis = None

    async def publish(self, channel: str, event: dict):
        event = mask_obj(json.loads(json.dumps(event, default=str)))
        if self.redis:
            await self.redis.publish(f"gigbid:{channel}", json.dumps(event))
        for q in self.local.get(channel, []):
            q.put_nowait(event)

    async def subscribe(self, channel: str):
        if self.redis:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(f"gigbid:{channel}")
            try:
                async for msg in pubsub.listen():
                    if msg["type"] == "message":
                        yield json.loads(msg["data"])
            finally:
                await pubsub.unsubscribe()
        else:
            q: asyncio.Queue = asyncio.Queue()
            self.local.setdefault(channel, []).append(q)
            try:
                while True:
                    yield await q.get()
            finally:
                self.local[channel].remove(q)


class Runtime:
    def __init__(self):
        self.stack = AsyncExitStack()
        self.bus = EventBus()
        self.bid = self.convo = self.store = self.checkpointer = None
        self.tasks: set[asyncio.Task] = set()

    async def start(self):
        url = (os.getenv("DATABASE_URL") or "")
        if url.startswith("postgres"):
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from langgraph.store.postgres.aio import AsyncPostgresStore
            raw = url.replace("+psycopg", "")
            self.checkpointer = await self.stack.enter_async_context(AsyncPostgresSaver.from_conn_string(raw))
            self.store = await self.stack.enter_async_context(AsyncPostgresStore.from_conn_string(raw))
            await self.checkpointer.setup()
            await self.store.setup()
        else:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
            from langgraph.store.sqlite.aio import AsyncSqliteStore
            path = str(db.ROOT / "data/processed/graph.db")
            self.checkpointer = await self.stack.enter_async_context(AsyncSqliteSaver.from_conn_string(path))
            self.store = await self.stack.enter_async_context(AsyncSqliteStore.from_conn_string(path))
            await self.store.setup()
        self.bid = build_bid_graph(self.checkpointer, self.store)
        self.convo = build_conversation_graph(self.checkpointer, self.store)
        await self.bus.connect()

    async def stop(self):
        from agent.mcp_client import hub
        await hub().close()
        await self.stack.aclose()

    # ---------- bid runs ----------
    @staticmethod
    def thread(user_id: str, job_id: str) -> str:
        return f"bid:{user_id}:{job_id}"

    def cfg(self, thread_id: str, trace_id: str | None = None) -> dict:
        trace_id = trace_id or uuid.uuid4().hex
        return {"configurable": {"thread_id": thread_id, "trace_id": trace_id},
                "metadata": {"trace_id": trace_id}, "run_name": thread_id, "recursion_limit": 60}

    async def run_bid(self, user: dict, job: dict, resume: dict | None = None, trace_id: str | None = None):
        thread_id = self.thread(user["id"], job["job_id"])
        cfg = self.cfg(thread_id, trace_id)
        if resume is None:
            inp: Any = {"user_id": user["id"], "persona": user["persona"], "profile": user.get("profile") or {},
                        "job": job}
            db.upsert_job(user["id"], job["job_id"], thread_id=thread_id, title=job.get("title", job["job_id"]),
                          status="analysing", stage="analysing")
        else:
            inp = Command(resume=resume)
        await self._stream(self.bid, inp, cfg, channel=thread_id)
        await self.sync_job(user["id"], job["job_id"])

    async def _stream(self, graph, inp, cfg, channel: str):
        t0 = time.monotonic()
        await self.bus.publish(channel, {"type": "run_started", "trace_id": cfg["configurable"]["trace_id"]})
        try:
            async for mode, chunk in graph.astream(inp, cfg, stream_mode=["updates"]):
                for node, upd in (chunk or {}).items():
                    if node == "__interrupt__":
                        await self.bus.publish(channel, {"type": "interrupt"})
                        continue
                    upd = upd or {}
                    await self.bus.publish(channel, {"type": "node", "node": node, "status": upd.get("status"),
                                                     "trace": (upd.get("trace") or [{}])[-1],
                                                     "elapsed": round(time.monotonic() - t0, 2)})
        except Exception as e:  # noqa: BLE001
            await self.bus.publish(channel, {"type": "error", "error": str(e)[:300]})
        await self.bus.publish(channel, {"type": "run_finished", "elapsed": round(time.monotonic() - t0, 2)})

    async def state(self, thread_id: str, graph=None) -> dict:
        snap = await (graph or self.bid).aget_state({"configurable": {"thread_id": thread_id}})
        values = dict(snap.values or {})
        values["pending_approval"] = [i.value for t in snap.tasks for i in (t.interrupts or [])]
        values["next"] = list(snap.next)
        return values

    async def sync_job(self, user_id: str, job_id: str):
        s = await self.state(self.thread(user_id, job_id))
        usage = s.get("usage", {})
        status = "awaiting_approval" if s["pending_approval"] else s.get("status", "unknown")
        stage = {"awaiting_approval": "drafted", "submitted": "submitted", "rejected": "lost",
                 "skipped": "skipped"}.get(status, status)
        db.upsert_job(user_id, job_id, status=status, stage=stage, action=(s.get("decision") or {}).get("action"),
                      reason=(s.get("decision") or {}).get("reason"), fit=(s.get("fit_report") or {}).get("score"),
                      risk=(s.get("risk_report") or {}).get("score"), flags=(s.get("risk_report") or {}).get("flags"),
                      price=(s.get("price_quote") or {}).get("amount_usd"),
                      connects=(s.get("price_quote") or s.get("job") or {}).get("connects_cost"),
                      category=(s.get("job_spec") or {}).get("category"),
                      cost_usd=round(sum(u.get("usd", 0) for u in usage.values()), 6),
                      seconds=round(sum(u.get("seconds", 0) for u in usage.values()), 2))

    async def enqueue_bid(self, user: dict, job: dict, resume: dict | None = None):
        """Long runs go to the Arq worker on Redis when RUN_IN_WORKER=1; otherwise a background task here.
        The Arq job id is derived from thread + action, so a retried enqueue never runs twice."""
        if os.getenv("RUN_IN_WORKER") == "1" and self.bus.redis:
            from arq import create_pool
            from arq.connections import RedisSettings
            if not getattr(self, "arq", None):
                self.arq = await create_pool(RedisSettings.from_dsn(os.environ["REDIS_URL"]))
            jid = f"{self.thread(user['id'], job['job_id'])}:{json.dumps(resume, sort_keys=True) if resume else 'start'}"
            await self.arq.enqueue_job("run_bid_job", user, job, resume, _job_id=hashlib.sha256(jid.encode()).hexdigest()[:24])
        else:
            self.spawn(self.run_bid(user, job, resume))

    def spawn(self, coro):
        t = asyncio.create_task(coro)
        self.tasks.add(t)
        t.add_done_callback(self.tasks.discard)
        return t

    # ---------- conversations ----------
    async def run_convo(self, user: dict, thread_id: str, resume: dict | None = None):
        gthread = f"convo:{user['id']}:{thread_id}"
        cfg = self.cfg(gthread)
        inp: Any = Command(resume=resume) if resume else {"user_id": user["id"], "thread_id": thread_id}
        await self._stream(self.convo, inp, cfg, channel=gthread)
        s = await self.state(gthread, self.convo)
        db.upsert_convo(user["id"], thread_id, status="awaiting_approval" if s["pending_approval"] else s.get("status"),
                        intent=(s.get("intent") or {}).get("intent"))


runtime = Runtime()
