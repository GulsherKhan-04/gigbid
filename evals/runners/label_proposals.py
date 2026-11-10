"""Judge calibration, step 1: YOU label 30 proposals as good or bad (the assignment requires your own labels).

    python -m evals.runners.label_proposals

Shows one job + proposal at a time: press g (good), b (bad), s (skip), q (quit and save). Resumes where you left off.
Writes evals/datasets/judge_labels.jsonl; then run `python -m evals.runners.judge_calibration` for Cohen's kappa.
Good = specific to this client's problem, every claim backed by real past work, a clear next step, no filler.
"""
from __future__ import annotations

import json
import random

from evals.runners.common import ROOT

OUT = ROOT / "evals/datasets/judge_labels.jsonl"


def pool() -> list[dict]:
    items = []
    for f in (ROOT / "evals/results").glob("decisions_*.json"):    # GigBid's own drafts, if saved
        for r in json.loads(f.read_text()).get("drafts", []):
            items.append({"job": r["job"], "proposal": r["proposal"], "source": f.name})
    for f in (ROOT / "data/personas").glob("*/proposals.jsonl"):     # persona past proposals (mixed quality)
        for line in f.read_text().splitlines():
            r = json.loads(line)
            items.append({"job": r["job_title"], "proposal": r["text"], "source": f"{f.parent.name}:{r['id']}"})
    random.Random(30).shuffle(items)
    return items


def main():
    done = [json.loads(x) for x in OUT.read_text().splitlines()] if OUT.exists() else []
    seen = {d["source"] for d in done}
    for item in (i for i in pool() if i["source"] not in seen):
        if len(done) >= 30:
            break
        print("\n" + "=" * 70 + f"\n[{len(done) + 1}/30]  JOB: {item['job']}\n\n{item['proposal']}\n")
        key = input("g = good, b = bad, s = skip, q = quit > ").strip().lower()
        if key == "q":
            break
        if key in {"g", "b"}:
            done.append({**item, "human": "good" if key == "g" else "bad"})
            OUT.write_text("\n".join(json.dumps(d) for d in done) + "\n")
    print(f"\n{len(done)} labels saved in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
