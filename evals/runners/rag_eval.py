"""B4 retrieval metrics for every variant:  python -m evals.runners.rag_eval [--variants v0_naive,v2_hybrid] [--limit 50]"""
from __future__ import annotations

import argparse
import asyncio
import time

from agent.nodes.fit_matcher import quick_requirements
from evals.runners.common import load_dev, mean, ndcg_at, mrr, pct, recall_at, save
from rag.retriever import VARIANTS, retrieve


async def run(variants: list[str], limit: int | None, name: str = "rag_retrieval"):
    rows = [r for r in load_dev(limit=limit) if r["evidence_ids"]]
    if not rows:
        raise SystemExit("No dev rows with gold evidence. Put the provided dev set in evals/datasets/<persona>/.")
    out = {}
    for v in variants:
        per, lat = [], []
        for r in rows:
            job = r["job"]
            text = f"{job.get('title', '')}. {job.get('description', '')}"
            t0 = time.monotonic()
            hits = await retrieve(r["persona"], text, quick_requirements(job), 10, v)
            lat.append(time.monotonic() - t0)
            ids = [h["evidence_id"] for h in hits]
            per.append({"persona": r["persona"], "job_type": r["job_type"], "recall5": recall_at(ids, r["evidence_ids"], 5),
                        "mrr": mrr(ids, r["evidence_ids"]), "ndcg10": ndcg_at(ids, r["evidence_ids"], 10),
                        "n_req": len(quick_requirements(job))})
        by = lambda key: {k: {"recall5": mean(x["recall5"] for x in per if x[key] == k),
                              "ndcg10": mean(x["ndcg10"] for x in per if x[key] == k)}
                          for k in sorted({x[key] for x in per})}
        out[v] = {"n": len(per), "recall5": mean(x["recall5"] for x in per), "mrr": mean(x["mrr"] for x in per),
                  "ndcg10": mean(x["ndcg10"] for x in per), "p50_s": pct(lat, .5), "p95_s": pct(lat, .95),
                  "by_persona": by("persona"), "by_job_type": by("job_type"),
                  "four_plus_requirements": {"recall5": mean(x["recall5"] for x in per if x["n_req"] >= 4)}}
        print(v, out[v]["recall5"], out[v]["ndcg10"])
    save(name, {"variants": out, "dataset": "GigSim-lite substitute dev set", "embeddings": __import__("os").getenv("EMBEDDINGS_PROVIDER") or "ollama"})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--name", default="rag_retrieval")
    a = ap.parse_args()
    asyncio.run(run(a.variants.split(","), a.limit, a.name))
