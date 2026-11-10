from __future__ import annotations

from typing import Protocol

from rag.index.store import PortfolioIndex


class Variant(Protocol):
    name: str

    async def retrieve(self, index: PortfolioIndex, job_text: str, requirements: list[str], k: int,
                       filters: dict | None = None) -> list[dict]: ...


def materialise(index: PortfolioIndex, ranked: list[tuple[str, float]], k: int,
                matched: dict[str, list[str]] | None = None) -> list[dict]:
    out = []
    for eid, score in ranked[:k]:
        c = index.by_id[eid]
        out.append({"evidence_id": eid, "score": round(score, 4), "type": c["type"], "source": c["source"],
                    "date": c.get("date", ""), "outcome": c.get("outcome", ""), "project": c["project"],
                    "title": c.get("title", ""), "skills": c.get("skills", []), "text": c["text"],
                    "requirements": (matched or {}).get(eid, [])})
    return out
