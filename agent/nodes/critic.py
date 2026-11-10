from __future__ import annotations

import time

from agent.guards import untrusted
from agent.handoffs import Critique
from agent.llm import get_llm
from agent.nodes.common import job_text, update
from agent.settings import config, prompt


async def critic_node(state):
    t0, draft = time.monotonic(), state["proposal_draft"]
    words = len(draft["cover_letter"].split())
    limit = config()["policy"]["max_proposal_words"]
    c, usage = await get_llm().structured(
        "critic", prompt("critic"),
        untrusted("job_post", job_text(state["job"])) + f"\n\nWord limit {limit}; draft has {words} words."
        f"\nVerified claims: {draft.get('claims', [])}\n\nDRAFT:\n{draft['cover_letter']}", Critique)
    if words > limit:
        c.length_ok, c.passed = False, False
        c.reasons.append(f"Cut to at most {limit} words (now {words}).")
    return update("critic", usage, t0, critiques=[c.model_dump()])
