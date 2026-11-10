"""Compliance Guard: deterministic policy rules from config first, then an LLM pass against the policy pack."""
from __future__ import annotations

import re
import time

from agent.handoffs import ComplianceVerdict
from agent.llm import get_llm
from agent.nodes.common import update
from agent.settings import config, policy_text, prompt

CONTACT = re.compile(r"([\w.+-]+@[\w-]+\.[\w.]+|\+?\d[\d\s().-]{8,}\d|https?://(?!github\.com)\S+)")


def rule_check(text: str) -> tuple[str, list[str]]:
    violations, out = [], text
    for m in CONTACT.findall(out):
        violations.append(f"contact detail removed: {m[:30]}")
        out = out.replace(m, "")
    for phrase in config()["policy"]["banned_phrases"]:
        if re.search(rf"\b{re.escape(phrase)}\b", out, re.I):
            violations.append(f"banned phrase: {phrase}")
            out = re.sub(rf"[^.!?]*\b{re.escape(phrase)}\b[^.!?]*[.!?]?", "", out, flags=re.I)
    return re.sub(r"\s{2,}", " ", out).strip(), violations


async def check(text: str) -> tuple[ComplianceVerdict, dict]:
    cleaned, rule_violations = rule_check(text)
    verdict, usage = await get_llm().structured("compliance", prompt("compliance") + "\n\n" + policy_text(),
                                                f"DRAFT:\n{cleaned}", ComplianceVerdict)
    verdict.violations = rule_violations + verdict.violations
    verdict.cleaned_text = verdict.cleaned_text or cleaned
    _, residual = rule_check(verdict.cleaned_text)     # the model's rewrite must also pass the rules
    if residual:
        verdict.allowed, verdict.violations = False, verdict.violations + residual
    return verdict, usage


async def compliance_node(state):
    t0, draft = time.monotonic(), dict(state["proposal_draft"])
    verdict, usage = await check(draft["cover_letter"])
    draft["cover_letter"] = verdict.cleaned_text
    status = "awaiting_approval" if verdict.allowed else "blocked"
    return update("compliance", usage, t0, compliance_verdict=verdict.model_dump(), proposal_draft=draft,
                  status=status)
