"""Dev-set loading and metric helpers. Every number in the README/report must come from evals/results/*.json."""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evals" / "results"


def load_dev(persona: str | None = None, limit: int | None = None) -> list[dict]:
    """Expected: evals/datasets/<persona>/dev.jsonl (or .json) from the starter kit. Each row has the job and
    gold labels. Field names vary between kits, so they are normalised here; adjust if the provided set differs."""
    rows = []
    base = ROOT / "evals" / "datasets"
    for f in sorted(base.rglob("*.json*")):
        p = f.parent.name if f.parent != base else f.stem.split("_")[0]
        if persona and p != persona:
            continue
        data = ([json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.suffix == ".jsonl"
                else json.loads(f.read_text()))
        for r in data:
            gold = r.get("gold") or r.get("labels") or r
            rows.append({"persona": r.get("persona", p), "job": r.get("job") or r,
                         "action": gold.get("action") or gold.get("bid_or_skip") or gold.get("decision"),
                         "is_scam": bool(gold.get("is_scam") or gold.get("scam")),
                         "evidence_ids": gold.get("evidence_ids") or gold.get("relevant_evidence") or [],
                         "price_band": gold.get("price_band") or gold.get("fair_price_band"),
                         "job_type": (r.get("job") or r).get("category", "general")})
    return rows[:limit] if limit else rows


def recall_at(ranked: list[str], gold: list[str], k: int) -> float:
    return len(set(ranked[:k]) & set(gold)) / len(gold) if gold else float("nan")


def mrr(ranked: list[str], gold: list[str]) -> float:
    return next((1 / (i + 1) for i, e in enumerate(ranked) if e in gold), 0.0) if gold else float("nan")


def ndcg_at(ranked: list[str], gold: list[str], k: int) -> float:
    if not gold:
        return float("nan")
    dcg = sum(1 / math.log2(i + 2) for i, e in enumerate(ranked[:k]) if e in gold)
    idcg = sum(1 / math.log2(i + 2) for i in range(min(k, len(gold))))
    return dcg / idcg


def mean(xs) -> float | None:
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return round(sum(xs) / len(xs), 4) if xs else None


def pct(xs: list[float], q: float) -> float | None:
    xs = sorted(xs)
    return round(xs[int(q * (len(xs) - 1))], 3) if xs else None


def f1(tp: int, fp: int, fn: int) -> float:
    return round(2 * tp / (2 * tp + fp + fn), 4) if tp else 0.0


def save(name: str, payload: dict) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), **payload}
    path = RESULTS / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"wrote {path.relative_to(ROOT)}")
    return path
