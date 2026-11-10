"""Factory: the deployed variant is chosen in agent/config.yaml (rag.variant) after `make eval` (R6)."""
from __future__ import annotations

from rag.index.store import PortfolioIndex
from rag.ingest.loaders import load_all
from rag.variants.v0_naive import V0Naive
from rag.variants.v1_decompose import V1Decompose
from rag.variants.v2_hybrid import V2Hybrid
from rag.variants.v3_rerank import V3Rerank
from rag.variants.v4_outcome import V4Outcome
from rag.variants.v8_corrective import V8Corrective

VARIANTS = {v.name: v for v in (V0Naive(), V1Decompose(), V2Hybrid(), V3Rerank(), V4Outcome(), V8Corrective())}
_indexes: dict[str, PortfolioIndex] = {}


def get_index(persona: str) -> PortfolioIndex:
    if persona not in _indexes:
        idx = PortfolioIndex.load(persona)
        if idx is None:
            chunks = [c for c in load_all() if c["persona"] == persona] or load_all()
            idx = PortfolioIndex.build(persona, chunks)
        _indexes[persona] = idx
    return _indexes[persona]


def reindex(persona: str) -> int:
    chunks = [c for c in load_all(persona) if c["persona"] == persona]
    _indexes[persona] = PortfolioIndex.build(persona, chunks)
    return len(chunks)


def personas() -> list[str]:
    return sorted({c["persona"] for c in load_all()})


async def retrieve(persona: str, job_text: str, requirements: list[str], k: int, variant: str,
                   filters: dict | None = None) -> list[dict]:
    return await VARIANTS[variant].retrieve(get_index(persona), job_text, requirements, k, filters)
