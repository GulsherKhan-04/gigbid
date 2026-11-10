"""Idempotency ledger, per-user rate limiter and append-only audit log (SQLite file or Postgres via env)."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path

from agent.guards import mask_obj

DB = Path(os.getenv("MARKETPLACE_LEDGER") or Path(__file__).resolve().parents[2] / "data/processed/ledger.db")
_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS idem (key TEXT PRIMARY KEY, result TEXT, at REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL, user TEXT, "
              "tool TEXT, args TEXT, result TEXT, trace_id TEXT)")
    c.execute("CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit "
              "BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END")
    c.execute("CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit "
              "BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END")
    return c


def seen(key: str) -> dict | None:
    with _lock, _conn() as c:
        row = c.execute("SELECT result FROM idem WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def remember(key: str, result: dict) -> None:
    with _lock, _conn() as c:
        c.execute("INSERT OR IGNORE INTO idem VALUES (?,?,?)", (key, json.dumps(result), time.time()))


def audit(user: str, tool: str, args: dict, result: object, trace_id: str | None) -> None:
    with _lock, _conn() as c:
        c.execute("INSERT INTO audit (at,user,tool,args,result,trace_id) VALUES (?,?,?,?,?,?)",
                  (time.time(), user, tool, json.dumps(mask_obj(json.loads(json.dumps(args, default=str)))),
                   json.dumps(mask_obj(json.loads(json.dumps(result, default=str))))[:4000], trace_id or ""))


class RateLimiter:
    """Token bucket per user, kept below GigSim's limit (config: marketplace.max_requests_per_minute)."""

    def __init__(self, per_minute: int):
        self.rate, self.buckets = per_minute / 60.0, {}
        self.capacity = max(1, per_minute // 4)

    def acquire(self, user: str) -> float:
        tokens, last = self.buckets.get(user, (self.capacity, time.monotonic()))
        now = time.monotonic()
        tokens = min(self.capacity, tokens + (now - last) * self.rate)
        wait = 0.0 if tokens >= 1 else (1 - tokens) / self.rate
        self.buckets[user] = (tokens - 1 + wait * self.rate, now + wait)
        return wait
