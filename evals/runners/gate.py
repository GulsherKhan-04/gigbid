"""CI gate: fail if bid/skip F1 drops or unsupported claims rise past thresholds (edit the numbers once you
have a measured baseline in evals/results/decisions_dev.json)."""
import json
import sys

from evals.runners.common import RESULTS

MIN_F1, MAX_UNSUPPORTED = 0.60, 0.25
s = json.loads((RESULTS / "decisions_smoke.json").read_text())["summary"]
problems = []
if (s.get("bid_skip_f1") or 0) < MIN_F1:
    problems.append(f"bid/skip F1 {s.get('bid_skip_f1')} < {MIN_F1}")
if (s.get("unsupported_rate_before_verification") or 0) > MAX_UNSUPPORTED:
    problems.append(f"unsupported claims {s['unsupported_rate_before_verification']} > {MAX_UNSUPPORTED}")
print(s)
sys.exit("; ".join(problems) if problems else 0)
