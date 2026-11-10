"""LangGraph store wrappers for the two required memories (style, outcome) plus their candidate ledgers."""
from __future__ import annotations

import time

from agent.memory import promotion_rules as rules


async def read_memories(store, user: str, category: str) -> tuple[list[str], str]:
    if store is None:
        return [], ""
    style = [i.value["rule"] for i in await store.asearch(("style", user))]
    outcome = await store.aget(("outcome", user), category)
    return style, (outcome.value["insight"] if outcome else "")


async def learn_from_edit(store, user: str, original: str, edited: str) -> list[str]:
    """Record candidate patterns; promote those that pass the rule. Returns newly promoted rules."""
    promoted = []
    cand_ns = ("style_candidates", user)
    for item in await store.asearch(cand_ns, limit=200):
        if rules.contradicted(original, edited, item.value["rule"]):
            await store.aput(cand_ns, item.key, {**item.value, "contradictions": item.value["contradictions"] + 1})
    for rule in rules.style_candidates(original, edited):
        key = rule[:60]
        cur = await store.aget(cand_ns, key)
        val = cur.value if cur else {"rule": rule, "count": 0, "contradictions": 0}
        val["count"] += 1
        await store.aput(cand_ns, key, val)
        if rules.should_promote_style(val["count"], val["contradictions"]) and not await store.aget(("style", user), key):
            await store.aput(("style", user), key, {"rule": rule, "promoted_at": time.time(), "evidence_edits": val["count"]})
            promoted.append(rule)
    return promoted


async def record_outcome(store, user: str, category: str, job_id: str, outcome: str, words: int) -> str | None:
    ns = ("outcome_log", user, category)
    await store.aput(ns, job_id, {"outcome": outcome, "words": words})
    insight = rules.outcome_insight(category, [i.value for i in await store.asearch(ns, limit=500)])
    if insight:
        await store.aput(("outcome", user), category, {"insight": insight, "updated_at": time.time()})
    return insight


async def list_memories(store, user: str) -> list[dict]:
    out = [{"kind": "style", "key": i.key, **i.value} for i in await store.asearch(("style", user))]
    out += [{"kind": "outcome", "key": i.key, **i.value} for i in await store.asearch(("outcome", user))]
    return out


async def delete_memory(store, user: str, kind: str, key: str) -> None:
    await store.adelete((kind, user), key)
    if kind == "style":
        await store.adelete(("style_candidates", user), key)
