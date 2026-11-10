"""V0 baseline: fixed chunks, top-k cosine against the whole job post."""
from rag.variants.base import materialise


class V0Naive:
    name = "v0_naive"

    async def retrieve(self, index, job_text, requirements, k, filters=None):
        return materialise(index, index.dense(job_text, k, filters), k)
