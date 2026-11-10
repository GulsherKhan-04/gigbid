"""B3 claim verification. Split the draft into claims, label each against evidence, drop unsupported ones."""
from __future__ import annotations

import re

from pydantic import BaseModel, Field

from agent.handoffs import Claim
from agent.llm import get_llm


class ClaimSet(BaseModel):
    claims: list[Claim] = Field(default_factory=list)


SYSTEM = ("You check a freelancer proposal for truthfulness. Split it into atomic claims about the freelancer's "
          "experience, skills, results or past clients (ignore greetings, questions and plans). For each claim set "
          "status: supported (evidence states it), partly_supported (evidence implies part of it) or unsupported. "
          "List the evidence ids that support it. Copy each claim's text EXACTLY as a substring of the proposal.")


async def verify_claims(draft: str, evidence: list[dict]) -> tuple[list[Claim], dict]:
    listing = "\n".join(f"[{e['evidence_id']}] {e['text'][:700]}" for e in evidence) or "(no evidence)"
    result, usage = await get_llm().structured("verifier", SYSTEM, f"Proposal:\n{draft}\n\nEvidence:\n{listing}",
                                               ClaimSet)
    known = {e["evidence_id"] for e in evidence}
    for c in result.claims:
        c.evidence_ids = [i for i in c.evidence_ids if i in known]
        if c.status != "unsupported" and not c.evidence_ids:
            c.status = "unsupported"
    return result.claims, usage


def remove_unsupported(draft: str, claims: list[Claim]) -> str:
    text = draft
    for c in claims:
        if c.status == "unsupported" and c.text and c.text in text:
            sentence = next((s for s in re.split(r"(?<=[.!?])\s+", text) if c.text in s), c.text)
            text = text.replace(sentence, "").replace("  ", " ")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def unsupported_rate(claims: list[Claim]) -> float:
    return sum(c.status == "unsupported" for c in claims) / len(claims) if claims else 0.0
