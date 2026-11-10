"""V1: one dense retrieval per extracted requirement, merged with reciprocal rank fusion."""
from rag.index.store import rrf
from rag.variants.base import materialise


class V1Decompose:
    name = "v1_decompose"

    async def retrieve(self, index, job_text, requirements, k, filters=None):
        reqs = requirements or [job_text]
        runs, matched = [], {}
        for r in reqs:
            hits = index.dense(r, k, filters)
            runs.append(hits)
            for eid, _ in hits[:3]:
                matched.setdefault(eid, []).append(r)
        return materialise(index, rrf(runs), k, matched)
