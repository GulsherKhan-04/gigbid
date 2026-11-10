"""V3: V2 candidates re-scored by an open cross-encoder (bge-reranker on CPU via fastembed)."""
from agent.settings import config
from rag.variants.base import materialise
from rag.variants.v2_hybrid import V2Hybrid

_model = None


def _reranker():
    global _model
    if _model is None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder  # optional extra: pip install .[rerank]
        _model = TextCrossEncoder(model_name=config()["reranker"]["model"])
    return _model


class V3Rerank:
    name = "v3_rerank"

    async def retrieve(self, index, job_text, requirements, k, filters=None):
        pool = await V2Hybrid().retrieve(index, job_text, requirements, k * 4, filters)
        if not pool:
            return []
        query = " ; ".join(requirements) if requirements else job_text
        scores = list(_reranker().rerank(query, [p["text"] for p in pool]))
        ranked = sorted(zip(pool, scores), key=lambda x: -x[1])
        matched = {p["evidence_id"]: p["requirements"] for p in pool}
        return materialise(index, [(p["evidence_id"], float(s)) for p, s in ranked], k, matched)
