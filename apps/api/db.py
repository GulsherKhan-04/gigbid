"""App tables (users, job inbox, tokens, outcomes). LangGraph state lives in the checkpointer, not here.
Every query is scoped by user_id (tenant isolation, E4)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from sqlalchemy import (JSON, Column, Float, Integer, MetaData, String, Table, Text, create_engine, select,
                        update as sql_update)

ROOT = Path(__file__).resolve().parents[2]


def _url() -> str:
    url = (os.getenv("DATABASE_URL") or "")
    if url.startswith("postgresql"):
        return url if "+psycopg" in url else url.replace("postgresql://", "postgresql+psycopg://")
    (ROOT / "data/processed").mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{ROOT / 'data/processed/app.db'}"


engine = create_engine(_url(), pool_pre_ping=True)
meta = MetaData()
users = Table("users", meta, Column("id", String, primary_key=True), Column("email", String, unique=True),
              Column("pw_hash", String), Column("persona", String), Column("profile", JSON),
              Column("created", Float))
jobs = Table("jobs", meta, Column("user_id", String, primary_key=True), Column("job_id", String, primary_key=True),
             Column("thread_id", String), Column("title", Text), Column("status", String), Column("action", String),
             Column("fit", Float), Column("risk", Float), Column("flags", JSON), Column("price", Float),
             Column("connects", Integer), Column("stage", String), Column("category", String),
             Column("outcome", String), Column("cost_usd", Float), Column("seconds", Float),
             Column("reason", Text), Column("updated", Float))
tokens = Table("oauth_tokens", meta, Column("user_id", String, primary_key=True),
               Column("provider", String, primary_key=True), Column("ciphertext", Text), Column("updated", Float))
convos = Table("conversations", meta, Column("user_id", String, primary_key=True),
               Column("thread_id", String, primary_key=True), Column("job_id", String), Column("status", String),
               Column("intent", String), Column("updated", Float))
meta.create_all(engine)


def upsert_job(user_id: str, job_id: str, **fields) -> None:
    fields["updated"] = time.time()
    with engine.begin() as c:
        row = c.execute(select(jobs).where(jobs.c.user_id == user_id, jobs.c.job_id == job_id)).first()
        if row:
            c.execute(sql_update(jobs).where(jobs.c.user_id == user_id, jobs.c.job_id == job_id).values(**fields))
        else:
            c.execute(jobs.insert().values(user_id=user_id, job_id=job_id, **fields))


def list_jobs(user_id: str) -> list[dict]:
    with engine.connect() as c:
        rows = c.execute(select(jobs).where(jobs.c.user_id == user_id).order_by(jobs.c.fit.desc().nulls_last()))
        return [dict(r._mapping) for r in rows]


def get_job_row(user_id: str, job_id: str) -> dict | None:
    with engine.connect() as c:
        r = c.execute(select(jobs).where(jobs.c.user_id == user_id, jobs.c.job_id == job_id)).first()
        return dict(r._mapping) if r else None


def upsert_convo(user_id: str, thread_id: str, **fields) -> None:
    fields["updated"] = time.time()
    with engine.begin() as c:
        row = c.execute(select(convos).where(convos.c.user_id == user_id, convos.c.thread_id == thread_id)).first()
        if row:
            c.execute(sql_update(convos).where(convos.c.user_id == user_id, convos.c.thread_id == thread_id)
                      .values(**fields))
        else:
            c.execute(convos.insert().values(user_id=user_id, thread_id=thread_id, **fields))


def list_convos(user_id: str) -> list[dict]:
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(select(convos).where(convos.c.user_id == user_id))]


def dumps(x) -> str:
    return json.dumps(x, default=str)
