"""R7: long-term memory changes only through these explicit rules.

Style memory  - a candidate pattern from a user edit is promoted after it appears in >= STYLE_MIN_EDITS distinct
                edits and has not been contradicted (the user re-adding what they removed resets it).
Outcome memory - a category insight is promoted after >= OUTCOME_MIN_PROPOSALS proposals with known outcomes.
Raw tool output never reaches memory: only these derived, human-readable rules do.
"""
from __future__ import annotations

import difflib
import re

STYLE_MIN_EDITS = 3
OUTCOME_MIN_PROPOSALS = 3
_WATCH_WORDS = re.compile(r"\b(passionate|excited|hello|hi|dear|expert|guru|ninja|rockstar|seasoned)\b", re.I)


def _sentences(t: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s.strip()]


def style_candidates(original: str, edited: str) -> list[str]:
    cands = []
    o, e = _sentences(original), _sentences(edited)
    if o and e and o[0] not in edited:
        cands.append("cut the generic first sentence; open with the client's problem")
    removed = {w.lower() for w in _WATCH_WORDS.findall(original)} - {w.lower() for w in _WATCH_WORDS.findall(edited)}
    cands += [f'never say "{w}"' for w in sorted(removed)]
    lo, le = len(original.split()), len(edited.split())
    if lo and le < 0.8 * lo:
        cands.append("keep proposals shorter than the first draft (about 20% shorter)")
    if "?" not in original and "?" in edited:
        cands.append("end with a specific question for the client")
    return cands


def contradicted(original: str, edited: str, rule: str) -> bool:
    m = re.match(r'never say "(.+)"', rule)
    return bool(m and m.group(1) not in original.lower() and m.group(1) in edited.lower())


def should_promote_style(count: int, contradictions: int) -> bool:
    return count >= STYLE_MIN_EDITS and contradictions == 0


def outcome_insight(category: str, rows: list[dict]) -> str | None:
    if len(rows) < OUTCOME_MIN_PROPOSALS:
        return None
    good = [r for r in rows if r["outcome"] in ("won", "replied", "hired", "interview")]
    rate = len(good) / len(rows)
    lengths = [r["words"] for r in good] or [0]
    return (f"In '{category}', {len(good)}/{len(rows)} proposals got a reply or better ({rate:.0%}); "
            f"successful ones averaged {sum(lengths) // len(lengths)} words.")


def edit_diff(original: str, edited: str) -> str:
    return "\n".join(difflib.unified_diff(original.splitlines(), edited.splitlines(), "draft", "edited", lineterm=""))
