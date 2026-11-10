"""V2: BM25 + dense per requirement, fused with RRF. Exact names ("Celery", "dbt") survive via BM25."""
from rag.index.store import rrf
from rag.variants.base import materialise


class V2Hybrid:
    name = "v2_hybrid"

    def __init__(self, decompose: bool = True):
        self.decompose = decompose

    async def retrieve(self, index, job_text, requirements, k, filters=None):
        reqs = (requirements if self.decompose and requirements else [job_text])
        runs, matched = [], {}
        for r in reqs:
            d, lex = index.dense(r, k * 2, filters), index.lexical(r, k * 2, filters)
            fused = rrf([d, lex])
            runs.append(fused)
            for eid, _ in fused[:3]:
                matched.setdefault(eid, []).append(r)
        return materialise(index, rrf(runs), k, matched)
