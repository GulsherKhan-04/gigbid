"""Preprocesses the REAL job postings (Kaggle "Upwork Job Postings Dataset 2024", asaniczka) for GigSim-lite.

Input : data/raw/upwork-jobs.csv   (not committed: 72 MB; download from Kaggle, see docs/DATA_CARD.md)
Output: data/real/jobs_used.jsonl  (committed: only the cleaned rows GigBid uses, every row source=real) and
        data/historical_jobs.json (price statistics from all cleaned rows)

Steps: drop rows without title/description/price, de-duplicate by link and by normalised title+description,
strip whitespace, truncate descriptions to 1,500 chars, parse fixed budget or hourly range, tag each job with the
persona whose skills it mentions most (or "other"), and extract the persona skills it names as required_skills.
No personal data is kept (the dataset has none beyond country, which is kept).

    python -m simulator.real_data
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "upwork-jobs.csv"
OUT = ROOT / "data" / "real" / "jobs_real.jsonl"
SOURCE = "real:kaggle/asaniczka/upwork-job-postings-dataset-2024-50k-records"


def _num(x: str) -> float | None:
    try:
        v = float(x)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def skill_hits(text: str, skills: list[str]) -> list[str]:
    low = f" {text.lower()} "
    out = []
    for s in skills:
        pat = re.escape(s.lower())
        if re.search(rf"(?<![a-z0-9]){pat}(?![a-z0-9])", low):
            out.append(s)
    return out


def load(personas: dict, outside: list[str]) -> list[dict]:
    if not RAW.exists():
        return []
    csv.field_size_limit(10 ** 8)
    seen_links, seen_text, rows = set(), set(), []
    with RAW.open(encoding="utf-8", errors="ignore") as f:
        for r in csv.DictReader(f):
            title, desc = (r.get("title") or "").strip(), " ".join((r.get("description") or "").split())
            if not title or len(desc) < 80 or r.get("link") in seen_links:
                continue
            key = hashlib.sha1((title.lower() + desc[:300].lower()).encode()).hexdigest()
            if key in seen_text:
                continue
            hourly = (r.get("is_hourly") or "").strip().lower() == "true"
            lo, hi, budget = _num(r.get("hourly_low")), _num(r.get("hourly_high")), _num(r.get("budget"))
            if hourly and not (lo or hi):
                continue
            if not hourly and not budget:
                continue
            seen_links.add(r.get("link"))
            seen_text.add(key)
            text = f"{title} {desc}"
            scores = {p: skill_hits(text, cfg["skills"]) for p, cfg in personas.items()}
            best = max(scores, key=lambda p: len(scores[p]))
            persona = best if len(scores[best]) >= 1 else "other"
            rows.append({
                "real_id": key[:12], "title": title[:200], "description": desc[:1500],
                "budget_type": "hourly" if hourly else "fixed",
                "budget": {"type": "hourly", "min": lo or hi, "max": hi or lo, "currency": "USD"} if hourly
                else {"type": "fixed", "min": budget, "max": budget, "currency": "USD"},
                "country": (r.get("country") or "").strip() or None,
                "published_date": (r.get("published_date") or "")[:10],
                "persona_match": persona, "required_skills": scores[best] + skill_hits(text, outside),
                "source": SOURCE,
            })
    return rows


if __name__ == "__main__":
    from simulator.generate import OUTSIDE_SKILLS, PERSONAS
    rows = load(PERSONAS, OUTSIDE_SKILLS)
    from collections import Counter
    print(len(rows), "clean real jobs;", Counter(r["persona_match"] for r in rows).most_common())
