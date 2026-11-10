"""Vector + BM25 index per persona, persisted under data/processed/<persona>/ (git-ignored).

Incremental: chunks are keyed by evidence_id, so re-indexing after an upload only embeds new chunks.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from rag.index.embed import embed

ROOT = Path(__file__).resolve().parents[2]


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#.]+", text.lower())


class PortfolioIndex:
    def __init__(self, persona: str, chunks: list[dict], vectors: np.ndarray):
        self.persona, self.chunks, self.vectors = persona, chunks, vectors
        self.by_id = {c["evidence_id"]: c for c in chunks}
        self.bm25 = BM25Okapi([tokenize(c["text"] + " " + " ".join(c["skills"])) for c in chunks]) if chunks else None

    # ---- persistence ----
    @staticmethod
    def path(persona: str) -> Path:
        return ROOT / "data" / "processed" / persona

    def save(self) -> None:
        p = self.path(self.persona)
        p.mkdir(parents=True, exist_ok=True)
        (p / "chunks.jsonl").write_text("\n".join(json.dumps(c) for c in self.chunks), encoding="utf-8")
        np.save(p / "vectors.npy", self.vectors)

    @classmethod
    def load(cls, persona: str) -> "PortfolioIndex | None":
        p = cls.path(persona)
        if not (p / "chunks.jsonl").exists():
            return None
        chunks = [json.loads(x) for x in (p / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if x]
        return cls(persona, chunks, np.load(p / "vectors.npy"))

    @classmethod
    def build(cls, persona: str, chunks: list[dict]) -> "PortfolioIndex":
        old = cls.load(persona)
        known = {c["evidence_id"]: i for i, c in enumerate(old.chunks)} if old else {}
        new = [c for c in chunks if c["evidence_id"] not in known]
        new_vecs = embed([c["text"] for c in new]) if new else None
        vecs = []
        for c in chunks:
            if c["evidence_id"] in known:
                vecs.append(old.vectors[known[c["evidence_id"]]])
            else:
                vecs.append(new_vecs[new.index(c)])
        idx = cls(persona, chunks, np.vstack(vecs) if vecs else np.zeros((0, 1), dtype=np.float32))
        idx.save()
        return idx

    # ---- search primitives ----
    def dense(self, query: str, k: int, filters: dict | None = None) -> list[tuple[str, float]]:
        if not self.chunks:
            return []
        scores = self.vectors @ embed([query])[0]
        order = np.argsort(-scores)
        return [(self.chunks[i]["evidence_id"], float(scores[i])) for i in order
                if _ok(self.chunks[i], filters)][:k]

    def lexical(self, query: str, k: int, filters: dict | None = None) -> list[tuple[str, float]]:
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(tokenize(query))
        order = np.argsort(-scores)
        return [(self.chunks[i]["evidence_id"], float(scores[i])) for i in order
                if scores[i] > 0 and _ok(self.chunks[i], filters)][:k]


def _ok(chunk: dict, filters: dict | None) -> bool:
    if not filters:
        return True
    return all(chunk.get(k) == v or (isinstance(v, list) and chunk.get(k) in v) for k, v in filters.items())


def rrf(rankings: list[list[tuple[str, float]]], k: int = 60) -> list[tuple[str, float]]:
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, (eid, _) in enumerate(ranking):
            fused[eid] = fused.get(eid, 0.0) + 1.0 / (k + rank + 1)
    return sorted(fused.items(), key=lambda x: -x[1])
