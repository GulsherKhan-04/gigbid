"""R&D question A: does tool granularity change agent behaviour?

Three tool sets over the same capabilities, 40 tasks with a known correct call each:
  fine      - one tool per operation (our real MCP surface)
  coarse    - two tools: marketplace(action, params) and portfolio(action, params)
  rewritten - the fine set with descriptions that say when to use each tool, and when not to
Measures tool-selection accuracy, argument accuracy and tokens per task.

    python -m evals.runners.tool_granularity
"""
from __future__ import annotations

import asyncio
import json
import random
from typing import Any

from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from pydantic import create_model

from agent.llm import LLM
from evals.runners.common import ROOT, mean, save

JOBS = [j["job_id"] for j in json.loads((ROOT / "data/sample/jobs.json").read_text())]
CLIENTS = [c["client_id"] for c in json.loads((ROOT / "data/sample/client_history.json").read_text())]
SKILLS = ["scikit-learn", "Celery", "dbt", "React", "Postgres", "Airflow", "FastAPI", "Tableau"]
IDS = set(JOBS + CLIENTS + SKILLS + ["evidence-001"])


def tasks(n: int = 40, seed: int = 7) -> list[dict]:
    """Eight task types, five each. The correct tool and argument are known in advance."""
    rnd = random.Random(seed)
    templates = [
        lambda: (f"Show me the full post for job {rnd.choice(JOBS)}.", "get_job", "job_id"),
        lambda: (f"Is client {rnd.choice(CLIENTS)} trustworthy? Check their history.", "get_client_history", "client_id"),
        lambda: ("How many Connects do I have left?", "get_connects_balance", None),
        lambda: (f"Find open jobs about {rnd.choice(SKILLS)}.", "search_jobs", "query"),
        lambda: (f"Do I have past work that proves {rnd.choice(SKILLS)}?", "search_evidence", "requirement"),
        lambda: ("Which skills appear most in my portfolio?", "list_skills", None),
        lambda: ("Open portfolio item evidence-001 in full.", "get_case_study", "id"),
        lambda: ("Any new messages from clients?", "list_messages", None),
    ]
    out = []
    for i in range(n):
        q, tool, arg = templates[i % len(templates)]()
        value = next((tok for tok in q.replace("?", " ").replace(".", " ").split() if tok in IDS), None)
        out.append({"q": q, "tool": tool, "arg": arg, "value": value if arg else None})
    return out


FINE = {
    "search_jobs": ("Search open jobs by keywords.", {"query": str}),
    "get_job": ("Full job post.", {"job_id": str}),
    "get_client_history": ("Client's hiring history.", {"client_id": str}),
    "get_connects_balance": ("Remaining Connects.", {}),
    "list_messages": ("Client conversation messages.", {}),
    "search_evidence": ("Find portfolio evidence for a requirement.", {"requirement": str}),
    "get_case_study": ("One portfolio item by id.", {"id": str}),
    "list_skills": ("Skills across the portfolio.", {}),
}
REWRITTEN = {
    "search_jobs": ("Use to FIND jobs by topic or skill when the user has no job id. Not for reading one known job.", {"query": str}),
    "get_job": ("Use when the user names a job id and wants its details. Not for searching.", {"job_id": str}),
    "get_client_history": ("Use to judge whether a client is trustworthy: spend, hires, rating, payment verification.", {"client_id": str}),
    "get_connects_balance": ("Use when asked how many Connects (bidding credits) are left. Takes no arguments.", {}),
    "list_messages": ("Use to read messages from clients. Not for jobs or portfolio.", {}),
    "search_evidence": ("Use to find the freelancer's OWN past work that proves a skill or requirement. Not for jobs.", {"requirement": str}),
    "get_case_study": ("Use when the user gives a portfolio item id like evidence-001 and wants it in full.", {"id": str}),
    "list_skills": ("Use to list which skills the freelancer's portfolio shows most. Takes no arguments.", {}),
}
COARSE = {
    "marketplace": ["search_jobs", "get_job", "get_client_history", "get_connects_balance", "list_messages"],
    "portfolio": ["search_evidence", "get_case_study", "list_skills"],
}


def make(name: str, desc: str, params: dict[str, Any]) -> StructuredTool:
    schema = create_model(f"{name}_args", **{k: (t, ...) for k, t in params.items()})
    return StructuredTool.from_function(func=lambda **kw: "ok", name=name, description=desc, args_schema=schema)


def coarse_tools() -> list[StructuredTool]:
    return [make(n, f"{n.title()} operations. `action` is one of {acts}; `params` holds that action's arguments.",
                 {"action": str, "params": dict}) for n, acts in COARSE.items()]


def judge(task: dict, call: dict | None, coarse: bool) -> tuple[bool, bool]:
    if not call:
        return False, False
    args = call.get("args") or {}
    if coarse:
        tool_ok = args.get("action") == task["tool"]
        args = args.get("params") or {}
    else:
        tool_ok = call["name"] == task["tool"]
    if not tool_ok:
        return False, False
    if not task["arg"] or not task["value"]:
        return True, True
    return True, task["value"].lower() in str(args.get(task["arg"], "")).lower()


async def run(n: int = 40) -> None:
    llm = LLM()
    model = ChatOpenAI(model=llm.model_for("analyst"), base_url=llm.base_url, api_key=llm.api_key,
                       temperature=0, max_retries=6)
    sets = {"fine": ([make(k, *v) for k, v in FINE.items()], False),
            "coarse": (coarse_tools(), True),
            "rewritten": ([make(k, *v) for k, v in REWRITTEN.items()], False)}
    results = {}
    for name, (tools, is_coarse) in sets.items():
        bound, rows = model.bind_tools(tools), []
        for t in tasks(n):
            msg = await bound.ainvoke([("system", "You are a freelancer's assistant. Call exactly one tool."),
                                       ("user", t["q"])])
            call = msg.tool_calls[0] if msg.tool_calls else None
            tool_ok, arg_ok = judge(t, call, is_coarse)
            rows.append({"q": t["q"], "expected": t["tool"], "got": call, "tool_ok": tool_ok, "arg_ok": arg_ok,
                         "tokens": (msg.usage_metadata or {}).get("total_tokens", 0)})
        results[name] = {"tool_selection_accuracy": mean(float(r["tool_ok"]) for r in rows),
                         "argument_accuracy": mean(float(r["arg_ok"]) for r in rows),
                         "tokens_per_task": mean(r["tokens"] for r in rows), "rows": rows}
        print(name, {k: v for k, v in results[name].items() if k != "rows"})
    save("tool_granularity", {"model": llm.model_for("analyst"), "n_tasks": n, "results": results})


if __name__ == "__main__":
    asyncio.run(run())
