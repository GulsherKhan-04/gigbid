from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class SignUp(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=8, max_length=200)
    persona: str
    hourly_rate_usd: float = 30
    minimum_project_budget_usd: float = 200
    weekly_connects_budget: int = 80
    saved_searches: list[str] = Field(default_factory=lambda: ["python", "machine learning"])


class Login(BaseModel):
    email: str
    password: str


class Session(BaseModel):
    token: str
    user: dict[str, Any]


class JobRow(BaseModel):
    job_id: str
    title: str | None = None
    status: str | None = None
    action: str | None = None
    fit: float | None = None
    risk: float | None = None
    flags: list[str] | None = None
    price: float | None = None
    connects: int | None = None
    stage: str | None = None
    category: str | None = None
    cost_usd: float | None = None
    seconds: float | None = None
    reason: str | None = None


class Approval(BaseModel):
    action: Literal["approve", "edit", "reject"]
    edited_text: str | None = None
    reason: str | None = Field(None, max_length=500)


class Settings(BaseModel):
    autonomy: Literal["suggest_only", "auto_skip_low_fit"] = "suggest_only"
    hourly_rate_usd: float = 30
    minimum_project_budget_usd: float = 200
    weekly_connects_budget: int = 80
    saved_searches: list[str] = Field(default_factory=list)


class Outcome(BaseModel):
    outcome: Literal["viewed", "replied", "interview", "hired", "lost", "ignored"]
