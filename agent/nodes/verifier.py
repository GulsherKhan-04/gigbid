from __future__ import annotations

import time

from agent.nodes.common import update
from agent.nodes.writer import _dedupe
from rag.verify import remove_unsupported, unsupported_rate, verify_claims


async def verifier_node(state):
    t0, draft = time.monotonic(), dict(state["proposal_draft"])
    claims, usage = await verify_claims(draft["cover_letter"], _dedupe(state.get("evidence", [])))
    before = unsupported_rate(claims)
    draft["cover_letter"] = remove_unsupported(draft["cover_letter"], claims)
    draft["claims"] = [c.model_dump() for c in claims if c.status != "unsupported"]
    draft["unsupported_before"] = before
    draft["unsupported_removed"] = [c.text for c in claims if c.status == "unsupported"]
    return update("verifier", usage, t0, proposal_draft=draft)
