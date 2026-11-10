from __future__ import annotations

import time

from agent.guards import untrusted
from agent.handoffs import ProposalDraft
from agent.llm import get_llm
from agent.memory.store import read_memories
from agent.nodes.common import job_text, update
from agent.settings import config, prompt


async def writer_node(state):
    from langgraph.config import get_store
    store = get_store()
    t0, job, spec = time.monotonic(), state["job"], state.get("job_spec", {})
    evidence = _dedupe(state.get("evidence", []))
    style, outcome = await read_memories(store, state["user_id"], spec.get("category", "general"))
    last = (state.get("critiques") or [{}])[-1]
    revision = state.get("proposal_draft", {}).get("revision", -1) + 1
    listing = "\n".join(f"[{e['evidence_id']}] {e.get('title') or e['project']}: {e['text'][:600]}" for e in evidence)
    user = (untrusted("job_post", job_text(job)) +
            f"\n\nClient requirements: {spec.get('requirements', [])}\nHidden needs: {spec.get('hidden_needs', [])}"
            f"\nScreening questions: {spec.get('screening_questions', [])}\n\nEVIDENCE:\n{listing or '(none)'}"
            f"\n\nFreelancer style preferences: {style or 'none yet'}\nWhat worked before in '{spec.get('category')}': "
            f"{outcome or 'no data yet'}")
    if revision and last.get("reasons"):
        user += f"\n\nREVISE the previous draft. Reviewer said: {last['reasons']}\nPrevious draft:\n" \
                f"{state['proposal_draft']['cover_letter']}"
    draft, usage = await get_llm().structured(
        "writer", prompt(strategy_for(job["job_id"])[1]).replace("{max_words}", str(config()["policy"]["max_proposal_words"])), user,
        ProposalDraft)
    draft.job_id, draft.revision = job["job_id"], revision
    draft_strategy = strategy_for(job["job_id"])[0]
    known = {e["evidence_id"] for e in evidence}
    draft.evidence_ids = sorted({i for i in draft.evidence_ids if i in known} |
                                {i for i in known if f"[{i}]" in draft.cover_letter})
    return update("writer", usage, t0, proposal_draft={**draft.model_dump(), "strategy": draft_strategy})


def strategy_for(job_id: str) -> tuple[str, str]:
    """X2: deterministic assignment by job id, so a job keeps its arm across revisions and restarts."""
    import hashlib
    exp = (config().get("experiments") or {}).get("proposal_ab") or {}
    if not exp.get("enabled"):
        return "A", "writer"
    arms = sorted(exp["strategies"])
    arm = arms[int(hashlib.sha256(f"{exp.get('seed', 0)}|{job_id}".encode()).hexdigest(), 16) % len(arms)]
    return arm, exp["strategies"][arm]


def _dedupe(evidence: list[dict]) -> list[dict]:
    seen, out = set(), []
    for e in evidence:
        if e["evidence_id"] not in seen:
            seen.add(e["evidence_id"])
            out.append(e)
    return out
