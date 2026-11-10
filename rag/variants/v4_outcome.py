"""V4: outcome-aware ranking. Evidence from proposals that won or got replies is boosted."""
from rag.variants.base import materialise
from rag.variants.v2_hybrid import V2Hybrid

BOOST = {"won": 1.5, "hired": 1.5, "replied": 1.25, "ignored": 0.8}


class V4Outcome:
    name = "v4_outcome"

    async def retrieve(self, index, job_text, requirements, k, filters=None):
        pool = await V2Hybrid().retrieve(index, job_text, requirements, k * 3, filters)
        for p in pool:
            p["score"] *= BOOST.get(str(p.get("outcome", "")).lower(), 1.0)
        pool.sort(key=lambda p: -p["score"])
        matched = {p["evidence_id"]: p["requirements"] for p in pool}
        return materialise(index, [(p["evidence_id"], p["score"]) for p in pool], k, matched)
