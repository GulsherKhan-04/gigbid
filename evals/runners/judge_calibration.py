"""Calibrate the LLM judge: label >= 30 proposals yourself in evals/datasets/judge_labels.jsonl
({"proposal": "...", "job": "...", "human": "good"|"bad"}), then run this. Reports Cohen's kappa."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from pydantic import BaseModel

from agent.llm import get_llm
from evals.runners.common import ROOT, save

RUBRIC = ("Score this freelance proposal for the job as good or bad. Good = specific to the client's problem, "
          "every claim backed by concrete past work, a clear next step, no filler. Return verdict and reason.")


class Verdict(BaseModel):
    verdict: str
    reason: str = ""


def kappa(a: list[str], b: list[str]) -> float:
    labels = sorted(set(a) | set(b))
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return round((po - pe) / (1 - pe), 4) if pe < 1 else 1.0


async def main():
    f = ROOT / "evals/datasets/judge_labels.jsonl"
    rows = [json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.exists() else []
    if len(rows) < 30:
        raise SystemExit(f"Need >= 30 human labels in {f.relative_to(ROOT)} (have {len(rows)}).")
    judge = []
    for r in rows:
        v, _ = await get_llm().structured("critic", RUBRIC, f"JOB:\n{r['job']}\n\nPROPOSAL:\n{r['proposal']}", Verdict)
        judge.append("good" if "good" in v.verdict.lower() else "bad")
    human = [r["human"] for r in rows]
    disagreements = [{"i": i, "human": h, "judge": j, "proposal": rows[i]["proposal"][:300]}
                     for i, (h, j) in enumerate(zip(human, judge)) if h != j]
    save("judge_calibration", {"n": len(rows), "cohens_kappa": kappa(human, judge), "disagreements": disagreements})


if __name__ == "__main__":
    asyncio.run(main())
