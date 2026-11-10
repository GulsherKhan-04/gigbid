"""V8: corrective RAG. Grade evidence per requirement; re-query when weak; mark 'none' when nothing fits.

Used by the Fit Matcher so the writer is never handed evidence for a requirement the persona cannot meet.
"""
from pydantic import BaseModel, Field

from agent.llm import get_llm
from rag.variants.base import materialise
from rag.variants.v2_hybrid import V2Hybrid


class Grade(BaseModel):
    relevant_ids: list[str] = Field(default_factory=list)
    rewrite: str = Field("", description="a better search query if nothing is relevant, else empty")


class V8Corrective:
    name = "v8_corrective"

    async def retrieve(self, index, job_text, requirements, k, filters=None):
        base, kept, matched = V2Hybrid(), {}, {}
        for req in requirements or [job_text]:
            query = req
            for _ in range(2):
                pool = await base.retrieve(index, query, [query], 4, filters)
                listing = "\n".join(f"[{p['evidence_id']}] {p['text'][:400]}" for p in pool)
                g, _ = await get_llm().structured(
                    "verifier", "You grade whether portfolio evidence proves a client requirement. "
                    "List only ids that directly prove it.", f"Requirement: {req}\n\nEvidence:\n{listing}", Grade)
                hits = [p for p in pool if p["evidence_id"] in g.relevant_ids]
                if hits or not g.rewrite:
                    break
                query = g.rewrite
            for p in hits:
                kept.setdefault(p["evidence_id"], p["score"])
                matched.setdefault(p["evidence_id"], []).append(req)
        ranked = sorted(kept.items(), key=lambda x: -x[1])
        return materialise(index, ranked, k, matched)
