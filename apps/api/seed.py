"""Creates the reviewer login (credentials from env, never from the repo) preloaded with a persona."""
from __future__ import annotations

import os

from sqlalchemy import select

from apps.api.auth.security import create_user
from apps.api.db import engine, users
from rag.retriever import personas


def ensure_reviewer() -> None:
    email, pw = os.getenv("REVIEWER_EMAIL"), os.getenv("REVIEWER_PASSWORD")
    if not (email and pw):
        return
    with engine.connect() as c:
        if c.execute(select(users).where(users.c.email == email.lower())).first():
            return
    persona = os.getenv("REVIEWER_PERSONA") or personas()[0]
    create_user(email, pw, persona, {"hourly_rate_usd": 35, "minimum_project_budget_usd": 200,
                                     "weekly_connects_budget": 80, "saved_searches": ["python", "data", "web"],
                                     "autonomy": "suggest_only"})
