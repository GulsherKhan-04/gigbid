"""Scripted LLM for offline tests: returns schema-valid objects per node without any API key."""
from __future__ import annotations

import re


class FakeLLM:
    def __init__(self, critic_fail_times: int = 0):
        self.critic_fail_times, self.calls = critic_fail_times, []

    async def structured(self, node, system, user, schema):
        self.calls.append(node)
        ids = re.findall(r"\[([0-9a-z-]{6,})\]", user)
        usage = {"model": "fake", "prompt_tokens": len(user) // 4, "completion_tokens": 50, "usd": 0.0, "seconds": 0.01}
        name = schema.__name__
        if name == "JobSpec":
            title = re.search(r"Title: (.*)", user).group(1)
            return schema(job_id="x", title=title, requirements=["Python classification baseline", "precision/recall"],
                          required_skills=["Python"], category="ml"), usage
        if name == "RiskReport":
            bad = "free" in user.lower() and "test" in user.lower()
            return schema(score=0.9 if bad else 0.1, flags=["free_work"] if bad else [], explanation="fake"), usage
        if name == "FitReport":
            return schema(score=0.8 if ids else 0.0, matrix=[{"requirement": "Python", "evidence_ids": ids[:1],
                                                             "strength": "strong" if ids else "none"}]), usage
        if name == "ProposalDraft":
            ev = ids[0] if ids else "none"
            return schema(job_id="x", cover_letter=(
                f"Your churn baseline needs honest evaluation on imbalanced data. I built a reproducible scikit-learn "
                f"comparison of logistic regression and random forest [{ev}]. I also won a Kaggle gold medal. "
                f"I would start by profiling class balance. Which metric matters most to your team?"),
                evidence_ids=[ev]), usage
        if name == "ClaimSet":
            ev = ids[0] if ids else ""
            return schema(claims=[{"text": "I built a reproducible scikit-learn comparison of logistic regression and "
                                           "random forest", "status": "supported", "evidence_ids": [ev]},
                                  {"text": "I also won a Kaggle gold medal", "status": "unsupported", "evidence_ids": []}]), usage
        if name == "Critique":
            if self.critic_fail_times > 0:
                self.critic_fail_times -= 1
                return schema(passed=False, personalised=False, reasons=["Mention their data size."]), usage
            return schema(passed=True), usage
        if name == "ComplianceVerdict":
            return schema(allowed=True, cleaned_text=""), usage
        if name == "Grade":
            return schema(relevant_ids=ids[:2]), usage
        if name == "LiaisonOut":
            return schema(intent={"intent": "interview_request"}, reply="Thanks! Happy to talk. Do any of these times work?"), usage
        raise AssertionError(f"unexpected schema {name}")
