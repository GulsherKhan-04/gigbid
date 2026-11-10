"""Regenerates the README/report results table from evals/results/*.json (B5)."""
from __future__ import annotations

import json

from evals.runners.common import RESULTS


def load(name):
    p = RESULTS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else {}


def main():
    rag = load("rag_retrieval").get("variants", {})
    dec = load("decisions_dev").get("summary", {})
    out = ["| Variant | Recall@5 | nDCG@10 | MRR | p95 retrieval (s) |", "|---|---|---|---|---|"]
    for v, m in rag.items():
        out.append(f"| {v} | {m['recall5']} | {m['ndcg10']} | {m['mrr']} | {m['p95_s']} |")
    if dec:
        out += ["", "| Metric | Value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in dec.items()]
    table = "\n".join(out)
    (RESULTS / "results_table.md").write_text(table + "\n")
    print(table)


if __name__ == "__main__":
    main()
