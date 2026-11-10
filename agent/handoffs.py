"""Typed hand-offs. Anything a later step decides on travels as one of these, never as free text."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class JobSpec(BaseModel):
    job_id: str
    title: str
    deliverables: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list, description="atomic things the client needs")
    required_skills: list[str] = Field(default_factory=list)
    budget_min: float | None = None
    budget_max: float | None = None
    budget_type: Literal["fixed", "hourly", "unknown"] = "unknown"
    timeline: str = ""
    screening_questions: list[str] = Field(default_factory=list)
    hidden_needs: list[str] = Field(default_factory=list)
    category: str = "general"


class RiskReport(BaseModel):
    score: float = Field(ge=0, le=1, description="0 safe, 1 certain scam")
    client_quality: float = Field(ge=0, le=1, default=0.5)
    flags: list[Literal["scam", "free_work", "off_platform", "injection", "low_budget",
                        "unverified_payment", "new_client", "vague"]] = Field(default_factory=list)
    injected_instructions: list[str] = Field(default_factory=list)
    explanation: str = ""


class RequirementMatch(BaseModel):
    requirement: str
    evidence_ids: list[str] = Field(default_factory=list)
    strength: Literal["strong", "partial", "none"] = "none"
    note: str = ""


class FitReport(BaseModel):
    score: float = Field(ge=0, le=1)
    matrix: list[RequirementMatch] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class BidDecision(BaseModel):
    action: Literal["bid", "watch", "skip"]
    reason: str


class PriceQuote(BaseModel):
    amount_usd: float = Field(ge=0)
    rate_type: Literal["fixed", "hourly"] = "fixed"
    connects_cost: int = Field(ge=0, default=0)
    worth_connects: bool = True
    rationale: str = ""


class Claim(BaseModel):
    text: str
    status: Literal["supported", "partly_supported", "unsupported"]
    evidence_ids: list[str] = Field(default_factory=list)


class ProposalDraft(BaseModel):
    job_id: str
    cover_letter: str
    screening_answers: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    revision: int = 0


class Critique(BaseModel):
    passed: bool
    grounded: bool = True
    personalised: bool = True
    length_ok: bool = True
    reasons: list[str] = Field(default_factory=list)


class ComplianceVerdict(BaseModel):
    allowed: bool
    violations: list[str] = Field(default_factory=list)
    cleaned_text: str = ""


class ApprovalDecision(BaseModel):
    action: Literal["approve", "edit", "reject"]
    edited_text: str | None = None
    reason: str | None = None


class ClientIntent(BaseModel):
    intent: Literal["question", "negotiation", "interview_request", "scam_signal", "other"]
    summary: str = ""


class ReplyDraft(BaseModel):
    thread_id: str
    text: str
    proposed_slots: list[str] = Field(default_factory=list)
